# File Parsing Service

## Overview
The File Parsing Service is a robust application designed to handle various file parsing operations. It supports multiple file formats, including CSV, JSON, XML, and more. This service allows users to upload, parse, and process files efficiently, providing a seamless integration for data extraction and transformation tasks.

## Features
- **Multi-Format Support**: Parse and process files in CSV, JSON, XML, and other formats.
- **API Integration**: RESTful API endpoints for file upload, parsing, and data retrieval.
- **Error Handling**: Comprehensive error handling for file validation and parsing errors.
- **Scalability**: Designed to handle large files and concurrent processing.
- **Custom Parsing Rules**: Define custom parsing rules to meet specific data extraction requirements.
- **Metrics Exposition**: Integrate functionality to expose key metrics related to the file processing operations using Prometheus.

## Installation
Follow these steps to set up the File Parsing Service locally:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamk-cper/file-parsing-service.git
   cd file-parsing-service
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**

   a) run server locally through system console (and go to site http://localhost:8000/static/index.html):
   ```bash
   uvicorn app.main:app
   ```

   b) run using Docker (details in following sections)

## Docker Usage
You can also run the File Parsing Service using Docker. Follow these steps:

1. **Build the Docker image:**
   ```bash
   docker build -t file-parsing-service .
   ```

2. **Run the Docker container:**
   ```bash
   docker run -p 8000:8000 file-parsing-service
   ```

This will start the service inside a Docker container, accessible at `http://localhost:8000/static/index.html`.

## HTML View
The HTML view provides options and buttons to interact with the file parsing service:
- **Upload Files section**: Allows users to upload file(s) for parsing using **Upload** button.
- **Loaded Files section**: Allows users to see currently uploaded files.
- **Select Data section**:

  a) to see emails, numbers or other data (number of words, characters, rows, unique values etc.) following option and file name has to be choosen (without selecting file name nothing will happen).

  b) special options **All emails** and **All Phone Numbers** shows all of the unique values found in all files in one list.

  c) pressing **Show Data** button shows selected data.

  d) pressing **Download Data** downloads current state of data in .json file type.

To use these options, navigate to the application's root URL (e.g., `http://localhost:8000/static/index.html`) in your web browser.

## Prometheus
The File Parsing Service exposes key metrics using Prometheus. To access the metrics, you can visit the `/metrics` endpoint:

- **Endpoint**: `/metrics`
- **Method**: `GET`
- **Description**: Exposes Prometheus metrics.

### Using Prometheus
1. **Install Prometheus**: Follow the [Prometheus installation guide](https://prometheus.io/docs/prometheus/latest/installation/).
2. **Configure Prometheus**:

   a) Add the following job to your Prometheus configuration file:
    ```yaml
    scrape_configs:
      - job_name: 'file-parsing-service'
        static_configs:
          - targets: ['localhost:8000']
    ```

    b) or use pre-set prometheus.yml file from repository
   
4. **Start Prometheus**: Run Prometheus with your configuration file.
5. **Access Metrics**:

   a) Navigate to `http://localhost:9090` to view the metrics collected by Prometheus.

   b) or go to site `http://localhost:8000/metrics`

### Prometheus metrics
The File Parsing Service collects and exposes several key metrics to provide insights into its performance and health. Below is a description of each metric exposed by the service:

- **python_gc_objects_collected_total**: Total number of objects collected during garbage collection.
  - **Type**: Counter
  - **Labels**: `generation` - The generation of the garbage collector.
  
- **python_gc_objects_uncollectable_total**: Total number of uncollectable objects found during garbage collection.
  - **Type**: Counter
  - **Labels**: `generation` - The generation of the garbage collector.

- **python_gc_collections_total**: Total number of times each generation was collected by the garbage collector.
  - **Type**: Counter
  - **Labels**: `generation` - The generation of the garbage collector.

- **python_info**: Provides Python platform information.
  - **Type**: Gauge
  - **Labels**: `implementation`, `major`, `minor`, `patchlevel`, `version`

- **files_processed_total**: Total number of files processed by the service.
  - **Type**: Counter

- **files_processed_created**: Timestamp of the last file processed.
  - **Type**: Gauge

- **processing_errors_total**: Total number of file processing errors.
  - **Type**: Counter

- **processing_errors_created**: Timestamp of the last processing error.
  - **Type**: Gauge

- **files_in_progress**: Number of files currently being processed.
  - **Type**: Gauge

- **file_size_bytes**: Size of the last processed file in bytes.
  - **Type**: Gauge

- **file_processing_duration_seconds**: Time spent processing files.
  - **Type**: Summary
  - **Metrics**: `count` (total number of files processed), `sum` (total processing time in seconds)

- **file_processing_time_seconds**: Histogram of file processing times.
  - **Type**: Histogram
  - **Buckets**: Various time intervals (`le` label) to record processing times

- **last_upload_file_count**: Number of files in the last upload.
  - **Type**: Gauge

- **last_upload_processing_duration_seconds**: Total processing duration of files in the last upload.
  - **Type**: Gauge

These metrics help monitor and analyze the performance and health of the File Parsing Service, ensuring it operates efficiently and effectively.


## Usage
### API Endpoints
- **Upload File**
  - **Endpoint**: `/upload`
  - **Method**: `POST`
  - **Description**: Upload a file for parsing.
  - **Example**:
    ```bash
    curl -X POST -F 'file=@/path/to/your/file.csv' http://localhost:8000/upload
    ```

- **Parse File**
  - **Endpoint**: `/parse`
  - **Method**: `POST`
  - **Description**: Parse an uploaded file.
  - **Example**:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"file_id": "12345"}' http://localhost:8000/parse
    ```

- **Retrieve Data**
  - **Endpoint**: `/data`
  - **Method**: `GET`
  - **Description**: Retrieve parsed data.
  - **Example**:
    ```bash
    curl -X GET http://localhost:8000/data?file_id=12345
    ```

## Script usage example
```python
import requests

# Upload file
with open('data.csv', 'rb') as f:
    response = requests.post('http://localhost:8000/upload', files={'file': f})
file_id = response.json()['file_id']

# Parse file
response = requests.post('http://localhost:8000/parse', json={'file_id': file_id})

# Retrieve parsed data
response = requests.get(f'http://localhost:8000/data?file_id={file_id}')
data = response.json()
print(data)
```


## Technologies Used
- **Python**: Core language for the application.
- **FastAPI**: Web framework for building the API.
- **Pandas**: Data manipulation and analysis.
- **XMLtodict**: Simple XML parsing.
- **JSON**: Handling JSON data.
- **Prometheus**: Monitoring and metrics exposition.
- **Docker**: Containerization.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
