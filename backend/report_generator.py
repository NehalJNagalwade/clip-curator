# report_generator.py — Professional PDF Report Generator (V2)
# Clean white design, meaningful charts, proper report structure

import os
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib import colors

# ── PROFESSIONAL COLOR PALETTE (Light Theme) ──────────────────────────────────
BRAND_PURPLE  = HexColor('#5B21B6')   # Deep purple — brand color
BRAND_PURPLE2 = HexColor('#7C3AED')   # Medium purple
ACCENT_TEAL   = HexColor('#0D9488')   # Teal for timestamps
ACCENT_RED    = HexColor('#DC2626')   # Red for links
PAGE_WHITE    = HexColor('#FFFFFF')
GRAY_50       = HexColor('#F9FAFB')   # Very light gray — card bg
GRAY_100      = HexColor('#F3F4F6')   # Light gray
GRAY_200      = HexColor('#E5E7EB')   # Border gray
GRAY_400      = HexColor('#9CA3AF')   # Muted text
GRAY_600      = HexColor('#4B5563')   # Secondary text
GRAY_800      = HexColor('#1F2937')   # Primary text
GRAY_900      = HexColor('#111827')   # Headings

COVER_BG      = HexColor('#1E1B4B')   # Dark indigo for cover page
COVER_PURPLE  = HexColor('#4338CA')
COVER_LIGHT   = HexColor('#A5B4FC')

# chart colors
CHART_COLORS = [
    '#5B21B6', '#7C3AED', '#0D9488', '#059669',
    '#D97706', '#DC2626', '#2563EB', '#7C3AED',
    '#DB2777', '#65A30D', '#0891B2', '#9333EA'
]

# ── STYLES ────────────────────────────────────────────────────────────────────

def S(name, **kwargs):
    """Quick style creator"""
    defaults = dict(
        fontName='Helvetica',
        fontSize=10,
        textColor=GRAY_800,
        leading=14,
        spaceAfter=4
    )
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)

def get_styles():
    return {
        'cover_title': S('cover_title',
            fontName='Helvetica-Bold', fontSize=32,
            textColor=white, leading=40, spaceAfter=8,
            alignment=TA_LEFT),
        'cover_sub': S('cover_sub',
            fontName='Helvetica', fontSize=14,
            textColor=COVER_LIGHT, leading=20, spaceAfter=6,
            alignment=TA_LEFT),
        'cover_meta': S('cover_meta',
            fontName='Helvetica', fontSize=10,
            textColor=HexColor('#C7D2FE'), leading=16,
            spaceAfter=4, alignment=TA_LEFT),
        'h1': S('h1',
            fontName='Helvetica-Bold', fontSize=18,
            textColor=GRAY_900, leading=24,
            spaceBefore=16, spaceAfter=8, alignment=TA_LEFT),
        'h2': S('h2',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=BRAND_PURPLE, leading=18,
            spaceBefore=12, spaceAfter=6, alignment=TA_LEFT),
        'h3': S('h3',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=GRAY_900, leading=16,
            spaceBefore=8, spaceAfter=4, alignment=TA_LEFT),
        'body': S('body',
            fontName='Helvetica', fontSize=10,
            textColor=GRAY_600, leading=16,
            spaceAfter=6, alignment=TA_JUSTIFY),
        'body_dark': S('body_dark',
            fontName='Helvetica', fontSize=10,
            textColor=GRAY_800, leading=16,
            spaceAfter=4, alignment=TA_LEFT),
        'bullet': S('bullet',
            fontName='Helvetica', fontSize=10,
            textColor=GRAY_600, leading=15,
            leftIndent=14, spaceAfter=4, alignment=TA_LEFT),
        'meta': S('meta',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY_400, leading=13, spaceAfter=2),
        'timestamp': S('timestamp',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=ACCENT_TEAL, leading=13, spaceAfter=2),
        'topic_num': S('topic_num',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=white, leading=14,
            alignment=TA_CENTER),
        'topic_title': S('topic_title',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=GRAY_900, leading=15, spaceAfter=3),
        'topic_body': S('topic_body',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY_600, leading=13,
            spaceAfter=4, alignment=TA_JUSTIFY),
        'footer': S('footer',
            fontName='Helvetica', fontSize=8,
            textColor=GRAY_400, alignment=TA_CENTER),
        'caption': S('caption',
            fontName='Helvetica', fontSize=8,
            textColor=GRAY_400, alignment=TA_CENTER,
            spaceAfter=8),
        'insight': S('insight',
            fontName='Helvetica', fontSize=10,
            textColor=GRAY_800, leading=16,
            spaceAfter=4, alignment=TA_LEFT),
        'link': S('link',
            fontName='Helvetica', fontSize=9,
            textColor=ACCENT_RED, leading=13),
    }

