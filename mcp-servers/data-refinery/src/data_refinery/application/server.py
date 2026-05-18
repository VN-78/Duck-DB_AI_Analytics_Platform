# region imports 
from mcp.server.fastmcp import FastMCP
import uuid
from pathlib import Path
import json
import logging

# Domain And Infrastructure imports
from data_refinery.domain.models.dataset import DatasetOverview
from data_refinery.domain.models.sql import SQLQueryResponse
from data_refinery.domain.models.cleaning import CleaningOptions, CleaningResponse
from data_refinery.infrastructure.pandas_client import PandasDatasetClient
from data_refinery.infrastructure.duckdb_client import DuckDBClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("data-refinery")

# region initialize mcp server
mcp = FastMCP(
    name = "data-refinery",
    )

client = PandasDatasetClient()
db_client = DuckDBClient()

# region Inspect-data tool  
@mcp.tool()
def inspect_dataset(file_uri: str) -> DatasetOverview:
    """
    Inspects a CSV dataset to understand its structure, schema, and data quality.
    
    CRITICAL: Always run this tool FIRST before performing any analysis or visualization 
    to understand column names and types.

    It calculates:
    - Row/Column counts
    - Missing value percentages (to identify dirty data)
    - Data types for every column
    - Basic statistics for numeric columns (mean, std, min, max, outlier counts)
    - A sample of 5 rows to understand context
    
    Args:
        file_uri: The absolute path to the file. 
            - Local: '/home/user/data/file.csv'
            - S3: 's3://my-bucket/data.csv'
    """
    logger.info(f"Tool 'inspect_dataset' called for {file_uri}")
    try:
        # load the data 
        df = client.load_data(file_uri)

        # analyze the data 
        status = client.analyze(df)

        return status
    except Exception as e:
        logger.error(f"Tool 'inspect_dataset' failed: {e}")
        raise RuntimeError(f"Inspection Failed: {str(e)}")

# region run_sql_query tool
@mcp.tool()
def run_sql_query(file_uri: str, sql_query: str) -> SQLQueryResponse:
    """
    Executes a SQL query against a file and saves the result to a new file.

    Use this tool to filter, sort, or aggregate data.
    
    CRITICAL SYNTAX RULES:
    1. The query MUST reference the 'file_uri' directly in the FROM clause.
    2. DO NOT use generic table names like 'users' or 'data'.
    3. The tool returns a 'result_uri' (path to the new file), NOT the full data.

    Args:
        file_uri: The absolute path to the source file (e.g., '/app/data.csv').
        sql_query: The DuckDB SQL query string.
        
    Examples:
        Correct: "SELECT name, age FROM '/app/data.csv' WHERE age > 25"
        Incorrect: "SELECT name, age FROM users WHERE age > 25"
    """
    logger.info(f"Tool 'run_sql_query' called. Target: {file_uri}")
    # 1. Input Integrity Check
    if file_uri not in sql_query:
        # Fail fast if the agent forgot to include the file path
        raise ValueError(
            f"Invalid Query: You must select directly from the file path. "
            f"Expected: SELECT ... FROM '{file_uri}' ..."
        )

    # 2. Execution Delegation
    try:
        response = db_client.execute_and_write(sql_query)
        return response
    except Exception as e:
        logger.error(f"Tool 'run_sql_query' failed: {e}")
        # In MCP, raising an exception usually returns a clear error to the client.
        raise RuntimeError(f"Tool Execution Error: {str(e)}")


# region clean_data_tool
@mcp.tool()
def clean_dataset(file_uri: str, options: CleaningOptions) -> CleaningResponse:
    """
    Apply data cleaning operations (imputation, normalization) to a dataset.

    This tool loads a file, applies the specified 'CleaningOptions', and saves 
    the result to a new Parquet file. It is the PRIMARY way to handle missing 
    values (NaNs) and inconsistent headers.

    Args:
        file_uri: The absolute path to the input file (e.g., 's3://bucket/raw.csv').
        options: A CleaningOptions object containing the specific rules.
            The 'strategies' dictionary maps column names to actions:
            - "drop": Remove rows.
            - "mean": Fill with average (numeric only).
            - "mode": Fill with most frequent (text/numeric).
            - "zero": Fill with 0 (numeric only).
            - "unknown": Fill with 'Unknown' (text only).
            
            The 'date_columns' list allows standardizing date formats:
            - "column_name": Name of the date column.
            - "output_format": Target format (e.g., "%Y-%m-%d").

    Returns:
        CleaningResponse: Metadata about the cleaned file (row count, new path, and column stats).
    """
    logger.info(f"Tool 'clean_dataset' called for {file_uri}")
    try:
        # 1. Load the data
        df = client.load_data(file_uri)
        
        # 2. Apply the cleaning logic (The function you just wrote)
        cleaned_df, quality_report = client.clean_dataset(df, options)
        
        # 3. Save Artifact (Pass-by-Reference)
        # We generate a unique ID so we don't overwrite previous work
        file_id = uuid.uuid4().hex[:8]
        output_filename = f"cleaned_{file_id}.parquet"
        
        if file_uri.startswith("s3://"):
             # Keep in the same "folder" as input
            parent = str(Path(file_uri).parent)
            # Fix Path issue with s3:// (Path('s3://...') might behave oddly on some OS)
            # Simpler string manipulation for S3 to be safe
            if parent == ".": # happens if file_uri is just 's3://bucket'
                 parent = file_uri
            
            # Reconstruct URI properly
            # If file_uri is s3://bucket/folder/file.csv -> parent is usually s3:/bucket/folder (Path strips slash)
            # Safest is to just replace filename
            base_uri = file_uri.rsplit('/', 1)[0]
            output_path = f"{base_uri}/{output_filename}"
        else:
            # Ensure the directory exists (using your configured temp path)
            output_path = str(Path("/home/vn-78/Projects/code/Entropy/test/temp") / output_filename)
        
        # Save using the smart client
        client.save_dataframe(cleaned_df, output_path)
        
        # 4. Return the DISTINCT CleaningResponse
        return CleaningResponse(
            status=True,
            result_uri=output_path,
            **quality_report.model_dump()
        )

    except Exception as e:
        logger.error(f"Tool 'clean_dataset' failed: {e}")
        raise RuntimeError(f"Cleaning Failed: {str(e)}")

