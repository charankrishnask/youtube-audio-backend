import json
from downloader_core import download_audio_from_youtube

def sse_format(data):
    return f"data: {json.dumps(data)}\n\n"

def stream_download(url, convert, keep):
    """Generator function that yields progress updates"""
    
    # Yield initial status
    yield sse_format({
        "status": "starting",
        "message": "Starting download process..."
    })
    
    progress_data = {"last_update": None}
    
    def progress_hook(progress):
        """This is called by yt-dlp on every progress update."""
        current_status = progress.get("status")
        
        # Only yield progress if status changed or significant update
        if current_status == "downloading":
            progress_data["last_update"] = "downloading"
            return {
                "status": "downloading",
                "percent": progress.get("_percent_str", "").strip(),
                "speed": progress.get("_speed_str", "").strip(),
                "eta": progress.get("_eta_str", "").strip(),
            }
        elif current_status == "finished" and progress_data["last_update"] != "finished":
            progress_data["last_update"] = "finished"
            return {
                "status": "converting",
                "message": "Download completed, converting audio..."
            }
        return None

    try:
        # Run download task with progress hook
        results = download_audio_from_youtube(
            url,
            convert_to_mp3=convert,
            keep_original=keep,
            progress_hook=lambda d: progress_hook(d)
        )
        
        # Final completion message
        yield sse_format({
            "status": "completed", 
            "results": results
        })
        
    except Exception as e:
        yield sse_format({
            "status": "error",
            "message": str(e)
        })