# ── HELPERS ───────────────────────────────────────────────────────────────────

def download_thumbnail(url):
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return io.BytesIO(r.content)
    except:
        pass
    return None

def format_seconds(secs):
    secs = int(secs)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def extract_keywords(topics):
    stop = {
        'the','a','an','and','or','but','in','on','at','to','for','of','with',
        'by','from','is','are','was','were','be','been','have','has','had',
        'do','does','did','will','would','could','should','this','that','it',
        'as','into','also','their','they','how','what','which','who','when',
        'where','all','each','both','such','so','than','more','about','section',
        'covers','discusses','explains','introduces','video','lecture','speaker',
        'including','provides','used','using','use','its','not','can','over',
        'through','between','after','before','during','while','well','most',
        'important','key','topic','topics','discusses','discussed','given'
    }
    words = []
    for t in topics:
        text = (t.get('title','') + ' ' + t.get('summary','')).lower()
        words.extend([w.strip('.,!?;:()[]"\'—-') for w in text.split()
                      if len(w) > 4 and w.strip('.,!?;:()[]"\'—-') not in stop])
    return Counter(words).most_common(10)

def has_varied_durations(topics):
    """Check if topic durations are meaningfully different"""
    if len(topics) < 2:
        return False
    durations = [t.get('end_time',0) - t.get('start_time',0) for t in topics]
    avg = sum(durations) / len(durations)
    variance = sum((d - avg)**2 for d in durations) / len(durations)
    return (variance**0.5) > 30  # std dev > 30 seconds = meaningful variance

# ── CHART: Timeline ───────────────────────────────────────────────────────────

def make_timeline(topics, video_duration):
    if not topics or video_duration == 0:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 1.6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')

    for i, t in enumerate(topics):
        s = t.get('start_time', 0)
        e = t.get('end_time', video_duration)
        color = CHART_COLORS[i % len(CHART_COLORS)]
        ax.barh(0, e - s, left=s, height=0.5,
                color=color, alpha=0.85, edgecolor='white', linewidth=0.8)
        mid = (s + e) / 2
        if (e - s) / video_duration > 0.05:
            ax.text(mid, 0, str(i+1), ha='center', va='center',
                    color='white', fontsize=7.5, fontweight='bold')

    ticks = list(range(0, int(video_duration)+1,
                       max(60, (int(video_duration)//8//60)*60)))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [f"{t//3600}:{(t%3600)//60:02d}" if t>=3600 else f"{t//60}:{t%60:02d}"
         for t in ticks],
        color='#6B7280', fontsize=7.5)
    ax.set_yticks([])
    ax.set_xlim(0, video_duration)
    for spine in ['top','right','left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#E5E7EB')
    plt.tight_layout(pad=0.8)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=140, facecolor='white',
                bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

# ── CHART: Duration (only if varied) ─────────────────────────────────────────

def make_duration_chart(topics, video_duration):
    if not has_varied_durations(topics):
        return None  # Skip if all durations are equal — meaningless chart!

    display = topics[:12]
    fig, ax = plt.subplots(figsize=(7.5, max(2.5, len(display)*0.45)))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')

    titles = []
    durations = []
    pcts = []
    for t in display:
        dur = t.get('end_time',0) - t.get('start_time',0)
        pct = (dur / video_duration * 100) if video_duration > 0 else 0
        title = t.get('title','?')[:28] + ('…' if len(t.get('title','')) > 28 else '')
        titles.append(title)
        durations.append(dur / 60)
        pcts.append(pct)

    colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(titles))]
    bars = ax.barh(range(len(titles)), durations, color=colors,
                   alpha=0.8, height=0.6, edgecolor='none')

    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f'{pct:.1f}%', va='center', ha='left',
                color='#6B7280', fontsize=7.5)

    ax.set_yticks(range(len(titles)))
    ax.set_yticklabels(titles, color='#374151', fontsize=8)
    ax.set_xlabel('Duration (minutes)', color='#6B7280', fontsize=8)
    for spine in ['top','right']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.spines['left'].set_color('#E5E7EB')
    plt.title('Time Spent per Topic (minutes)', color='#1F2937',
              fontsize=9, pad=8, fontweight='bold', loc='left')
    plt.tight_layout(pad=1.2)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=140, facecolor='white',
                bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

