import os
import snowflake.connector
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Load environment variables from .env file
load_dotenv()

# Persistent connection object
snowflake_conn = None

def connect_snowflake():
    global snowflake_conn
    if snowflake_conn is None or snowflake_conn.is_closed():
        try:
            snowflake_conn = snowflake.connector.connect(
                user=os.getenv('SF_USER'),
                password=os.getenv('SF_PASSWORD'),
                account=os.getenv('SF_ACCOUNT'),
                warehouse=os.getenv('SF_WAREHOUSE'),
                database=os.getenv('SF_DATABASE'),
                schema=os.getenv('SF_SCHEMA'),
                role=os.getenv('SF_ROLE'),
                passcode=os.getenv('SF_PASSCODE'),
                # SSL configuration to handle certificate issues
                validate_default_parameters=False,
                # Disable OCSP check which often causes certificate issues
                disable_request_pooling=True,
                # Additional SSL settings to handle certificate validation issues
                insecure_mode=True,  # Disable SSL certificate validation
                ocsp_fail_open=True,  # Allow connection even if OCSP check fails
            )
            print("Successfully connected to Snowflake!")
        except Exception as e:
            print(f"Failed to connect to Snowflake: {e}")
            print("Continuing without Snowflake connection for testing...")
            snowflake_conn = None
    return snowflake_conn

def close_snowflake():
    global snowflake_conn
    if snowflake_conn is not None:
        try:
            snowflake_conn.close()
        except Exception:
            pass
        snowflake_conn = None

def execute_query(query: str, params: Optional[tuple] = None) -> List[Dict]:
    """
    Executes a SQL query on Snowflake and returns the results as a list of dictionaries.
    """
    print(f"DEBUG: execute_query called with query: {query[:100]}...")
    print(f"DEBUG: execute_query params: {params}")

    conn = connect_snowflake()
    if conn is None:
        print("ERROR: No Snowflake connection available. Cannot execute query.")
        raise Exception("Snowflake connection failed. Please check your connection settings and environment variables.")

    results = []
    try:
        print("DEBUG: Executing query on Snowflake...")
        with conn.cursor(snowflake.connector.DictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            print(f"DEBUG: Query executed successfully, got {len(results)} results")
            if results:
                print(f"DEBUG: First result: {results[0]}")
    except Exception as e:
        print(f"ERROR: Failed to execute Snowflake query: {e}")
        print(f"DEBUG: Query was: {query}")
        print(f"DEBUG: Params were: {params}")
        import traceback
        traceback.print_exc()
        raise e

    print(f"DEBUG: execute_query returning {len(results)} results")
    return results