# region generate_visualization
@mcp.tool()
def generate_visualization(file_uri: str, chart_type: str, x_column: str, y_column: str = "", title: str = "") -> str:
    """
    Generates a full Vega-Lite JSON specification for a dataset.
    
    CRITICAL: Always run 'inspect_dataset' first to confirm column names and types before calling this tool.
    
    Args:
        file_uri: The absolute path or S3 URI to the dataset (e.g., 's3://bucket/data.csv').
        chart_type: The type of chart to generate. MUST be one of: 'bar', 'line', 'scatter', or 'pie'.
        x_column: The column name for the X-axis (categorical for 'bar'/'pie', numeric for 'scatter'/'line').
        y_column: The column name for the Y-axis (must be numeric). If empty, the tool will automatically perform a 'count(*)' aggregation on x_column.
        title: A descriptive title for the chart.
        
    Usage Notes:
    - For 'bar' and 'pie' charts, if y_column is omitted, it creates a frequency distribution of x_column.
    - The tool automatically samples the first 1000 rows to ensure frontend performance.
    """
    try:
        import duckdb
        
        logger.info(f"Generating {chart_type} visualization for {file_uri}. X: {x_column}, Y: {y_column}")
        
        conn = duckdb.connect(database=':memory:')
        db_client._configure_s3(conn)
        
        # 1. Fetch Data
        # Sample/Aggregate data (Limit to 1000 rows for browser stability)
        try:
            if not y_column:
                logger.info(f"No Y column provided. Performing COUNT aggregation on {x_column}")
                # Use double quotes for column names to handle spaces/special characters
                sql = f"SELECT \"{x_column}\", count(*) as count_val FROM '{file_uri}' GROUP BY \"{x_column}\" ORDER BY count_val DESC LIMIT 1000"
                x_col_final = x_column
                y_col_final = "count_val"
            else:
                logger.info(f"Y column provided: {y_column}. Selecting both.")
                sql = f"SELECT \"{x_column}\", \"{y_column}\" FROM '{file_uri}' LIMIT 1000"
                x_col_final = x_column
                y_col_final = y_column
                
            rel = conn.sql(sql)
            columns = rel.columns
            rows = rel.fetchall()
            data_values = [dict(zip(columns, row)) for row in rows]
            logger.info(f"Successfully retrieved {len(data_values)} data points for visualization.")
        except Exception as e:
            logger.error(f"SQL execution failed for visualization: {e}")
            raise
        finally:
            conn.close()

        # 2. Map to Vega-Lite Schema
        vega_type_map = {
            "bar": "bar",
            "line": "line",
            "scatter": "point",
            "pie": "arc"
        }
        
        mark = vega_type_map.get(chart_type, "bar")
        
        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
            "title": title or f"{chart_type.capitalize()} Chart",
            "width": "container",
            "height": 300,
            "data": {"name": "table"},
            "mark": {"type": mark, "tooltip": True},
            "encoding": {
                "x": {"field": x_col_final, "type": "nominal" if chart_type in ["bar", "pie"] else "quantitative", "axis": {"labelAngle": -45}},
                "y": {"field": y_col_final, "type": "quantitative"}
            }
        }
        
        # Adjust for Pie Charts
        if chart_type == "pie":
            spec["encoding"] = {
                "theta": {"field": y_col_final, "type": "quantitative"},
                "color": {"field": x_col_final, "type": "nominal"}
            }
        
        # Adjust for Scatter Plots (quantitative X)
        if chart_type == "scatter":
            spec["encoding"]["x"]["type"] = "quantitative"

        logger.info(f"Generated Vega-Lite spec for {chart_type} chart.")
        return json.dumps({
            "type": "vega_lite",
            "chart_type": chart_type,
            "data": data_values,
            "spec": spec
        })
        
    except Exception as e:
        logger.error(f"Visualization tool failed: {e}")
        raise RuntimeError(f"Vega-Lite Generation Failed: {str(e)}")

# region preview_dataset
@mcp.tool()
def preview_dataset(file_uri: str, limit: int = 10, offset: int = 0) -> str:
    """
    Returns a portion of the dataset for previewing in a table.
    
    CRITICAL: This tool uses DuckDB to efficiently fetch a window of rows.
    Use this for paginated table views.
    
    Args:
        file_uri: The absolute path or S3 URI to the file.
        limit: The number of rows to return (default: 10).
        offset: The number of rows to skip (default: 0).
    """
    try:
        logger.info(f"Tool 'preview_dataset' called for {file_uri} (limit={limit}, offset={offset})")
        preview = db_client.query_preview(file_uri, limit, offset)
        return json.dumps(preview)
    except Exception as e:
        logger.error(f"Tool 'preview_dataset' failed: {e}")
        raise RuntimeError(f"Preview Generation Failed: {str(e)}")


# region main
if __name__ == "__main__":
    mcp.run(transport="stdio")
