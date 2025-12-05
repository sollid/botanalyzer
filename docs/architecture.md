# Log Analyzer Architecture

## Overview
This system is designed to ingest, store, and analyze Nginx access and error logs locally using Docker, ClickHouse, and Streamlit. It aims to provide actionable insights for IT (security/anomalies) and Marketing (SEO/traffic) teams.

## Components

### 1. Data Storage: ClickHouse
- **Role**: High-performance columnar database for storing large volumes of log data.
- **Why ClickHouse**: Excellent compression and query speed for analytical workloads (OLAP).
- **Schema**:
  - `access_logs`: Stores parsed Nginx access logs. Partitioned by date.
  - `error_logs`: Stores parsed Nginx error logs.

### 2. Data Ingestion: Python Script (`src/ingest.py`)
- **Role**: ETL process to read compressed log files, parse them, enrich data (GeoIP, Bot detection), and load into ClickHouse.
- **Key Features**:
  - Recursive file scanning in `logs/` directory.
  - Support for `.gz` decompression.
  - Batch insertion for performance.
  - User-Agent parsing for bot classification.

### 3. User Interface: Streamlit (`src/app.py`)
- **Role**: Interactive web dashboard for data visualization and exploration.
- **Modules**:
  - **Dashboard**: High-level KPIs and trends.
  - **Bot Analyzer**: Identification of bot traffic (Google, Facebook, etc.) and potential DDoS/spam anomalies.
  - **SEO & Traffic**: Analysis of referrers, landing pages, and status codes.
  - **Log Explorer**: Raw data search functionality.

## Data Flow
1. **Raw Logs**: Gzipped log files placed in `logs/`.
2. **Ingestion**: `src/ingest.py` reads files -> Parses lines -> Enriches (GeoIP/UA) -> Inserts to ClickHouse.
3. **Storage**: Data persists in ClickHouse volume.
4. **Analysis**: User interacts with Streamlit -> SQL queries sent to ClickHouse -> Results visualized.

## Metrics Definition
- **Requests**: Total number of HTTP requests.
- **Unique IPs**: Count of distinct client IP addresses.
- **Bandwidth**: Sum of response bytes sent.
- **Error Rate**: Percentage of 4xx and 5xx responses.
- **Bot Traffic**: Traffic matched against known bot User-Agent patterns.


