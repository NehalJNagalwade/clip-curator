# clipper.py — Downloads and cuts a specific portion of a YouTube video
# Uses yt-dlp to download + ffmpeg to cut the exact clip

import os
import subprocess

# ── SETTINGS ──────────────────────────────────────────────────────────────────

# Where to save the downloaded clips
CLIPS_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'clips')
AUDIO_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'audio')

# Make sure folders exist
os.makedirs(CLIPS_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Path to ffmpeg (same fix as transcriber.py)
FFMPEG_PATH = r'C:\ffmpeg\bin\ffmpeg.exe'

# ── MAIN FUNCTION: Download and Cut a Clip ────────────────────────────────────

def create_clip(video_id, start_time, end_time):
    """
    Downloads a YouTube video and cuts out the exact portion you want.
    
    Example:
        create_clip("jNQXAC9IVRw", 10.0, 30.0)
        → Downloads the video
        → Cuts from 10 seconds to 30 seconds
        → Saves as clips/jNQXAC9IVRw_10_30.mp4
        → Returns the path to the saved clip
    
    Arguments:
        video_id   — YouTube video ID (e.g. "jNQXAC9IVRw")
        start_time — Start of clip in seconds (e.g. 10.0)
        end_time   — End of clip in seconds (e.g. 30.0)
    """
    
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Name for the output clip file
    # Example: jNQXAC9IVRw_10_30.mp4
    clip_filename = f"{video_id}_{int(start_time)}_{int(end_time)}.mp4"
    clip_path = os.path.join(CLIPS_FOLDER, clip_filename)
    
    # If clip already exists, no need to re-download!
    if os.path.exists(clip_path):
        print(f"Clip already exists: {clip_path} ✅")
        return clip_path
    
    # Temporary file for the full downloaded video
    temp_video_path = os.path.join(AUDIO_FOLDER, f"{video_id}_temp.mp4")
    
    print(f"Downloading video for clipping: {youtube_url}")
    print(f"Cutting from {start_time}s to {end_time}s")
    
    try:
        # Step 1: Download the full video using yt-dlp
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',   # Download as mp4
            'outtmpl': temp_video_path,         # Save location
            'ffmpeg_location': r'C:\ffmpeg\bin',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        print("Video downloaded! Now cutting clip...")
        
        # Step 2: Cut the exact portion using ffmpeg
        # ffmpeg command explained:
        # -i = input file
        # -ss = start time (seek to this position)
        # -to = end time
        # -c:v copy = copy video without re-encoding (fast!)
        # -c:a copy = copy audio without re-encoding (fast!)
        
        duration = end_time - start_time
        
        ffmpeg_command = [
            FFMPEG_PATH,
            '-i', temp_video_path,      # Input: full video
            '-ss', str(start_time),     # Start time in seconds
            '-t', str(duration),        # Duration (not end time!)
            '-c:v', 'copy',             # Copy video stream (no re-encode)
            '-c:a', 'copy',             # Copy audio stream (no re-encode)
            clip_path,                  # Output: our clip file
            '-y'                        # Overwrite if exists
        ]
        
        # Run the ffmpeg command
        result = subprocess.run(
            ffmpeg_command,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg error: {result.stderr}")
        
        print(f"Clip created successfully: {clip_path} ✅")
        
        # Step 3: Delete the full video (we only need the clip)
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            print("Temporary video file deleted ✅")
        
        return clip_path
        
    except Exception as e:
        # Clean up temp file if something went wrong
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        raise Exception(f"Clip creation failed: {str(e)}")