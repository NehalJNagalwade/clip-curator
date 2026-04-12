# clipper.py — Downloads and cuts video clips using range requests
# Uses ffmpeg seeking BEFORE input for faster, smarter clipping
# Works on any video length — just limits clip duration to 5 minutes

import os
import subprocess
import yt_dlp

CLIPS_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'clips')
os.makedirs(CLIPS_FOLDER, exist_ok=True)
FFMPEG_PATH = r'C:\ffmpeg\bin\ffmpeg.exe'

def get_video_stream_url(video_id):
    """
    Gets the direct stream URL from YouTube using yt-dlp.
    This URL is used by ffmpeg to seek and download only the needed part.
    """
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'ffmpeg_location': r'C:\ffmpeg\bin',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        # Get the direct stream URL
        if 'url' in info:
            return info['url']
        # For formats list, pick best mp4
        formats = info.get('formats', [])
        for f in reversed(formats):
            if f.get('ext') == 'mp4' and f.get('url'):
                return f['url']
        # Fallback to any URL
        if formats:
            return formats[-1].get('url')
    return None

def create_clip(video_id, start_time, end_time):
    """
    Creates an MP4 clip using ffmpeg range requests.
    
    Key improvement: -ss is placed BEFORE -i (input seeking)
    This means ffmpeg seeks to the timestamp WITHOUT downloading
    all the video before it. Much faster for long videos!
    
    Works on any video length.
    Clip duration limited to 5 minutes max.
    """
    
    duration = end_time - start_time
    
    # Safety checks
    if duration <= 0:
        raise Exception("End time must be greater than start time.")
    if duration > 300:
        raise Exception("Maximum clip duration is 5 minutes (300 seconds).")

    clip_filename = f"{video_id}_{int(start_time)}_{int(end_time)}.mp4"
    clip_path = os.path.join(CLIPS_FOLDER, clip_filename)

    # If clip already exists, return it directly
    if os.path.exists(clip_path):
        print(f"Clip already exists: {clip_path} ✅")
        return clip_path

    print(f"Getting stream URL for video: {video_id}")
    stream_url = get_video_stream_url(video_id)

    if not stream_url:
        raise Exception("Could not get video stream URL. Video may be restricted.")

    print(f"Cutting clip from {start_time}s to {end_time}s using range requests...")

    # KEY: -ss BEFORE -i for input seeking (much faster — no pre-download!)
    # This seeks to start_time first, then reads only the needed duration
    ffmpeg_command = [
        FFMPEG_PATH,
        '-ss', str(start_time),        # ← BEFORE -i (input seeking, not output seeking)
        '-i', stream_url,              # Direct stream URL (no full download!)
        '-t', str(duration),           # Duration to capture
        '-c:v', 'copy',                # Copy video stream (no re-encoding = fast!)
        '-c:a', 'copy',                # Copy audio stream (no re-encoding = fast!)
        '-avoid_negative_ts', '1',     # Fixes blank/lag at start of clip
        clip_path,
        '-y'                           # Overwrite if exists
    ]

    result = subprocess.run(
        ffmpeg_command,
        capture_output=True,
        text=True,
        timeout=120  # 2 minute timeout
    )

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr[-500:]}")
        raise Exception(f"Clip creation failed. Please try a different timestamp range.")

    if not os.path.exists(clip_path):
        raise Exception("Clip file was not created. Please try again.")

    file_size = os.path.getsize(clip_path)
    if file_size < 1000:
        os.remove(clip_path)
        raise Exception("Clip file is too small — likely empty. Try different timestamps.")

    print(f"✅ Clip created: {clip_path} ({file_size // 1024} KB)")
    return clip_path