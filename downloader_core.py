#!/usr/bin/env python3

import shutil
import subprocess
from pathlib import Path
from yt_dlp import YoutubeDL
import speedtest

# -------------------------
# GLOBAL CONSTANTS
# -------------------------
DOWNLOADS_DIR = Path("downloads")

CONNECTION_THRESHOLDS = [
    (100, 16),
    (50, 8),
    (10, 4),
    (0, 1),
]

def human_readable_size(size_bytes):
    """Convert file size to human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def human_readable_speed(mbps):
    if mbps >= 1000:
        return f"{mbps/1000:.2f} Gbps"
    return f"{mbps:.2f} Mbps"

def measure_download_speed():
    st = speedtest.Speedtest()
    st.get_best_server()
    st.download(threads=None)
    dl_bps = st.results.dict().get("download", 0)
    return dl_bps / 1_000_000.0

def choose_connections(mbps):
    for threshold, conns in CONNECTION_THRESHOLDS:
        if mbps >= threshold:
            return conns
    return 1

def check_tool_exists(tool_name):
    return shutil.which(tool_name) is not None

def safe_outtmpl(output_dir):
    # Create the output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return str(Path(output_dir) / "%(title).200s.%(ext)s")

# -----------------------------------------------------------
# MAIN FUNCTION - Prevent duplicate downloads
# -----------------------------------------------------------
def download_audio_from_youtube(url, output_dir=None, convert_to_mp3=False, keep_original=True, progress_hook=None):
    # Backward compatibility: if output_dir not provided, use old default
    if output_dir is None:
        output_dir = DOWNLOADS_DIR
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("Measuring internet download speed...")
    try:
        mbps = measure_download_speed()
        print(f"Speed: {human_readable_speed(mbps)}")
        connections = choose_connections(mbps)
        print(f"Using {connections} connections")
    except Exception:
        mbps = 0
        connections = 1
        print("Speed test failed, using default connection")

    use_aria2 = check_tool_exists("aria2c") and connections > 1

    external_downloader = "aria2c" if use_aria2 else None
    external_downloader_args = ["-x", str(connections), "-s", str(connections), "-k", "1M"] if use_aria2 else []

    ytdlp_opts = {
        "format": "bestaudio/best",
        "outtmpl": safe_outtmpl(output_dir),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
        "ignoreerrors": False,
        "postprocessors": [],
        "skip_download": False,
        "external_downloader": external_downloader,
        "external_downloader_args": external_downloader_args,
        "writeinfojson": False,
        # Prevent duplicate downloads by overwriting existing files
        "overwrites": True,
    }

    if progress_hook:
        ytdlp_opts["progress_hooks"] = [progress_hook]

    try:
        with YoutubeDL(ytdlp_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed: {e}")

    # ---- FILE DETECTION ----
    downloaded_file = None

    if "requested_downloads" in info:
        for req in info["requested_downloads"]:
            fp = req.get("filepath")
            if fp and Path(fp).exists():
                downloaded_file = Path(fp)
                break

    if not downloaded_file and "filepath" in info:
        fp = info["filepath"]
        if fp and Path(fp).exists():
            downloaded_file = Path(fp)

    if not downloaded_file:
        # Try to find the most recently created file in the output directory
        files = list(output_path.glob("*"))
        if files:
            downloaded_file = max(files, key=lambda x: x.stat().st_mtime)

    if not downloaded_file:
        raise RuntimeError("Could not find downloaded audio file.")

    print("Downloaded:", downloaded_file)
    
    # SIMPLIFIED OUTPUT FORMAT
    video_title = info.get('title', 'Unknown Title')
    results = {
        "title": video_title,
        "status": "success",
        "files": []
    }

    # Add original file info
    if downloaded_file.exists():
        results["files"].append({
            "name": downloaded_file.name,
            "type": "original",
            "size": human_readable_size(downloaded_file.stat().st_size),
            "format": downloaded_file.suffix.replace('.', '').upper()
        })

    # ---- MP3 conversion ----
    if convert_to_mp3:
        if not check_tool_exists("ffmpeg"):
            raise RuntimeError("ffmpeg not found")

        mp3_path = output_path / (downloaded_file.stem + ".mp3")
        
        # Remove existing MP3 file if it exists (prevent duplicates)
        if mp3_path.exists():
            mp3_path.unlink()
            print("Removed existing MP3 file to prevent duplicates")

        cmd = [
            "ffmpeg", "-y",  # -y to overwrite output file
            "-i", str(downloaded_file),
            "-vn",
            "-codec:a", "libmp3lame",
            "-b:a", "320k",
            str(mp3_path)
        ]

        print("Converting to MP3...")
        subprocess.run(cmd, check=True, capture_output=True)
        print("MP3 saved:", mp3_path)
        
        # Add MP3 file info
        if mp3_path.exists():
            results["files"].append({
                "name": mp3_path.name,
                "type": "mp3",
                "size": human_readable_size(mp3_path.stat().st_size),
                "format": "MP3"
            })

        if not keep_original and downloaded_file.exists():
            downloaded_file.unlink()
            # Remove original from results if deleted
            results["files"] = [f for f in results["files"] if f["type"] != "original"]
            print("Original file removed as requested")

    return results