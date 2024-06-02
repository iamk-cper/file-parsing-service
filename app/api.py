import io
import re
import pandas as pd
import xml.etree.ElementTree as ET
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import openpyxl
import xlrd
import yaml
from bs4 import BeautifulSoup

app = FastAPI()

# Get the absolute path of the project root directory
project_root = Path(__file__).parent.parent

# Mount the static files
static_path = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


def process_csv(file_content):
    df = pd.read_csv(io.StringIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    characters = len(file_content)
    # Calculating words by joining all cell values and splitting into words
    words = ' '.join(df.astype(str).values.flatten()).split()
    return {
        "characters": characters,
        "rows": df.shape[0],
        "words": len(words),
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats
    }


def process_json(file_content):
    df = pd.read_json(io.StringIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    characters = len(file_content)
    # Calculating words by joining all cell values and splitting into words
    words = ' '.join(df.astype(str).values.flatten()).split()
    return {
        "characters": characters,
        "rows": df.shape[0],
        "words": len(words),
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats
    }


def process_file(file_content):
    lines = file_content.splitlines()
    words = file_content.split()
    characters = len(file_content)
    return {
        "characters": characters,
        "rows": len(lines),
        "words": len(words)
        }


def process_xml(file_content):
    tree = ET.ElementTree(ET.fromstring(file_content))
    data = [{elem.tag: elem.text for elem in child} for child in tree.getroot()]

    return {
        **process_file(file_content),
        "data": data
    }



def process_html(file_content):
    soup = BeautifulSoup(file_content, 'html.parser')
    visible_text = soup.get_text()
    visible_lines = visible_text.splitlines()
    visible_words = visible_text.split()

    text = soup.get_text()
    return {
        **process_file(file_content),
        "visible_characters": len(visible_text),  # Characters in visible text
        "visible_rows": len(visible_lines),  # Lines in visible text
        "visible_words": len(visible_words)  # Words in visible text
    }


def process_yaml(file_content):
    data = yaml.safe_load(file_content)

    return {
        **process_file(file_content),
        "data": data
    }



def search_patterns(file_content, patterns):
    results = {}
    for pattern, name in patterns:
        matches = re.findall(pattern, file_content)
        results[name] = matches
    return results


# Global storage for emails and phone numbers
all_emails = set()
all_phone_numbers = set()

def search_patterns(file_content, patterns):
    global all_emails, all_phone_numbers
    results = {}
    for pattern, name in patterns:
        matches = re.findall(pattern, file_content)
        if name == 'email':
            all_emails.update(matches)
        elif name == 'number':
            all_phone_numbers.update(matches)
        results[name] = matches
    return results


@app.post("/uploadfiles/")
async def upload_files(files: list[UploadFile] = File(...)):
    global uploaded_files
    uploaded_files = []
    try:
        for file in files:
            content = await file.read()
            content_str = None
            summary = None

            if file.content_type == 'text/plain':
                content_str = content.decode('utf-8')
                summary = process_file(content_str)
            elif file.content_type == 'text/csv':
                content_str = content.decode('utf-8')
                summary = process_csv(content_str)
            elif file.content_type == 'application/json':
                content_str = content.decode('utf-8')
                summary = process_json(content_str)
            elif file.content_type == 'application/xml' or file.content_type == 'text/xml':
                content_str = content.decode('utf-8')
                summary = process_xml(content_str)
            elif file.content_type == 'application/x-yaml' or file.content_type == 'text/yaml' or file.content_type == 'application/octet-stream':
                content_str = content.decode('utf-8')
                summary = process_yaml(content_str)
            elif file.content_type == 'text/html':
                content_str = content.decode('utf-8')
                summary = process_html(content_str)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

            if content_str:
                patterns = [(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'), (r'\b\d{9}\b', 'number')]
                pattern_matches = search_patterns(content_str, patterns)
                summary["pattern_matches"] = pattern_matches

            uploaded_files.append({"filename": file.filename, "summary": summary})

        return JSONResponse(content={"files": uploaded_files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/showdata/")
async def show_data(request: Request):
    request_json = await request.json()
    selected_files = request_json.get('selectedFiles')
    selected_data = request_json.get('selectedData')

    results = []
    for file_info in selected_files:
        file_summary = next((item for item in uploaded_files if item["filename"] == file_info), None)
        if file_summary:
            data = file_summary['summary']
            filtered_data = {}
            include_others = "others" in selected_data[file_info]

            # Explicit categories
            explicit_categories = ['email', 'number']

            for key, value in data.items():
                if key in explicit_categories:
                    if key in selected_data[file_info]:
                        filtered_data[key] = value
                elif include_others:
                    if not any(cat in key for cat in explicit_categories + ['pattern_matches']):
                        filtered_data[key] = value

            results.append({"filename": file_info, "data": filtered_data})

    return JSONResponse(content={"results": results})
