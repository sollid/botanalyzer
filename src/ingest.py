import os
import gzip
import re
import glob
from datetime import datetime
import clickhouse_connect
import geoip2.database
from db import get_client, init_db
import multiprocessing
from functools import partial
import time

# Configuration
LOG_DIR = '/app/logs' if os.path.exists('/app/logs') else 'logs'
BATCH_SIZE = 100000  # Increased batch size
GEOIP_DB_PATH = 'GeoLite2-Country.mmdb'

# Regex Patterns
ACCESS_LOG_PATTERN = re.compile(
    r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+) (\S+)" (\d+) (\d+) "([^"]*)" "([^"]*)"'
)
ERROR_LOG_PATTERN = re.compile(
    r'^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (\d+)#(\d+): \*(\d+) (.+?)(?:, client: (\S+))?(?:, server: (\S+))?(?:, request: "([^"]+)")?(?:, host: "([^"]+)")?(?:, referrer: "([^"]+)")?'
)

BOT_KEYWORDS = [
    'bot', 'crawl', 'spider', 'slurp', 'facebook', 'google', 'bing', 'yandex', 'baidu', 
    'ahrefs', 'semrush', 'mj12', 'dotbot', 'petal', 'bytespider'
]

def parse_time_access(time_str):
    try:
        # 04/Dec/2025:00:04:04 +0100
        return datetime.strptime(time_str.split()[0], '%d/%b/%Y:%H:%M:%S')
    except:
        return datetime.now()

def parse_time_error(time_str):
    try:
        # 2025/12/04 03:11:09
        return datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
    except:
        return datetime.now()

def is_bot(user_agent):
    if not user_agent or user_agent == '-':
        return 0
    ua_lower = user_agent.lower()
    for keyword in BOT_KEYWORDS:
        if keyword in ua_lower:
            return 1
    return 0

def get_country(ip, reader):
    if not reader or ip == '-' or ip is None:
        return 'Unknown'
    try:
        response = reader.country(ip)
        return response.country.name or 'Unknown'
    except:
        return 'Unknown'

def process_file(file_path):
    print(f"Processing {file_path}...")
    
    # Each process needs its own connection
    try:
        client = get_client()
    except Exception as e:
        print(f"Failed to connect to DB in worker: {e}")
        return
        
    # Each process needs its own GeoIP reader
    geoip_reader = None
    if os.path.exists(GEOIP_DB_PATH):
        try:
            geoip_reader = geoip2.database.Reader(GEOIP_DB_PATH)
        except:
            pass

    access_batch = []
    error_batch = []
    
    ACCESS_COLUMNS = ['timestamp', 'client_ip', 'method', 'url', 'http_version', 'status_code', 'response_size', 'referer', 'user_agent', 'country', 'is_bot']
    ERROR_COLUMNS = ['timestamp', 'level', 'pid', 'tid', 'cid', 'message', 'client_ip', 'server', 'request', 'host', 'referrer']

    try:
        with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Try parsing as access log
                if 'HIT' in line or 'MISS' in line or ' HTTP/' in line: # Quick check before regex
                    access_match = ACCESS_LOG_PATTERN.match(line)
                    if access_match:
                        ip, time_str, method, url, proto, status, size, referer, ua = access_match.groups()
                        
                        row = [
                            parse_time_access(time_str),
                            ip,
                            method,
                            url,
                            proto,
                            int(status),
                            int(size),
                            referer,
                            ua,
                            get_country(ip, geoip_reader),
                            is_bot(ua)
                        ]
                        access_batch.append(row)

                        if len(access_batch) >= BATCH_SIZE:
                            client.insert('access_logs', access_batch, column_names=ACCESS_COLUMNS)
                            access_batch = []
                        continue

                # Try parsing as error log
                error_match = ERROR_LOG_PATTERN.match(line)
                if error_match:
                    time_str, level, pid, tid, cid, msg, client_ip, server, request, host, referrer = error_match.groups()
                    
                    row = [
                        parse_time_error(time_str),
                        level,
                        int(pid),
                        int(tid),
                        int(cid),
                        msg.strip(),
                        client_ip or '',
                        server or '',
                        request or '',
                        host or '',
                        referrer or ''
                    ]
                    error_batch.append(row)

                    if len(error_batch) >= BATCH_SIZE:
                        client.insert('error_logs', error_batch, column_names=ERROR_COLUMNS)
                        error_batch = []
                    continue
                    
        # Insert remaining
        if access_batch:
            client.insert('access_logs', access_batch, column_names=ACCESS_COLUMNS)
        if error_batch:
            client.insert('error_logs', error_batch, column_names=ERROR_COLUMNS)
            
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    finally:
        if geoip_reader:
            geoip_reader.close()

def process_logs_multiprocess():
    init_db()
    
    log_files = glob.glob(os.path.join(LOG_DIR, '**/*.gz'), recursive=True)
    print(f"Found {len(log_files)} log files. Starting multiprocessing...")
    
    # Use 75% of available cores to leave room for ClickHouse
    cpu_count = max(1, int(multiprocessing.cpu_count() * 0.75))
    print(f"Using {cpu_count} workers.")
    
    pool = multiprocessing.Pool(processes=cpu_count)
    pool.map(process_file, log_files)
    pool.close()
    pool.join()
    
    print("Ingestion complete.")

if __name__ == "__main__":
    start_time = time.time()
    try:
        process_logs_multiprocess()
    except Exception as e:
        print(f"Ingestion failed: {e}")
    print(f"Total time: {time.time() - start_time:.2f} seconds")
