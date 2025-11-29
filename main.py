from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from downloader_core import download_audio_from_youtube
from progress import stream_download
from fastapi import BackgroundTasks
from pathlib import Path
import shutil
import time
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DownloadRequest(BaseModel):
    url: str
    convert_mp3: bool
    keep_original: bool

# Temporary directory for web downloads
TEMP_DOWNLOAD_DIR = Path("temp_downloads")
TEMP_DOWNLOAD_DIR.mkdir(exist_ok=True)

def cleanup_temp_files():
    """Clean up temporary files older than 1 hour"""
    current_time = time.time()
    for file_path in TEMP_DOWNLOAD_DIR.glob("*"):
        if file_path.is_file() and (current_time - file_path.stat().st_mtime) > 3600:
            try:
                file_path.unlink()
                print(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                print(f"Error cleaning up {file_path}: {e}")
        elif file_path.is_dir():
            try:
                if (current_time - file_path.stat().st_mtime) > 3600:
                    shutil.rmtree(file_path)
                    print(f"Cleaned up temp directory: {file_path}")
            except Exception as e:
                print(f"Error cleaning up directory {file_path}: {e}")

def cleanup_file(temp_dir: Path):
    """Clean up temporary directory after download"""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"Cleaned up download directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning up {temp_dir}: {e}")

@app.get("/download-stream")
async def download_stream(url: str, convert_mp3: str, keep_original: str):
    """Endpoint for streaming download progress (for progress updates)"""
    convert_mp3 = convert_mp3.lower() == "true"
    keep_original = keep_original.lower() == "true"

    generator = stream_download(url, convert_mp3, keep_original)
    return StreamingResponse(generator, media_type="text/event-stream")

@app.post("/download-file")
async def download_file(request: DownloadRequest, background_tasks: BackgroundTasks):
    """MAIN ENDPOINT - Direct file download that triggers browser save dialog"""
    try:
        print(f"Starting download for URL: {request.url}")
        print(f"Options - MP3: {request.convert_mp3}, Keep Original: {request.keep_original}")
        
        # Use temp directory for web downloads
        temp_dir = TEMP_DOWNLOAD_DIR / f"download_{hash(request.url)}_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Downloading to temporary directory: {temp_dir}")
        
        # Download the file
        result = download_audio_from_youtube(
            url=request.url,
            output_dir=str(temp_dir),
            convert_to_mp3=request.convert_mp3,
            keep_original=request.keep_original
        )
        
        print(f"Download result: {result}")
        
        # Find the file to serve (MP3 if converted, otherwise original)
        file_to_serve = None
        file_type = None
        
        # Priority: MP3 if requested and available
        if request.convert_mp3:
            for file_info in result.get("files", []):
                if file_info["type"] == "mp3":
                    file_to_serve = Path(temp_dir) / file_info["name"]
                    file_type = "mp3"
                    break
        
        # If no MP3 found or not requested, look for original
        if not file_to_serve:
            for file_info in result.get("files", []):
                if file_info["type"] == "original":
                    file_to_serve = Path(temp_dir) / file_info["name"]
                    file_type = "original"
                    break
        
        if not file_to_serve or not file_to_serve.exists():
            print(f"File not found. Available files: {list(temp_dir.glob('*'))}")
            raise HTTPException(status_code=404, detail="Downloaded file not found")
        
        print(f"Serving file: {file_to_serve} (Type: {file_type})")
        
        # Determine media type and filename
        filename = file_to_serve.name
        if file_to_serve.suffix.lower() == '.mp3':
            media_type = 'audio/mpeg'
        elif file_to_serve.suffix.lower() in ['.webm', '.m4a', '.ogg']:
            media_type = 'audio/*'
        else:
            media_type = 'application/octet-stream'
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_file, temp_dir)
        
        # Return the file - this will trigger browser download dialog
        return FileResponse(
            path=file_to_serve,
            filename=filename,
            media_type=media_type,
            background=background_tasks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/file")
async def get_file(path: str, background_tasks: BackgroundTasks):
    """Legacy endpoint to serve files with cleanup"""
    try:
        path = Path(path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Schedule cleanup for temp files
        if "temp_downloads" in str(path):
            background_tasks.add_task(cleanup_file, path.parent)
        
        # Determine media type
        if path.suffix.lower() == '.mp3':
            media_type = 'audio/mpeg'
        else:
            media_type = 'audio/*'
        
        return FileResponse(
            path,
            media_type=media_type,
            filename=path.name,
            background=background_tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "YouTube Audio Downloader API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

# Cleanup on startup
@app.on_event("startup")
async def startup_event():
    cleanup_temp_files()
    print("YouTube Audio Downloader API started successfully!")