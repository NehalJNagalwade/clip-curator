# processor.py — Clip Curator (Render + Local Compatible)

import os
import re
import json
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    print("✅ Whisper available (local mode)")
except ImportError:
    print("ℹ️ Whisper not available (server mode)")

# ── HELPERS ───────────────────────────────────────────────────────────────────

def extract_video_id(url):
    patterns = [
        r'[?&]v=([^&#]+)',
        r'youtu\.be\/([^?&#]+)',
        r'embed\/([^?&#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).split('?')[0].split('&')[0]
    return None

def format_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

# ── VIDEO INFO — No yt-dlp on server (YouTube blocks it) ─────────────────────

def get_video_info(video_id):
    """
    Gets video info without yt-dlp.
    Uses YouTube's oEmbed API (free, no auth needed, works on servers!)
    """
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # Try oEmbed API — always works, no bot detection
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(oembed_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get('title', 'Unknown Title')
            channel = data.get('author_name', 'Unknown Channel')
            print(f"✅ Got video info via oEmbed: {title}")

            # Get duration separately using a different approach
            duration = get_video_duration(video_id)

            return {
                'title': title,
                'duration': duration,
                'thumbnail': thumbnail_url,
                'channel': channel
            }
    except Exception as e:
        print(f"oEmbed failed: {e}")

    # Fallback: try yt-dlp locally (won't work on server but fine locally)
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
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
        print(f"yt-dlp also failed: {e}")

    return {
        'title': 'Unknown Title',
        'duration': 0,
        'thumbnail': thumbnail_url,
        'channel': 'Unknown Channel'
    }

def get_video_duration(video_id):
    """
    Gets video duration using YouTube's noembed API
    Returns duration in seconds
    """
    try:
        # Try noembed.com — gives more info
        resp = requests.get(
            f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}",
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            # noembed doesn't give duration, but we can estimate from transcript later
            pass
    except Exception:
        pass
    return 0  # Duration 0 is fine — we calculate from transcript

# ── TRANSCRIPT ────────────────────────────────────────────────────────────────

def get_transcript(video_id, duration_seconds):
    """
    Gets transcript using youtube-transcript-api v1.2.x
    Only uses instance methods (class methods removed in v1.2)
    """
    print(f"Getting transcript for: {video_id}")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        # v1.2.x uses INSTANCE method, not class method
        ytt = YouTubeTranscriptApi()
        fetched = None

        # Try languages in order
        lang_groups = [
            ['en', 'en-US', 'en-GB', 'en-IN'],
            ['hi'],
            ['en-auto'],
        ]

        for langs in lang_groups:
            try:
                fetched = ytt.fetch(video_id, languages=langs)
                print(f"✅ Captions found: {langs}")
                break
            except Exception as e:
                print(f"  Lang {langs} failed: {e}")
                continue

        # Try without specifying language (gets whatever is available)
        if fetched is None:
            try:
                fetched = ytt.fetch(video_id)
                print("✅ Captions found: default language")
            except Exception as e:
                print(f"  Default fetch failed: {e}")

        if fetched is None:
            raise Exception("No captions available in any language")

        # Convert to our format
        result = []
        for seg in fetched:
            try:
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
            except Exception:
                continue

        if not result:
            raise Exception("Captions found but empty after parsing")

        print(f"✅ Got {len(result)} caption segments")
        return result, "captions"

    except Exception as caption_err:
        print(f"All caption methods failed: {caption_err}")

        # Whisper fallback — local only, short videos only
        if WHISPER_AVAILABLE and duration_seconds and duration_seconds <= 900:
            print("Trying Whisper fallback...")
            try:
                return get_transcript_whisper(video_id), "whisper"
            except Exception as w_err:
                raise Exception(f"Captions: {caption_err} | Whisper: {w_err}")

        raise Exception(
            f"This video has no accessible captions. "
            f"Error: {str(caption_err)[:100]}. "
            f"Please try a video with YouTube captions enabled "
            f"(most lecture and TED videos have captions)."
        )

def get_transcript_whisper(video_id):
    from transcriber import download_audio, transcribe_audio
    url = f"https://www.youtube.com/watch?v={video_id}"
    info = download_audio(url)
    segments = transcribe_audio(info['audio_path'])
    if os.path.exists(info['audio_path']):
        os.remove(info['audio_path'])
    return [
        {'text': s['text'], 'start': s['start'], 'duration': s['end'] - s['start']}
        for s in segments
    ]

# ── AI SUMMARIZATION ──────────────────────────────────────────────────────────

def build_prompt(segments, title, duration):
    total = len(segments)
    sampled = segments if total <= 100 else segments[::total//100][:100]
    full_text = " ".join(s['text'] for s in sampled)[:6000]

    hints = []
    last = -30
    for s in segments:
        if s['start'] - last >= 30:
            hints.append(f"[{format_time(s['start'])}] {s['text'][:80]}")
            last = s['start']
    hint_text = "\n".join(hints[:30])

    mins = duration / 60
    if mins <= 5: topics = "3-4"
    elif mins <= 15: topics = "5-7"
    elif mins <= 30: topics = "7-10"
    elif mins <= 60: topics = "10-12"
    else: topics = "12-15"

    dur_fmt = format_time(duration) if duration > 0 else "unknown"

    return f"""Analyze this YouTube video: "{title}"
Duration: {dur_fmt} ({duration} seconds)

Timestamps:
{hint_text}

Transcript:
{full_text}

Create {topics} topics covering the full video.
Rules:
- Last topic end_time = {duration if duration > 0 else 'end of video'}
- No topic exceeds video duration
- start_time and end_time are integers (seconds)

Return ONLY this JSON:
{{
  "overall_summary": ["point 1", "point 2", "point 3", "point 4"],
  "topics": [
    {{
      "topic_number": 1,
      "title": "Topic Name",
      "start_time": 0,
      "end_time": 120,
      "summary": "What this section covers"
    }}
  ]
}}"""

def call_groq(prompt):
    print("Calling Groq...")
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=2500
    )
    print("Groq ✅")
    return r.choices[0].message.content.strip()

def call_gemini(prompt):
    print("Trying Gemini...")
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    r = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
    print("Gemini ✅")
    return r.text.strip()

def parse_response(text, duration):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text).strip()
    result = json.loads(text)
    for t in result['topics']:
        if duration > 0:
            if t['end_time'] > duration:
                t['end_time'] = duration
            if t['start_time'] > duration:
                t['start_time'] = max(0, duration - 60)
    return result

def summarize(segments, title, duration):
    prompt = build_prompt(segments, title, duration)
    try:
        return parse_response(call_groq(prompt), duration)
    except Exception as e:
        print(f"Groq failed: {e}")
    if GEMINI_API_KEY:
        try:
            return parse_response(call_gemini(prompt), duration)
        except Exception as e:
            print(f"Gemini failed: {e}")
    raise Exception("AI summarization failed. Please try again.")

# ── MASTER FUNCTION ───────────────────────────────────────────────────────────

def process_video(youtube_url):
    print(f"\n{'='*50}\nProcessing: {youtube_url}\n{'='*50}")

    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise Exception("Invalid YouTube URL.")

    print(f"Video ID: {video_id}")

    # Get video info
    info = get_video_info(video_id)
    print(f"Title: {info['title']}, Duration: {format_time(info['duration'])}")

    # Get transcript
    transcript, method = get_transcript(video_id, info['duration'])
    print(f"Transcript: {method}, {len(transcript)} segments")

    # If duration was 0 from oEmbed, calculate from transcript
    duration = info['duration']
    if duration == 0 and transcript:
        last_seg = transcript[-1]
        duration = int(last_seg['start'] + last_seg.get('duration', 0))
        print(f"Duration calculated from transcript: {format_time(duration)}")

    # Summarize
    ai_result = summarize(transcript, info['title'], duration)

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
        'title': info['title'],
        'thumbnail': info['thumbnail'],
        'channel': info['channel'],
        'duration': duration,
        'duration_formatted': format_time(duration),
        'transcript_method': method,
        'overall_summary': ai_result['overall_summary'],
        'topics': ai_result['topics']
    }