# summarizer.py — Takes transcript segments and creates AI summaries
# Uses HuggingFace's distilbart model (small, fast, free!)

from transformers import pipeline
import math

# ── LOAD THE SUMMARIZATION MODEL ─────────────────────────────────────────────

print("Loading summarization model...")

# This loads the AI summarizer (downloads ~1GB first time)
# "sshleifer/distilbart-cnn-12-6" is a small fast model, perfect for our use
summarizer_pipeline = pipeline(
    "summarization",
    model="sshleifer/distilbart-cnn-12-6",
    device=0  # device=0 means use GPU (your RTX 3050). Use -1 for CPU.
)

print("Summarization model loaded! ✅")

# ── SETTINGS ──────────────────────────────────────────────────────────────────

# How many seconds of transcript to group into one summary chunk
# 120 seconds = 2 minutes per chunk (good balance of detail vs brevity)
CHUNK_DURATION_SECONDS = 120

# ── FUNCTION 1: Group Segments into Chunks ────────────────────────────────────

def group_segments_into_chunks(transcript, chunk_duration=CHUNK_DURATION_SECONDS):
    """
    Takes individual transcript segments and groups them into larger chunks.
    
    Example: If chunk_duration = 120 seconds (2 minutes)
    - Chunk 1: all segments from 0:00 to 2:00
    - Chunk 2: all segments from 2:00 to 4:00
    - etc.
    
    Each chunk will get its own summary.
    """
    
    if not transcript:
        return []
    
    chunks = []
    current_chunk_text = ""
    current_chunk_start = transcript[0]['start']
    last_end = 0
    
    for segment in transcript:
        # Add this segment's text to current chunk
        current_chunk_text += " " + segment['text']
        last_end = segment['end']
        
        # If this chunk has reached our desired duration, save it and start a new one
        if (segment['end'] - current_chunk_start) >= chunk_duration:
            chunks.append({
                'start': current_chunk_start,
                'end': last_end,
                'text': current_chunk_text.strip()
            })
            # Start fresh chunk
            current_chunk_text = ""
            current_chunk_start = segment['end']
    
    # Don't forget the last chunk (it might be shorter than chunk_duration)
    if current_chunk_text.strip():
        chunks.append({
            'start': current_chunk_start,
            'end': last_end,
            'text': current_chunk_text.strip()
        })
    
    return chunks

# ── FUNCTION 2: Summarize One Chunk of Text ───────────────────────────────────

def summarize_text(text):
    """
    Takes a chunk of text and returns a short summary.
    
    Example input:  "Hello and welcome to this lecture on machine learning. 
                     Today we will cover neural networks and how they work..."
    Example output: "This lecture covers machine learning and neural networks."
    """
    
    # The model needs at least 50 characters of text to summarize
    if len(text) < 50:
        return text  # Too short to summarize, just return as-is
    
    # The model can only handle ~1000 words at a time
    # If text is too long, trim it (we already chunk by time, so this is just safety)
    max_chars = 3000
    if len(text) > max_chars:
        text = text[:max_chars]
    
    try:
        # Run the AI summarizer!
        # max_length = maximum words in summary
        # min_length = minimum words in summary  
        # do_sample = False means deterministic (same input = same output)
        result = summarizer_pipeline(
            text,
            max_length=80,
            min_length=20,
            do_sample=False
        )
        
        # result looks like: [{"summary_text": "The summary here..."}]
        return result[0]['summary_text'].strip()
        
    except Exception as e:
        print(f"Summarization error: {e}")
        # If AI fails, return first 150 characters as fallback
        return text[:150] + "..."

# ── FUNCTION 3: Summarize Entire Transcript ───────────────────────────────────

def summarize_transcript(transcript):
    """
    Master function — takes full transcript, returns chunks with summaries.
    
    This is what app.py will call directly.
    
    Returns list like:
    [
        {
            "start": 0,
            "end": 120,
            "start_formatted": "0:00",
            "end_formatted": "2:00", 
            "summary": "Introduction to the topic...",
            "full_text": "Hello and welcome..."
        },
        ...
    ]
    """
    
    print(f"Starting summarization of {len(transcript)} transcript segments...")
    
    # Step 1: Group segments into 2-minute chunks
    chunks = group_segments_into_chunks(transcript)
    print(f"Grouped into {len(chunks)} chunks of ~{CHUNK_DURATION_SECONDS}s each")
    
    # Step 2: Summarize each chunk
    summarized_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i+1}/{len(chunks)}...")
        
        summary = summarize_text(chunk['text'])
        
        summarized_chunks.append({
            'start': chunk['start'],
            'end': chunk['end'],
            'start_formatted': format_time(chunk['start']),  # "1:23" format
            'end_formatted': format_time(chunk['end']),
            'summary': summary,
            'full_text': chunk['text']  # Keep original text too
        })
    
    print(f"Summarization complete! {len(summarized_chunks)} summaries created ✅")
    return summarized_chunks

# ── HELPER: Format seconds into MM:SS ─────────────────────────────────────────

def format_time(seconds):
    """
    Converts seconds to a readable time format.
    
    Example: format_time(125.5) → "2:05"
    Example: format_time(3661) → "61:01"
    """
    seconds = int(seconds)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"