# processor.py — Heart of Clip Curator (With Gemini Backup)

import os
import re
import json
from dotenv import load_dotenv
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

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

# ── HELPER: Format seconds to MM:SS or H:MM:SS ───────────────────────────────

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
    try:
        print("Trying YouTube captions...")
        ytt_api = YouTubeTranscriptApi()

        languages_to_try = [
            ['en', 'en-US', 'en-GB', 'en-IN'],
            ['hi'],
            ['en-auto'],
        ]

        fetched = None
        for lang_list in languages_to_try:
            try:
                fetched = ytt_api.fetch(video_id, languages=lang_list)
                print(f"Found captions in: {lang_list}")
                break
            except Exception:
                continue

        if fetched is None:
            try:
                transcript_list_obj = YouTubeTranscriptApi.list_transcripts(video_id)
                first_transcript = next(iter(transcript_list_obj))
                print(f"Using available language: {first_transcript.language_code}")
                fetched = first_transcript.fetch()
            except Exception as e:
                raise Exception(f"No captions available: {e}")

        transcript_result = [
            {
                'text': seg.text,
                'start': seg.start,
                'duration': seg.duration
            }
            for seg in fetched
        ]

        print(f"✅ YouTube captions found! {len(transcript_result)} segments")
        return transcript_result, "captions"

    except Exception as e:
        print(f"No YouTube captions available: {e}")

        if duration_seconds and duration_seconds <= 900:
            print("Falling back to Whisper transcription...")
            try:
                return get_transcript_whisper(video_id), "whisper"
            except Exception as we:
                raise Exception(f"Whisper transcription failed: {we}")
        else:
            raise Exception(
                "This video has no captions available in any language. "
                "Please try a video that has captions enabled."
            )

# ── FUNCTION 3: Whisper Fallback ──────────────────────────────────────────────

def get_transcript_whisper(video_id):
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

# ── FUNCTION 4: Build Prompt ──────────────────────────────────────────────────

def build_prompt(transcript_segments, video_title, video_duration):
    total_segments = len(transcript_segments)
    if total_segments <= 100:
        sampled = transcript_segments
    else:
        step = total_segments // 100
        sampled = transcript_segments[::step][:100]

    full_text = " ".join([seg['text'] for seg in sampled])
    max_chars = 6000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars]

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

    video_duration_formatted = format_time(video_duration)

    return f"""You are analyzing a YouTube lecture titled: "{video_title}"
Total video duration: {video_duration_formatted} ({video_duration} seconds)

Timestamp markers:
{timestamp_hints}

Transcript sample:
{full_text}

STRICT RULES:
1. Create exactly {num_topics} topics covering the ENTIRE video from 0 to {video_duration} seconds
2. Last topic end_time MUST equal exactly {video_duration}
3. No topic end_time can exceed {video_duration}
4. Topics must be evenly spread across the full duration
5. start_time and end_time must be plain integers (seconds only)

Respond with ONLY this JSON format, no extra text:
{{
  "overall_summary": [
    "main point 1 about this video",
    "main point 2 about key topics",
    "main point 3 about what is covered",
    "main point 4 about who this is for"
  ],
  "topics": [
    {{
      "topic_number": 1,
      "title": "Descriptive Topic Title Here",
      "start_time": 0,
      "end_time": 400,
      "summary": "2-3 sentences about what is covered in this section"
    }}
  ]
}}"""

# ── FUNCTION 5: Summarize with Groq (Primary) ────────────────────────────────

def summarize_with_groq(prompt, video_duration):
    print("Trying Groq AI...")
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2500
    )
    ai_response = response.choices[0].message.content.strip()
    print("Groq AI responded! ✅")
    return ai_response

# ── FUNCTION 6: Summarize with Gemini (Backup) ───────────────────────────────

def summarize_with_gemini(prompt, video_duration):
    print("Groq failed — trying Gemini AI as backup...")
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    ai_response = response.text.strip()
    print("Gemini AI responded! ✅")
    return ai_response

# ── FUNCTION 7: Parse AI Response ────────────────────────────────────────────

def parse_ai_response(ai_response, video_duration):
    ai_response = re.sub(r'```json\s*', '', ai_response)
    ai_response = re.sub(r'```\s*', '', ai_response)
    ai_response = ai_response.strip()
    result = json.loads(ai_response)

    # Safety: fix timestamps exceeding video duration
    for topic in result['topics']:
        if topic['end_time'] > video_duration:
            topic['end_time'] = video_duration
        if topic['start_time'] > video_duration:
            topic['start_time'] = max(0, video_duration - 60)

    return result

# ── FUNCTION 8: Master Summarize (tries Groq then Gemini) ────────────────────

def summarize_transcript(transcript_segments, video_title, video_duration):
    print(f"Building prompt for {format_time(video_duration)} video...")
    prompt = build_prompt(transcript_segments, video_title, video_duration)

    # Try Groq first
    try:
        ai_response = summarize_with_groq(prompt, video_duration)
        return parse_ai_response(ai_response, video_duration)
    except Exception as groq_error:
        print(f"Groq failed: {groq_error}")

        # Try Gemini as backup
        if GEMINI_API_KEY:
            try:
                ai_response = summarize_with_gemini(prompt, video_duration)
                return parse_ai_response(ai_response, video_duration)
            except Exception as gemini_error:
                raise Exception(
    f"AI summarization failed. Please try again in a few minutes. Error: {groq_error}"
)
        else:
            raise Exception(
                f"Groq failed and no Gemini key configured. Error: {groq_error}"
            )

# ── MASTER FUNCTION ───────────────────────────────────────────────────────────

def process_video(youtube_url):
    print(f"\n{'='*50}")
    print(f"Processing: {youtube_url}")
    print(f"{'='*50}")

    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise Exception("Invalid YouTube URL. Please check and try again.")
    print(f"Video ID: {video_id}")

    print("Getting video info...")
    video_info = get_video_info(video_id)
    print(f"Title: {video_info['title']}")
    print(f"Duration: {format_time(video_info['duration'])}")

    transcript, method = get_transcript(video_id, video_info['duration'])
    print(f"Transcript method: {method}")

    ai_result = summarize_transcript(
        transcript,
        video_info['title'],
        video_info['duration']
    )

    for topic in ai_result['topics']:
        topic['start_formatted'] = format_time(topic['start_time'])
        topic['end_formatted'] = format_time(topic['end_time'])
        topic['youtube_link'] = (
            f"https://www.youtube.com/watch?v={video_id}"
            f"&t={int(topic['start_time'])}s"
        )

    print(f"✅ Processing complete! Topics: {len(ai_result['topics'])}")

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