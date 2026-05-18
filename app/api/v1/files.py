from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.storage import storage_service
from app.services.mcp_client import data_refinery_mcp
import uuid
import json

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Uploads a file to the configured storage (MinIO/S3).
    Returns the 's3://' URI which can be passed to the Agent/MCP tools.
    """
    try:
        # Generate unique filename to prevent overwrites
        extension = file.filename.split(".")[-1] if "." in file.filename else "dat"
        unique_name = f"{uuid.uuid4().hex}.{extension}"
        
        file_uri = await storage_service.upload_file(file, unique_name)
        
        return {
            "filename": file.filename,
            "stored_name": unique_name,
            "uri": file_uri,
            "message": "File uploaded successfully. Pass the 'uri' to the agent."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview")
async def preview_file(
    uri: str = Query(...),
    limit: int = Query(10),
    offset: int = Query(0)
):
    """
    Returns a paginated preview of the file data using DuckDB via MCP.
    """
    try:
        result = await data_refinery_mcp.call_tool(
            "preview_dataset", 
            {"file_uri": uri, "limit": limit, "offset": offset}
        )
        # FastMCP might return the tool output differently depending on if it's content list or string
        # If it's the raw string from server.py (which returns json.dumps), we parse it once.
        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch preview: {str(e)}")