# ── CHART: Keywords ───────────────────────────────────────────────────────────

def make_keywords_chart(keywords):
    if not keywords or len(keywords) < 4:
        return None
    words = [k[0].capitalize() for k in keywords[:8]]
    counts = [k[1] for k in keywords[:8]]

    fig, ax = plt.subplots(figsize=(7.5, 2.2))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')

    bars = ax.bar(range(len(words)), counts,
                  color=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(words))],
                  alpha=0.8, width=0.6, edgecolor='none')

    ax.set_xticks(range(len(words)))
    ax.set_xticklabels(words, rotation=25, ha='right',
                       color='#374151', fontsize=8.5)
    ax.set_ylabel('Mentions', color='#6B7280', fontsize=8)
    for spine in ['top','right']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.spines['left'].set_color('#E5E7EB')
    plt.title('Most Mentioned Concepts', color='#1F2937',
              fontsize=9, pad=8, fontweight='bold', loc='left')
    plt.tight_layout(pad=1.2)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=140, facecolor='white',
                bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

# ── COVER PAGE ────────────────────────────────────────────────────────────────

def build_cover(story, styles, video_data, width):
    title = video_data.get('title','Unknown')
    channel = video_data.get('channel','Unknown')
    duration_fmt = video_data.get('duration_formatted','0:00')
    video_id = video_data.get('video_id','')
    topics = video_data.get('topics',[])
    method = video_data.get('transcript_method','captions')
    duration_min = int(video_data.get('duration', 0) / 60)
    generated = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # Dark cover background table
    cover_title_text = title[:70] + ('...' if len(title) > 70 else '')

    # Brand line
    brand = Table([[
        Paragraph('✂  CLIP CURATOR', S('brand_cover',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=COVER_LIGHT, alignment=TA_LEFT)),
        Paragraph('AI Video Report', S('brand_right',
            fontName='Helvetica', fontSize=10,
            textColor=HexColor('#6366F1'), alignment=TA_RIGHT))
    ]], colWidths=[width*0.6, width*0.4])
    brand.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COVER_BG),
        ('PADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))

    # Cover main content
    thumb_buf = download_thumbnail(video_data.get('thumbnail',''))
    thumb_img = None
    if thumb_buf:
        try:
            thumb_img = Image(thumb_buf, width=55*mm, height=31*mm)
        except:
            pass

    # Cover info block
    cover_lines = [
        Paragraph(cover_title_text, styles['cover_title']),
        Spacer(1, 6),
        Paragraph(f'by {channel}', styles['cover_sub']),
        Spacer(1, 12),
        Paragraph(f'⏱  {duration_fmt}  ({duration_min} minutes)', styles['cover_meta']),
        Paragraph(f'🎯  {len(topics)} topics identified', styles['cover_meta']),
        Paragraph(f'📝  Transcript: {"YouTube Captions" if method == "captions" else "Whisper AI"}', styles['cover_meta']),
        Paragraph(f'📅  Generated: {generated}', styles['cover_meta']),
    ]

    if thumb_img:
        cover_row = [[cover_lines, thumb_img]]
        tw = width * 0.55
        cover_table = Table(cover_row, colWidths=[tw, width - tw])
        cover_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COVER_BG),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 20),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
        ]))
    else:
        cover_table = Table([[cover_lines]], colWidths=[width])
        cover_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COVER_BG),
            ('PADDING', (0,0), (-1,-1), 20),
        ]))

    story.append(brand)
    story.append(cover_table)
    story.append(Spacer(1, 16))

    # URL line
    story.append(Paragraph(
        f'<font color="#6366F1">🔗</font>  <font color="#4B5563">youtube.com/watch?v={video_id}</font>',
        S('url', fontName='Helvetica', fontSize=9, textColor=GRAY_600)
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width=width, thickness=1, color=GRAY_200, spaceAfter=4))

# ── SUMMARY SECTION ───────────────────────────────────────────────────────────

