import io
import re
import pandas as pd
import xml.etree.ElementTree as ET
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, Summary, Histogram, generate_latest
from starlette.responses import Response
from pathlib import Path
import yaml
from bs4 import BeautifulSoup
import time

app = FastAPI()

# Get the absolute path of the project root directory
project_root = Path(__file__).parent.parent

# Mount the static files
static_path = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

class DataStore:
    def __init__(self):
        self.emails = set()
        self.phone_numbers = set()
        self.uploaded_files = []

    def add_emails(self, email_list):
        self.emails.update(email_list)

    def add_phone_numbers(self, phone_list):
        self.phone_numbers.update(phone_list)

    def get_emails(self):
        return list(self.emails)

    def get_phone_numbers(self):
        return list(self.phone_numbers)

    def add_uploaded_file(self, file_summary):
        self.uploaded_files.append(file_summary)

    def get_uploaded_files(self):
        return self.uploaded_files

    def clear_uploaded_files(self):
        self.uploaded_files = []

# Instantiate the datastore as a global variable
data_store = DataStore()



# Dependency provider function
def get_data_store():
    return data_store

# Define Prometheus metrics
files_processed = Counter('files_processed_total', 'Total number of files processed')
processing_errors = Counter('processing_errors_total', 'Total number of file processing errors')
files_in_progress = Gauge('files_in_progress', 'Number of files currently being processed')
file_size = Gauge('file_size_bytes', 'Size of the file being processed in bytes')
processing_duration = Summary('file_processing_duration_seconds', 'Time spent processing files')
processing_time_histogram = Histogram('file_processing_time_seconds', 'Histogram of file processing times', buckets=(0.004, 0.005, 0.0075, 0.01, 0.02, 0.05, 0.1, 1.0, float('inf')))
last_upload_file_count = Gauge('last_upload_file_count', 'Number of files in the last upload')
last_upload_processing_duration = Gauge('last_upload_processing_duration_seconds', 'Processing duration of files in the last upload')


def process_file(file_content):
    lines = file_content.splitlines()
    words = file_content.split()
    return {
        "characters": len(file_content),
        "rows": len(lines),
        "words": len(words)
    }

def process_dataframe(df):
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    if 'Phone' in df.columns:
        df = df.drop(columns=['Phone'])
    stats = df.describe().to_dict()
    characters = df.to_csv(index=False).encode().decode()
    words = ' '.join(df.astype(str).values.flatten()).split()
    return {
        "visible_characters": len(characters),
        "visible_rows": df.shape[0],
        "visible_words": len(words),
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats
    }

def process_csv(file_content):
    df = pd.read_csv(io.StringIO(file_content))
    return {
        **process_file(file_content),
        **process_dataframe(df)
    }

def process_json(file_content):
    df = pd.read_json(io.StringIO(file_content))
    return {
        **process_file(file_content),
        **process_dataframe(df)
    }

def process_xml(file_content):
    tree = ET.ElementTree(ET.fromstring(file_content))
    data = [{elem.tag: elem.text for elem in child} for child in tree.getroot()]
    df = pd.DataFrame(data)
    return {
        **process_file(file_content),
        **process_dataframe(df)
    }

def process_html(file_content):
    soup = BeautifulSoup(file_content, 'html.parser')
    table = soup.find('table')
    if table:
        df = pd.read_html(str(table))[0]
        return {
            **process_file(file_content),
            **process_dataframe(df)
        }
    else:
        visible_text = soup.get_text()
        visible_lines = visible_text.splitlines()
        visible_words = visible_text.split()
        return {
            **process_file(file_content),
            "visible_characters": len(visible_text),
            "visible_rows": len(visible_lines),
            "visible_words": len(visible_words)
        }

def process_yaml(file_content):
    data = yaml.safe_load(file_content)
    df = pd.json_normalize(data)
    return {
        **process_file(file_content),
        **process_dataframe(df)
    }

def search_patterns(file_content, patterns, store):
    results = {}
    for pattern, name in patterns:
        matches = re.findall(pattern, file_content)
        if name == 'email':
            store.add_emails(matches)
        elif name == 'number':
            store.add_phone_numbers(matches)
        results[name] = matches
    return results

@app.post("/uploadfiles/")
async def upload_files(files: list[UploadFile] = File(...), store: DataStore = Depends(get_data_store)):
    # Clear old files from the datastore
    store.clear_uploaded_files()

    # Track the number of files in the current upload
    num_files = len(files)
    last_upload_file_count.set(num_files)

    # Track the total processing duration for this upload
    total_processing_duration = 0

    files_in_progress.set(num_files)
    try:
        for file in files:
            content = await file.read()
            content_str = content.decode('utf-8')
            summary = None

            file_size.set(len(content_str))

            start_time = time.time()

            try:
                if file.content_type == 'text/plain':
                    summary = process_file(content_str)
                elif file.content_type == 'text/csv':
                    summary = process_csv(content_str)
                elif file.content_type == 'application/json':
                    summary = process_json(content_str)
                elif file.content_type in ['application/xml', 'text/xml']:
                    summary = process_xml(content_str)
                elif file.content_type in ['application/x-yaml', 'text/yaml', 'application/octet-stream']:
                    summary = process_yaml(content_str)
                elif file.content_type == 'text/html':
                    summary = process_html(content_str)
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

                patterns = [(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'), (r'\b\d{9}\b', 'number')]
                pattern_matches = search_patterns(content_str, patterns, store)
                summary["pattern_matches"] = pattern_matches

                store.add_uploaded_file({"filename": file.filename, "summary": summary})

                files_processed.inc()
            except Exception as e:
                processing_errors.inc()
                raise e
            finally:
                end_time = time.time()
                duration = end_time - start_time
                processing_duration.observe(duration)  # Observe the duration of file processing
                processing_time_histogram.observe(duration)  # Observe the duration in the histogram

                total_processing_duration += duration  # Accumulate the processing duration

        # Set the last upload processing duration metric
        last_upload_processing_duration.set(total_processing_duration)

        return JSONResponse(content={"files": store.get_uploaded_files()})
    except Exception as e:
        processing_errors.inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        files_in_progress.set(0)

@app.post("/showdata/")
async def show_data(request: Request, store: DataStore = Depends(get_data_store)):
    request_json = await request.json()
    selected_files = request_json.get('selectedFiles')
    selected_data = request_json.get('selectedData')

    results = []
    for file_info in selected_files:
        file_summary = next((item for item in store.get_uploaded_files() if item["filename"] == file_info), None)
        if file_summary:
            data = file_summary['summary']
            filtered_data = {}
            include_others = "others" in selected_data[file_info]

            explicit_categories = ['email', 'number']

            for key, value in data.items():
                if key == "pattern_matches":
                    pattern_data = data["pattern_matches"]
                    for pattern_key, pattern_value in pattern_data.items():
                        if pattern_key in explicit_categories and pattern_key in selected_data[file_info]:
                            filtered_data[pattern_key] = pattern_value
                elif include_others:
                    if not any(cat in key for cat in explicit_categories + ['pattern_matches']):
                        filtered_data[key] = value

            results.append({"filename": file_info, "data": filtered_data})

    return JSONResponse(content={"results": results})


@app.get("/global_data/")
async def get_global_data(data_type: str, store: DataStore = Depends(get_data_store)):
    if data_type == 'emails':
        return JSONResponse(content={"emails": store.get_emails()})
    elif data_type == 'phone_numbers':
        return JSONResponse(content={"phone_numbers": store.get_phone_numbers()})
    else:
        raise HTTPException(status_code=400, detail="Invalid data type requested")

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
