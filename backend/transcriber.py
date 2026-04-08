# transcriber.py — Downloads audio from YouTube and converts speech to text
# Two jobs: 1) Download audio using yt-dlp  2) Transcribe using Whisper

import os
import yt_dlp
from faster_whisper import WhisperModel

# ── SETTINGS ──────────────────────────────────────────────────────────────────

# Where to save downloaded audio files temporarily
AUDIO_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'audio')

# Make sure the audio folder exists (create it if it doesn't)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Which Whisper model to use
# "medium" is accurate and works well on your RTX 3050
# Other options: "tiny" (fastest), "base", "small", "large" (most accurate but slow)
WHISPER_MODEL_SIZE = "medium"
# ── LOAD WHISPER MODEL ────────────────────────────────────────────────────────

print("Loading Whisper model... (first time takes 1-2 minutes to download)")

# "cuda" means use your RTX 3050 GPU — much faster than CPU!
# "int8" means use less memory — perfect for 6GB VRAM
model = WhisperModel(WHISPER_MODEL_SIZE, device="cuda", compute_type="int8")

print("Whisper model loaded! ✅")

# ── FUNCTION 1: Download Audio from YouTube ───────────────────────────────────

def download_audio(youtube_url):
    """
    Takes a YouTube URL and downloads just the audio (not the video).
    Returns the path to the saved audio file.
    
    Example: download_audio("https://youtube.com/watch?v=abc123")
    Returns: "C:/Users/NITRO/clip-curator/audio/abc123.mp3"
    """
    
    print(f"Downloading audio from: {youtube_url}")
    
    # Settings for yt-dlp (the YouTube downloader)
    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(AUDIO_FOLDER, '%(id)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'ffmpeg_location': r'C:\ffmpeg\bin',   # ← THIS LINE ADDED
    'quiet': True,
    'no_warnings': True,
}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # This downloads the video info AND the audio
        info = ydl.extract_info(youtube_url, download=True)
        video_id = info['id']              # e.g. "dQw4w9WgXcQ"
        video_title = info.get('title', 'Unknown Title')
        video_duration = info.get('duration', 0)  # Duration in seconds
    
    # Build the path where the audio was saved
    audio_path = os.path.join(AUDIO_FOLDER, f"{video_id}.mp3")
    
    print(f"Audio downloaded! Saved to: {audio_path} ✅")
    
    return {
        'audio_path': audio_path,
        'video_id': video_id,
        'title': video_title,
        'duration': video_duration
    }

# ── FUNCTION 2: Transcribe Audio to Text with Timestamps ──────────────────────

def transcribe_audio(audio_path):
    """
    Takes an audio file path and converts speech to text.
    Returns a list of segments, each with start time, end time, and text.
    
    Example output:
    [
        {"start": 0.0, "end": 5.2, "text": "Hello and welcome to this lecture"},
        {"start": 5.2, "end": 10.8, "text": "Today we will learn about Python"},
        ...
    ]
    """
    
    print(f"Transcribing audio: {audio_path}")
    print("This may take a few minutes depending on video length...")
    
    # Run Whisper on the audio file
    # beam_size=5 means Whisper considers 5 possible words at each step (more accurate)
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    print(f"Detected language: {info.language} (confidence: {info.language_probability:.0%})")
    
    # Convert segments to a simple list of dictionaries
    transcript = []
    
    for segment in segments:
        transcript.append({
            'start': round(segment.start, 2),   # Start time in seconds e.g. 12.5
            'end': round(segment.end, 2),        # End time in seconds e.g. 18.3
            'text': segment.text.strip()         # The spoken words
        })
    
    print(f"Transcription complete! {len(transcript)} segments found ✅")
    
    return transcript

# ── FUNCTION 3: Do Everything in One Step ─────────────────────────────────────

def process_youtube_url(youtube_url):
    """
    Master function — give it a YouTube URL, get back everything:
    - Video title and duration
    - Full transcript with timestamps
    
    This is what app.py will call directly.
    """
    
    # Step 1: Download the audio
    download_info = download_audio(youtube_url)
    
    # Step 2: Transcribe the audio
    transcript = transcribe_audio(download_info['audio_path'])
    
    # Step 3: Clean up — delete the audio file to save disk space
    # (we don't need it anymore after transcription)
    if os.path.exists(download_info['audio_path']):
        os.remove(download_info['audio_path'])
        print("Temporary audio file deleted ✅")
    
    # Step 4: Return everything together
    return {
        'video_id': download_info['video_id'],
        'title': download_info['title'],
        'duration': download_info['duration'],
        'transcript': transcript   # List of {start, end, text} segments
    }