def build_summary(story, styles, overall_summary, width):
    story.append(Paragraph('Executive Summary', styles['h1']))
    story.append(HRFlowable(width=width, thickness=1.5,
                             color=BRAND_PURPLE, spaceAfter=10))

    if not overall_summary:
        return

    # Highlighted summary box
    summary_rows = []
    for i, point in enumerate(overall_summary):
        num_cell = Table([[Paragraph(str(i+1), S('snum',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=white, alignment=TA_CENTER))]],
            colWidths=[6*mm])
        num_cell.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BRAND_PURPLE),
            ('PADDING', (0,0), (-1,-1), 3),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        text_cell = Paragraph(point, styles['body'])
        summary_rows.append([num_cell, text_cell])

    sum_table = Table(summary_rows, colWidths=[8*mm, width - 8*mm])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRAY_50),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GRAY_50, HexColor('#EEF2FF')]),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (1,0), (1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.3, GRAY_200),
        ('LINEBEFORE', (0,0), (0,-1), 3, BRAND_PURPLE),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 12))

# ── INSIGHTS SECTION ──────────────────────────────────────────────────────────

def build_insights(story, styles, topics, video_duration, width):
    """Generate smart insights about the video content"""
    if not topics:
        return

    story.append(Paragraph('Key Insights', styles['h1']))
    story.append(HRFlowable(width=width, thickness=1.5,
                             color=BRAND_PURPLE, spaceAfter=10))

    # Insight 1: Longest topic
    durations = [(t.get('end_time',0) - t.get('start_time',0), t) for t in topics]
    longest = max(durations, key=lambda x: x[0])
    shortest = min(durations, key=lambda x: x[0])

    # Insight 2: Coverage
    duration_min = int(video_duration / 60)
    topic_count = len(topics)
    avg_min = int(video_duration / max(topic_count, 1) / 60)

    insights = []

    if longest[0] > 0:
        insights.append(
            f"📌  <b>Most detailed section:</b> \"{longest[1].get('title','?')}\" "
            f"— covers {int(longest[0]//60)}m {int(longest[0]%60)}s "
            f"({int(longest[0]/video_duration*100)}% of video)"
        )

    insights.append(
        f"⏱  <b>Content density:</b> {topic_count} topics across {duration_min} minutes "
        f"— average {avg_min} minutes per topic"
    )

    if topic_count >= 3:
        first_third = [t for t in topics if t.get('start_time',0) < video_duration/3]
        last_third = [t for t in topics
                      if t.get('start_time',0) >= 2*video_duration/3]
        insights.append(
            f"📊  <b>Structure:</b> {len(first_third)} topics in the first third, "
            f"{len(last_third)} topics in the final third of the video"
        )

    keywords = extract_keywords(topics)
    if keywords and len(keywords) >= 3:
        top3 = ', '.join([f'"{k[0]}"' for k in keywords[:3]])
        insights.append(
            f"🔑  <b>Most discussed concepts:</b> {top3} — appearing repeatedly across multiple sections"
        )

    for insight_text in insights:
        row = Table([[Paragraph(insight_text, styles['insight'])]],
                    colWidths=[width])
        row.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), HexColor('#EEF2FF')),
            ('PADDING', (0,0), (-1,-1), 10),
            ('LINEBEFORE', (0,0), (0,-1), 3, BRAND_PURPLE2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(row)
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 6))

# ── TOPICS TABLE ──────────────────────────────────────────────────────────────

def build_topics_table(story, styles, topics, width):
    story.append(Paragraph('Topics at a Glance', styles['h1']))
    story.append(HRFlowable(width=width, thickness=1.5,
                             color=BRAND_PURPLE, spaceAfter=10))

    header = [
        Paragraph('<b>#</b>', S('th', fontName='Helvetica-Bold', fontSize=9,
                                textColor=white, alignment=TA_CENTER)),
        Paragraph('<b>Topic</b>', S('th', fontName='Helvetica-Bold', fontSize=9,
                                   textColor=white, alignment=TA_LEFT)),
        Paragraph('<b>Start</b>', S('th', fontName='Helvetica-Bold', fontSize=9,
                                   textColor=white, alignment=TA_CENTER)),
        Paragraph('<b>End</b>', S('th', fontName='Helvetica-Bold', fontSize=9,
                                 textColor=white, alignment=TA_CENTER)),
        Paragraph('<b>Duration</b>', S('th', fontName='Helvetica-Bold', fontSize=9,
                                      textColor=white, alignment=TA_CENTER)),
    ]
    rows = [header]

    for i, t in enumerate(topics):
        s = t.get('start_time', 0)
        e = t.get('end_time', 0)
        dur = e - s
        dur_str = f"{int(dur//60)}m {int(dur%60)}s"
        bg = PAGE_WHITE if i % 2 == 0 else GRAY_50

        rows.append([
            Paragraph(f'{t.get("topic_number", i+1):02d}',
                      S(f'n{i}', fontName='Helvetica-Bold', fontSize=9,
                        textColor=BRAND_PURPLE, alignment=TA_CENTER)),
            Paragraph(t.get('title','?'),
                      S(f't{i}', fontName='Helvetica', fontSize=9,
                        textColor=GRAY_800, alignment=TA_LEFT)),
            Paragraph(t.get('start_formatted','0:00'),
                      S(f's{i}', fontName='Helvetica-Bold', fontSize=9,
                        textColor=ACCENT_TEAL, alignment=TA_CENTER)),
            Paragraph(t.get('end_formatted','0:00'),
                      S(f'e{i}', fontName='Helvetica', fontSize=9,
                        textColor=GRAY_600, alignment=TA_CENTER)),
            Paragraph(dur_str,
                      S(f'd{i}', fontName='Helvetica', fontSize=9,
                        textColor=GRAY_400, alignment=TA_CENTER)),
        ])

    tbl = Table(rows, colWidths=[10*mm, width-72*mm, 16*mm, 16*mm, 18*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BRAND_PURPLE),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [PAGE_WHITE, GRAY_50]),
        ('GRID', (0,0), (-1,-1), 0.4, GRAY_200),
        ('LINEBELOW', (0,0), (-1,0), 1.5, BRAND_PURPLE2),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 14))

