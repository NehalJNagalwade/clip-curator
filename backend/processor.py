# processor.py — Clip Curator (Complete Working Version)
# Works both locally (with Whisper) and on Render (captions only)

import os
import re
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# Check if Whisper is available (only on local PC)
WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    print("✅ Whisper available (running locally with GPU)")
except ImportError:
    print("ℹ️ Whisper not available (server mode — captions only)")

# ── HELPER: Extract Video ID ──────────────────────────────────────────────────

def extract_video_id(url):
    patterns = [
        r'[?&]v=([^&#]+)',
        r'youtu\.be\/([^?&#]+)',
        r'embed\/([^?&#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ── HELPER: Format time ───────────────────────────────────────────────────────

def format_time(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

# ── FUNCTION 1: Get Video Info ────────────────────────────────────────────────

def get_video_info(video_id):
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False
            )
            return {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': thumbnail_url,
                'channel': info.get('uploader', 'Unknown Channel')
            }
    except Exception as e:
        print(f"Could not get video info: {e}")
        return {
            'title': 'Unknown Title',
            'duration': 0,
            'thumbnail': thumbnail_url,
            'channel': 'Unknown'
        }

# ── FUNCTION 2: Get Transcript ────────────────────────────────────────────────

def get_transcript(video_id, duration_seconds):
    """
    Robust transcript fetching - works on both local and Render
    Tries multiple API methods for maximum compatibility
    """
    print(f"Trying YouTube captions for: {video_id}")

    # Method A: Try using class method (works on older API versions)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        # First try: list_transcripts class method
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            fetched_transcript = None

            # Try English first
            for lang in ['en', 'en-US', 'en-GB', 'en-IN']:
                try:
                    t = transcript_list.find_transcript([lang])
                    fetched_transcript = t.fetch()
                    print(f"✅ Found captions via list method: {lang}")
                    break
                except Exception:
                    continue

            # Try Hindi
            if not fetched_transcript:
                try:
                    t = transcript_list.find_transcript(['hi'])
                    fetched_transcript = t.fetch()
                    print("✅ Found Hindi captions via list method")
                except Exception:
                    pass

            # Try any generated transcript
            if not fetched_transcript:
                try:
                    for t in transcript_list:
                        fetched_transcript = t.fetch()
                        print(f"✅ Found captions: {t.language_code}")
                        break
                except Exception:
                    pass

            if fetched_transcript:
                result = []
                for seg in fetched_transcript:
                    if isinstance(seg, dict):
                        result.append({
                            'text': str(seg.get('text', '')),
                            'start': float(seg.get('start', 0)),
                            'duration': float(seg.get('duration', 0))
                        })
                    else:
                        try:
                            result.append({
                                'text': str(seg.text),
                                'start': float(seg.start),
                                'duration': float(seg.duration)
                            })
                        except Exception:
                            result.append({
                                'text': str(seg),
                                'start': 0.0,
                                'duration': 0.0
                            })

                if result:
                    print(f"✅ Got {len(result)} segments via list method")
                    return result, "captions"

        except Exception as list_error:
            print(f"List method failed: {list_error}")

        # Second try: instance fetch method (newer API versions)
        try:
            ytt = YouTubeTranscriptApi()
            fetched = None

            for lang in [['en', 'en-US', 'en-GB', 'en-IN'], ['hi']]:
                try:
                    fetched = ytt.fetch(video_id, languages=lang)
                    print(f"✅ Found captions via fetch method: {lang}")
                    break
                except Exception:
                    continue

            if fetched is None:
                try:
                    fetched = ytt.fetch(video_id)
                    print("✅ Found captions via default fetch")
                except Exception:
                    pass

            if fetched:
                result = []
                for seg in fetched:
                    if hasattr(seg, 'text'):
                        result.append({
                            'text': str(seg.text),
                            'start': float(seg.start),
                            'duration': float(seg.duration)
                        })
                    elif isinstance(seg, dict):
                        result.append({
                            'text': str(seg.get('text', '')),
                            'start': float(seg.get('start', 0)),
                            'duration': float(seg.get('duration', 0))
                        })

                if result:
                    print(f"✅ Got {len(result)} segments via fetch method")
                    return result, "captions"

        except Exception as fetch_error:
            print(f"Fetch method failed: {fetch_error}")

        raise Exception("All caption methods failed")

    except Exception as caption_error:
        print(f"Captions completely failed: {caption_error}")

        if WHISPER_AVAILABLE and duration_seconds and duration_seconds <= 900:
            print("Falling back to Whisper...")
            try:
                result = get_transcript_whisper(video_id)
                return result, "whisper"
            except Exception as w_err:
                raise Exception(f"Both failed — Captions: {caption_error}, Whisper: {w_err}")
        elif not WHISPER_AVAILABLE:
            raise Exception(
                f"Caption error on server: {str(caption_error)[:200]}. "
                "Please try a video with YouTube captions enabled."
            )
        else:
            raise Exception(
                "No captions available and video too long for Whisper. "
                "Please try a video with captions enabled."
            )

# ── FUNCTION 3: Whisper Fallback ──────────────────────────────────────────────

def get_transcript_whisper(video_id):
    """Only called locally when captions unavailable"""
    from transcriber import download_audio, transcribe_audio
    url = f"https://www.youtube.com/watch?v={video_id}"
    download_info = download_audio(url)
    whisper_segments = transcribe_audio(download_info['audio_path'])
    if os.path.exists(download_info['audio_path']):
        os.remove(download_info['audio_path'])
    return [
        {
            'text': seg['text'],
            'start': seg['start'],
            'duration': seg['end'] - seg['start']
        }
        for seg in whisper_segments
    ]

# ── FUNCTION 4: Build AI Prompt ───────────────────────────────────────────────

def build_prompt(transcript_segments, video_title, video_duration):
    total = len(transcript_segments)
    if total <= 100:
        sampled = transcript_segments
    else:
        step = total // 100
        sampled = transcript_segments[::step][:100]

    full_text = " ".join([seg['text'] for seg in sampled])
    if len(full_text) > 6000:
        full_text = full_text[:6000]

    timestamp_map = []
    last_added = -30
    for seg in transcript_segments:
        if seg['start'] - last_added >= 30:
            timestamp_map.append({
                'time': seg['start'],
                'text': seg['text'][:80]
            })
            last_added = seg['start']

    timestamp_hints = "\n".join([
        f"[{format_time(t['time'])}] {t['text']}"
        for t in timestamp_map[:30]
    ])

    duration_minutes = video_duration / 60
    if duration_minutes <= 5:
        num_topics = "3-4"
    elif duration_minutes <= 15:
        num_topics = "5-7"
    elif duration_minutes <= 30:
        num_topics = "7-10"
    elif duration_minutes <= 60:
        num_topics = "10-12"
    else:
        num_topics = "12-15"

    return f"""You are analyzing a YouTube lecture titled: "{video_title}"
Total video duration: {format_time(video_duration)} ({video_duration} seconds)

Timestamp markers:
{timestamp_hints}

Transcript sample:
{full_text}

STRICT RULES:
1. Create exactly {num_topics} topics covering ENTIRE video 0 to {video_duration} seconds
2. Last topic end_time MUST equal exactly {video_duration}
3. No topic can exceed {video_duration} seconds
4. start_time and end_time must be plain integers

Respond with ONLY this JSON, no extra text:
{{
  "overall_summary": [
    "point 1 about this video",
    "point 2 about key topics covered",
    "point 3 about what viewers will learn",
    "point 4 about the target audience"
  ],
  "topics": [
    {{
      "topic_number": 1,
      "title": "Clear Topic Name",
      "start_time": 0,
      "end_time": 300,
      "summary": "2-3 sentences about this section"
    }}
  ]
}}"""

# ── FUNCTION 5: Groq AI ───────────────────────────────────────────────────────

def call_groq(prompt):
    print("Calling Groq AI...")
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2500
    )
    result = response.choices[0].message.content.strip()
    print("Groq responded! ✅")
    return result

