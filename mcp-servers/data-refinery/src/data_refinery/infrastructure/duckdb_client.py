# region imports 
import duckdb
import uuid
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

# model imports 
from data_refinery.domain.models.sql import SQLQueryResponse

logger = logging.getLogger(__name__)

# region DuckDB client
class DuckDBClient:
    """
    Infrastructure service for executing SQL transformations.
    """

    def __init__(self, artifact_dir: str = "/home/vn-78/Projects/code/Entropy/test/temp"):
        """
        Ensures that a folder is available to store the Generated file.
        """
        self.artifact_path = Path(artifact_dir)
        try:
            self.artifact_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"DuckDB artifact directory set to: {artifact_dir}")
        except PermissionError:
            raise RuntimeError(f"Critical: Cannot write to artifact directory: {artifact_dir}")

    def _configure_s3(self, conn: duckdb.DuckDBPyConnection):
        """Configures the DuckDB connection for S3 access if credentials exist."""
        endpoint = os.environ.get("S3_ENDPOINT_URL")
        key = os.environ.get("S3_ACCESS_KEY")
        secret = os.environ.get("S3_SECRET_KEY")
        
        logger.info(f"Configuring S3 for DuckDB. Endpoint: {endpoint}")
        
        if endpoint and key and secret:
            try:
                # Install/Load httpfs extension for S3 support
                conn.execute("INSTALL httpfs; LOAD httpfs;")
                
                # Configure S3/MinIO
                # Strip http/https from endpoint as DuckDB s3_endpoint expects just the host:port
                stripped_endpoint = endpoint.replace('http://', '').replace('https://', '')
                conn.execute(f"SET s3_endpoint='{stripped_endpoint}';")
                conn.execute(f"SET s3_access_key_id='{key}';")
                conn.execute(f"SET s3_secret_access_key='{secret}';")
                conn.execute("SET s3_url_style='path';")
                conn.execute("SET s3_use_ssl=false;")
                logger.info("S3 configuration applied successfully to DuckDB connection.")
            except Exception as e:
                logger.error(f"Failed to configure S3 for DuckDB: {e}")
        else:
            logger.warning("S3 credentials or endpoint missing from environment. S3 access will fail.")

    def _make_serializable(self, obj: Any) -> Any:
        """Helper to convert non-serializable objects (like date/datetime) to strings."""
        import datetime
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        return obj

    def execute_and_write(self, sql_query: str) -> SQLQueryResponse:
        """
        Executes a SQL query and materializes the result to a Parquet file.
        """
        logger.info(f"Executing SQL: {sql_query}")
        conn = duckdb.connect(database=':memory:')
        self._configure_s3(conn)

        try:
            relation = conn.sql(sql_query)
            row_count = relation.shape[0]
            col_count = relation.shape[1]
            columns = relation.columns

            sample_rows = relation.limit(5).fetchall()
            # Ensure sample data is serializable
            sample_data: List[Dict[str, Any]] = [
                self._make_serializable(dict(zip(columns, row))) for row in sample_rows
            ]

            file_id = uuid.uuid4().hex[:8]
            output_filename = f"result_{file_id}.parquet"
            output_uri = self.artifact_path / output_filename

            relation.write_parquet(str(output_uri))
            logger.info(f"Query successful. Result written to: {output_uri}")

            return SQLQueryResponse(
                status=True,
                total_rows=row_count,
                total_columns=col_count,
                sample_data=sample_data,
                result_uri=str(output_uri)
            )

        except duckdb.ParserException as e:
            logger.error(f"SQL Syntax Error: {e}")
            raise ValueError(f"SQL Syntax Error: {str(e)}")
        except duckdb.CatalogException as e:
            logger.error(f"Data Access Error (Catalog): {e}")
            raise FileNotFoundError(f"Data Access Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during SQL execution: {e}")
            raise RuntimeError(f"Execution Failed: {str(e)}")
        finally:
            conn.close()

    def query_preview(self, file_uri: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        Queries a portion of a dataset for preview purposes.
        """
        logger.info(f"Fetching preview for: {file_uri} (limit={limit}, offset={offset})")
        conn = duckdb.connect(database=':memory:')
        self._configure_s3(conn)
        
        try:
            sql = f"SELECT * FROM '{file_uri}' LIMIT {limit} OFFSET {offset}"
            relation = conn.sql(sql)
            
            columns = relation.columns
            rows = relation.fetchall()
            
            total_count = conn.sql(f"SELECT count(*) FROM '{file_uri}'").fetchone()[0]
            
            # Ensure data is serializable
            data = [self._make_serializable(dict(zip(columns, row))) for row in rows]
            logger.info(f"Preview successful. Retrieved {len(data)} rows.")
            
            return {
                "columns": columns,
                "data": data,
                "total_rows": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Preview failed for {file_uri}: {e}")
            raise
        finally:
            conn.close()