# ── DETAILED NOTES ────────────────────────────────────────────────────────────

def build_detailed_notes(story, styles, topics, video_id, width):
    story.append(PageBreak())
    story.append(Paragraph('Detailed Topic Notes', styles['h1']))
    story.append(HRFlowable(width=width, thickness=1.5,
                             color=BRAND_PURPLE, spaceAfter=12))
    story.append(Paragraph(
        'In-depth summaries for each section with direct YouTube jump links.',
        styles['body']
    ))
    story.append(Spacer(1, 8))

    for i, topic in enumerate(topics):
        num = topic.get('topic_number', i+1)
        title = topic.get('title','?')
        start_fmt = topic.get('start_formatted','0:00')
        end_fmt = topic.get('end_formatted','0:00')
        summary = topic.get('summary','')
        link = topic.get('youtube_link',
               f'https://youtube.com/watch?v={video_id}&t=0s')
        start = topic.get('start_time', 0)
        end = topic.get('end_time', 0)
        dur = end - start
        dur_str = f"{int(dur//60)}m {int(dur%60)}s"

        # Number badge + title row
        badge = Table([[Paragraph(f'{num:02d}', S(f'badge{i}',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=white, alignment=TA_CENTER))]],
            colWidths=[8*mm], rowHeights=[8*mm])
        badge.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BRAND_PURPLE),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))

        header_row = Table([[
            badge,
            Paragraph(title, styles['topic_title']),
            Paragraph(
                f'<font color="#0D9488"><b>{start_fmt}</b></font>'
                f' → <font color="#6B7280">{end_fmt}</font>'
                f'  <font color="#9CA3AF">({dur_str})</font>',
                S(f'ts{i}', fontName='Helvetica', fontSize=9,
                  textColor=ACCENT_TEAL, alignment=TA_RIGHT))
        ]], colWidths=[10*mm, width*0.58, width*0.35])
        header_row.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,-1), GRAY_50),
            ('PADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (1,0), (1,0), 8),
            ('LINEBEFORE', (0,0), (0,-1), 3, BRAND_PURPLE),
            ('LINEBELOW', (0,0), (-1,0), 0.5, GRAY_200),
        ]))

        # Summary + link row
        body_row = Table([[
            Paragraph(''),
            Paragraph(summary, styles['topic_body']),
            Paragraph(f'▶ Jump to {start_fmt}', styles['link'])
        ]], colWidths=[10*mm, width*0.68, width*0.25])
        body_row.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), PAGE_WHITE),
            ('PADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (1,0), (1,0), 8),
            ('RIGHTPADDING', (2,0), (2,0), 6),
            ('LINEBEFORE', (0,0), (0,-1), 3, HexColor('#E0E7FF')),
            ('LINEBELOW', (0,0), (-1,0), 0.5, GRAY_200),
        ]))

        story.append(KeepTogether([header_row, body_row]))
        story.append(Spacer(1, 6))

        if (i+1) % 8 == 0 and i < len(topics)-1:
            story.append(PageBreak())

# ── JUMP LINKS ────────────────────────────────────────────────────────────────