# ── FUNCTION 6: Gemini AI (Backup) ───────────────────────────────────────────

def call_gemini(prompt):
    print("Trying Gemini as backup...")
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    print("Gemini responded! ✅")
    return response.text.strip()

# ── FUNCTION 7: Parse JSON Response ──────────────────────────────────────────

def parse_response(text, video_duration):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    result = json.loads(text)
    for topic in result['topics']:
        if topic['end_time'] > video_duration:
            topic['end_time'] = video_duration
        if topic['start_time'] > video_duration:
            topic['start_time'] = max(0, video_duration - 60)
    return result

# ── FUNCTION 8: Summarize ─────────────────────────────────────────────────────

def summarize(transcript_segments, video_title, video_duration):
    prompt = build_prompt(transcript_segments, video_title, video_duration)

    # Try Groq first
    try:
        return parse_response(call_groq(prompt), video_duration)
    except Exception as groq_err:
        print(f"Groq failed: {groq_err}")

    # Try Gemini backup
    if GEMINI_API_KEY:
        try:
            return parse_response(call_gemini(prompt), video_duration)
        except Exception as gemini_err:
            print(f"Gemini failed: {gemini_err}")

    raise Exception("Both AI services failed. Please try again in a few minutes.")

# ── MASTER FUNCTION ───────────────────────────────────────────────────────────

def process_video(youtube_url):
    print(f"\n{'='*50}")
    print(f"Processing: {youtube_url}")
    print(f"{'='*50}")

    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise Exception("Invalid YouTube URL. Please check and try again.")

    print(f"Video ID: {video_id}")
    video_info = get_video_info(video_id)
    print(f"Title: {video_info['title']}")
    print(f"Duration: {format_time(video_info['duration'])}")

    transcript, method = get_transcript(video_id, video_info['duration'])
    print(f"Transcript method: {method}, segments: {len(transcript)}")

    ai_result = summarize(transcript, video_info['title'], video_info['duration'])

    for topic in ai_result['topics']:
        topic['start_formatted'] = format_time(topic['start_time'])
        topic['end_formatted'] = format_time(topic['end_time'])
        topic['youtube_link'] = (
            f"https://www.youtube.com/watch?v={video_id}"
            f"&t={int(topic['start_time'])}s"
        )

    print(f"✅ Done! {len(ai_result['topics'])} topics")

    return {
        'video_id': video_id,
        'title': video_info['title'],
        'thumbnail': video_info['thumbnail'],
        'channel': video_info['channel'],
        'duration': video_info['duration'],
        'duration_formatted': format_time(video_info['duration']),
        'transcript_method': method,
        'overall_summary': ai_result['overall_summary'],
        'topics': ai_result['topics']
    }