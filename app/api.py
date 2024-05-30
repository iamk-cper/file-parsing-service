import io
import re
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

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
    return {"rows": len(lines), "words": len(words), "characters": characters}


def process_csv(file_content):
    df = pd.read_csv(io.StringIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats
    }


def process_json(file_content):
    df = pd.read_json(io.StringIO(file_content))
    unique_values = {column: df[column].unique().tolist() for column in df.columns}
    stats = df.describe().to_dict()
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "unique_values": unique_values,
        "stats": stats
    }


def search_patterns(file_content, patterns):
    results = {}
    for pattern in patterns:
        matches = re.findall(pattern, file_content)
        results[pattern] = matches
    return results


@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        if file.content_type == 'text/plain':
            summary = process_txt(content_str)
        elif file.content_type == 'text/csv':
            summary = process_csv(content_str)
        elif file.content_type == 'application/json':
            summary = process_json(content_str)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        patterns = [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'\b\d{9}\b']
        pattern_matches = search_patterns(content_str, patterns)
        summary["pattern_matches"] = pattern_matches

        return JSONResponse(content=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