def build_jump_links(story, styles, topics, width):
    story.append(PageBreak())
    story.append(Paragraph('Quick Reference — Jump Links', styles['h1']))
    story.append(HRFlowable(width=width, thickness=1.5,
                             color=BRAND_PURPLE, spaceAfter=8))
    story.append(Paragraph(
        'All timestamps in one place. Open the YouTube link and navigate directly to each topic.',
        styles['body']
    ))
    story.append(Spacer(1, 8))

    link_rows = []
    row = []
    col_w = (width - 4*mm) / 2

    for i, t in enumerate(topics):
        cell_content = [
            Paragraph(
                f'<font color="#7C3AED"><b>{t.get("topic_number",i+1):02d}</b></font>'
                f'  <font color="#0D9488"><b>{t.get("start_formatted","0:00")}</b></font>',
                S(f'lt{i}', fontName='Helvetica-Bold', fontSize=9,
                  textColor=ACCENT_TEAL, alignment=TA_LEFT)
            ),
            Paragraph(
                t.get('title','?')[:40] + ('…' if len(t.get('title','')) > 40 else ''),
                S(f'ln{i}', fontName='Helvetica', fontSize=8.5,
                  textColor=GRAY_600 if i % 2 else GRAY_800, alignment=TA_LEFT)
            ),
        ]
        cell = Table([
            [cell_content[0]],
            [cell_content[1]],
        ], colWidths=[col_w])
        cell.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), GRAY_50),
            ('LINEBEFORE', (0,0), (0,-1), 2.5, BRAND_PURPLE),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (0,0), 6),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        row.append(cell)
        if len(row) == 2:
            link_rows.append(row[:])
            row = []

    if row:
        while len(row) < 2:
            row.append(Paragraph('', styles['body']))
        link_rows.append(row)

    if link_rows:
        grid = Table(link_rows, colWidths=[col_w, col_w],
                     hAlign='LEFT')
        grid.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(grid)

# ── MAIN FUNCTION ─────────────────────────────────────────────────────────────

def generate_report(video_data, output_path):
    styles = get_styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm,
        title=f"Clip Curator — {video_data.get('title','Video Report')}",
    )
    width = A4[0] - 36*mm
    story = []

    topics = video_data.get('topics', [])
    video_duration = video_data.get('duration', 0)

    # 1. Cover
    build_cover(story, styles, video_data, width)
    story.append(Spacer(1, 10))

    # 2. Executive Summary
    build_summary(story, styles, video_data.get('overall_summary',[]), width)

    # 3. Key Insights (auto-generated, meaningful!)
    build_insights(story, styles, topics, video_duration, width)

    # 4. Timeline chart
    story.append(Paragraph('Visual Timeline', styles['h2']))
    timeline_buf = make_timeline(topics, video_duration)
    if timeline_buf:
        story.append(Image(timeline_buf, width=width, height=42*mm))
        story.append(Paragraph('Each colored block represents one topic section.',
                                styles['caption']))
    story.append(Spacer(1, 8))

    # 5. Duration chart (only if meaningful)
    duration_buf = make_duration_chart(topics, video_duration)
    if duration_buf:
        story.append(Paragraph('Topic Duration Breakdown', styles['h2']))
        chart_h = max(45*mm, min(110*mm, len(topics[:12]) * 9*mm))
        story.append(Image(duration_buf, width=width, height=chart_h))
        story.append(Paragraph('Longer bars indicate more time spent on that topic.',
                                styles['caption']))
        story.append(Spacer(1, 8))

    # 6. Keywords chart
    keywords = extract_keywords(topics)
    kw_buf = make_keywords_chart(keywords)
    if kw_buf:
        story.append(Paragraph('Key Concepts', styles['h2']))
        story.append(Image(kw_buf, width=width, height=52*mm))
        story.append(Paragraph(
            'Words appearing most frequently across all topic titles and summaries.',
            styles['caption']
        ))
        story.append(Spacer(1, 8))

    # 7. Topics table
    build_topics_table(story, styles, topics, width)

    # 8. Detailed notes
    build_detailed_notes(story, styles, topics,
                          video_data.get('video_id',''), width)

    # 9. Jump links
    build_jump_links(story, styles, topics, width)

    # 10. Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=width, thickness=0.5,
                              color=GRAY_200, spaceAfter=6))
    story.append(Paragraph(
        f'Generated by <b>Clip Curator</b> — AI YouTube Summarizer  •  '
        f'{datetime.now().strftime("%d %B %Y")}',
        styles['footer']
    ))

    doc.build(story)
    print(f"✅ PDF report generated: {output_path}")
    return output_path