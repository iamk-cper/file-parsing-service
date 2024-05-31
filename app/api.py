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

app = FastAPI()

# Get the absolute path of the project root directory
project_root = Path(__file__).parent.parent

# Mount the static files
static_path = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


def process_txt(file_content):
    lines = file_content.splitlines()
    words = file_content.split()
    characters = len(file_content)
    return {"rows": len(lines), "words": len(words), "characters": characters, "email": search_patterns(file_content, [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'])[r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'], "phone": search_patterns(file_content, [r'\b\d{9}\b'])[r'\b\d{9}\b']}


def process_csv(file_content):
    df = pd.read_csv(io.StringIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    characters = len(file_content)
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats,
        "characters": characters,
        "email": search_patterns(file_content, [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'])[r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'],
        "phone": search_patterns(file_content, [r'\b\d{9}\b'])[r'\b\d{9}\b']
    }


def process_json(file_content):
    df = pd.read_json(io.StringIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    characters = len(file_content)
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats,
        "characters": characters,
        "email": search_patterns(file_content, [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'])[r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'],
        "phone": search_patterns(file_content, [r'\b\d{9}\b'])[r'\b\d{9}\b']
    }


def process_xml(file_content):
    tree = ET.ElementTree(ET.fromstring(file_content))
    root = tree.getroot()
    data = [{elem.tag: elem.text for elem in child} for child in root]
    characters = len(file_content)
    return {
        "elements": len(root),
        "data": data,
        "characters": characters
    }


def process_excel(file_content):
    df = pd.read_excel(io.BytesIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    characters = len(file_content)
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats,
        "characters": characters
    }


def process_html(file_content):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(file_content, 'html.parser')
    text = soup.get_text()
    lines = text.splitlines()
    words = text.split()
    characters = len(text)
    return {"rows": len(lines), "words": len(words), "characters": characters, "email": search_patterns(text, [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'])[r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'], "phone": search_patterns(text, [r'\b\d{9}\b'])[r'\b\d{9}\b']}


def process_yaml(file_content):
    data = yaml.safe_load(file_content)
    characters = len(file_content)
    return {
        "data": data,
        "characters": characters
    }


def search_patterns(file_content, patterns):
    results = {}
    for pattern in patterns:
        matches = re.findall(pattern, file_content)
        results[pattern] = matches
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
                summary = process_txt(content_str)
            elif file.content_type == 'text/csv':
                content_str = content.decode('utf-8')
                summary = process_csv(content_str)
            elif file.content_type == 'application/json':
                content_str = content.decode('utf-8')
                summary = process_json(content_str)
            elif file.content_type == 'application/xml' or file.content_type == 'text/xml':
                content_str = content.decode('utf-8')
                summary = process_xml(content_str)
            elif file.content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or file.content_type == 'application/vnd.ms-excel':
                summary = process_excel(content)
            elif file.content_type == 'application/x-yaml' or file.content_type == 'text/yaml' or file.content_type == 'application/octet-stream':
                content_str = content.decode('utf-8')
                summary = process_yaml(content_str)
            elif file.content_type == 'text/html':
                content_str = content.decode('utf-8')
                summary = process_html(content_str)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

            if content_str:
                patterns = [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'\b\d{9}\b']
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
            filtered_data = {k: data[k] for k in selected_data[file_info] if k in data}
            results.append({"filename": file_info, "data": filtered_data})

    return JSONResponse(content={"results": results})
