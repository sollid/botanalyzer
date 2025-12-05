import clickhouse_connect
import os

CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')

def get_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, 
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )

def init_db():
    client = get_client()
    
    # Access Logs Table
    client.command("""
        CREATE TABLE IF NOT EXISTS access_logs (
            timestamp DateTime,
            client_ip String,
            method String,
            url String,
            http_version String,
            status_code UInt16,
            response_size UInt64,
            referer String,
            user_agent String,
            country LowCardinality(String),
            is_bot UInt8
        ) ENGINE = MergeTree()
        ORDER BY timestamp
        PARTITION BY toYYYYMM(timestamp)
    """)

    # Add indices for performance
    try:
        client.command("ALTER TABLE access_logs ADD INDEX IF NOT EXISTS idx_status status_code TYPE set(0) GRANULARITY 1")
        client.command("ALTER TABLE access_logs ADD INDEX IF NOT EXISTS idx_ua user_agent TYPE tokenbf_v1(256, 2, 0) GRANULARITY 1")
    except Exception as e:
        print(f"Index creation warning: {e}")

    # Error Logs Table
    client.command("""
        CREATE TABLE IF NOT EXISTS error_logs (
            timestamp DateTime,
            level LowCardinality(String),
            pid UInt32,
            tid UInt32,
            cid UInt32,
            message String,
            client_ip String,
            server String,
            request String,
            host String,
            referrer String
        ) ENGINE = MergeTree()
        ORDER BY timestamp
        PARTITION BY toYYYYMM(timestamp)
    """)
    
    init_mvs(client)
    
    print("Database tables and views initialized.")

def init_mvs(client):
    # Materialized View: Hourly Traffic Stats
    client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_traffic
        ENGINE = SummingMergeTree()
        ORDER BY time
        POPULATE
        AS SELECT
            toStartOfHour(timestamp) as time,
            count() as requests,
            countIf(status_code >= 400) as errors,
            sum(response_size) as total_bytes
        FROM access_logs
        GROUP BY time
    """)

    # Materialized View: Daily Bot Stats
    client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_bots
        ENGINE = SummingMergeTree()
        ORDER BY date
        POPULATE
        AS SELECT
            toDate(timestamp) as date,
            countIf(is_bot=1) as bot_requests,
            countIf(is_bot=0) as human_requests
        FROM access_logs
        GROUP BY date
    """)


if __name__ == "__main__":
    init_db()

