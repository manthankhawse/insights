import duckdb

def get_duckdb_connection():
    """Creates a DuckDB connection configured for local MinIO/S3."""
    con = duckdb.connect(database=':memory:')

    # Load the HTTP/S3 extension
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")

    # Configure MinIO credentials (matches your s3/client.py)
    con.execute("""
        CREATE SECRET (
            TYPE S3,
            KEY_ID 'minioadmin',
            SECRET 'minioadmin',
            REGION 'us-east-1',
            ENDPOINT 'localhost:9000',
            URL_STYLE 'path',
            USE_SSL false
        );
    """)
    return con