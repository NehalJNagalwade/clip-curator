# report_generator.py — Generates beautiful PDF reports for any video
# Uses ReportLab (free, open-source) for PDF creation
# Uses matplotlib for charts embedded in the PDF

import os
import io
import requests
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for servers
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import (
    HexColor, white, black
)
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image, PageBreak, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from datetime import datetime

# ── BRAND COLORS ──────────────────────────────────────────────────────────────
DARK_BG     = HexColor('#0a0a0a')
PURPLE      = HexColor('#6c47ff')
PURPLE_LIGHT= HexColor('#a855f7')
TEAL        = HexColor('#2dd4bf')
RED_ACCENT  = HexColor('#ff4444')
GRAY_DARK   = HexColor('#1a1a1a')
GRAY_MID    = HexColor('#333333')
GRAY_LIGHT  = HexColor('#888888')
WHITE       = HexColor('#ffffff')
GREEN       = HexColor('#4ade80')
AMBER       = HexColor('#fbbf24')
PAGE_BG     = HexColor('#0d0d0d')
CARD_BG     = HexColor('#141414')

# ── STYLES ────────────────────────────────────────────────────────────────────

def get_styles():
    styles = getSampleStyleSheet()

    custom = {
        'title': ParagraphStyle(
            'title',
            fontName='Helvetica-Bold',
            fontSize=28,
            textColor=WHITE,
            spaceAfter=6,
            alignment=TA_LEFT,
            leading=34
        ),
        'subtitle': ParagraphStyle(
            'subtitle',
            fontName='Helvetica',
            fontSize=13,
            textColor=HexColor('#aaaaaa'),
            spaceAfter=4,
            alignment=TA_LEFT
        ),
        'section_header': ParagraphStyle(
            'section_header',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=PURPLE_LIGHT,
            spaceBefore=18,
            spaceAfter=8,
            alignment=TA_LEFT
        ),
        'body': ParagraphStyle(
            'body',
            fontName='Helvetica',
            fontSize=10,
            textColor=HexColor('#cccccc'),
            spaceAfter=6,
            leading=15,
            alignment=TA_LEFT
        ),
        'bullet': ParagraphStyle(
            'bullet',
            fontName='Helvetica',
            fontSize=10,
            textColor=HexColor('#cccccc'),
            spaceAfter=4,
            leading=14,
            leftIndent=12,
            bulletIndent=0,
            alignment=TA_LEFT
        ),
        'topic_title': ParagraphStyle(
            'topic_title',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=WHITE,
            spaceAfter=3,
            alignment=TA_LEFT
        ),
        'topic_body': ParagraphStyle(
            'topic_body',
            fontName='Helvetica',
            fontSize=9,
            textColor=HexColor('#bbbbbb'),
            spaceAfter=4,
            leading=13,
            alignment=TA_LEFT
        ),
        'timestamp': ParagraphStyle(
            'timestamp',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=TEAL,
            spaceAfter=2,
            alignment=TA_LEFT
        ),
        'meta': ParagraphStyle(
            'meta',
            fontName='Helvetica',
            fontSize=9,
            textColor=HexColor('#777777'),
            spaceAfter=2,
            alignment=TA_LEFT
        ),
        'footer': ParagraphStyle(
            'footer',
            fontName='Helvetica',
            fontSize=8,
            textColor=HexColor('#555555'),
            alignment=TA_CENTER
        ),
        'page_num': ParagraphStyle(
            'page_num',
            fontName='Helvetica',
            fontSize=8,
            textColor=HexColor('#555555'),
            alignment=TA_RIGHT
        ),
    }
    return custom

# ── HELPER: Download thumbnail ────────────────────────────────────────────────

def download_thumbnail(thumbnail_url):
    """Downloads video thumbnail and returns as BytesIO object"""
    try:
        response = requests.get(thumbnail_url, timeout=10)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception as e:
        print(f"Could not download thumbnail: {e}")
    return None

# ── HELPER: Extract key words from text ───────────────────────────────────────

def extract_keywords(topics):
    """Extract most common meaningful words from all topic summaries"""
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'shall', 'can', 'this', 'that',
        'these', 'those', 'it', 'its', 'as', 'into', 'also', 'their', 'they',
        'how', 'what', 'which', 'who', 'when', 'where', 'why', 'all', 'each',
        'both', 'such', 'so', 'than', 'more', 'about', 'between', 'through',
        'section', 'covers', 'discusses', 'explains', 'introduces', 'video',
        'lecture', 'speaker', 'including', 'provides', 'used', 'using', 'use'
    }
    all_words = []
    for topic in topics:
        text = (topic.get('title', '') + ' ' + topic.get('summary', '')).lower()
        words = [w.strip('.,!?;:()[]"\'') for w in text.split()]
        all_words.extend([w for w in words if len(w) > 3 and w not in stop_words])

    counter = Counter(all_words)
    return counter.most_common(12)

# ── CHART 1: Topic Duration Bar Chart ────────────────────────────────────────

def create_topic_duration_chart(topics, video_duration):
    """Creates a horizontal bar chart showing time spent per topic"""
    if not topics:
        return None

    # Limit to top 12 topics for readability
    display_topics = topics[:12]

    fig, ax = plt.subplots(figsize=(7, max(3, len(display_topics) * 0.5)))
    fig.patch.set_facecolor('#141414')
    ax.set_facecolor('#0d0d0d')

    titles = []
    durations = []
    percentages = []

    for t in display_topics:
        duration = t.get('end_time', 0) - t.get('start_time', 0)
        pct = (duration / video_duration * 100) if video_duration > 0 else 0
        title = t.get('title', 'Unknown')
        if len(title) > 30:
            title = title[:28] + '...'
        titles.append(title)
        durations.append(duration / 60)  # convert to minutes
        percentages.append(pct)

    colors_list = [
        '#6c47ff', '#a855f7', '#2dd4bf', '#4ade80',
        '#fbbf24', '#f87171', '#60a5fa', '#34d399',
        '#fb923c', '#a78bfa', '#38bdf8', '#f472b6'
    ][:len(titles)]

    bars = ax.barh(range(len(titles)), durations, color=colors_list,
                   alpha=0.85, height=0.6, edgecolor='none')

    for i, (bar, pct) in enumerate(zip(bars, percentages)):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{pct:.1f}%', va='center', ha='left',
                color='#888888', fontsize=7)

    ax.set_yticks(range(len(titles)))
    ax.set_yticklabels(titles, color='#cccccc', fontsize=8)
    ax.set_xlabel('Duration (minutes)', color='#888888', fontsize=8)
    ax.tick_params(colors='#666666', labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#333333')
    ax.spines['left'].set_color('#333333')
    ax.xaxis.label.set_color('#888888')
    ax.set_xlim(0, max(durations) * 1.2 if durations else 1)

    plt.title('Time Distribution by Topic', color='#cccccc', fontsize=10,
              pad=10, fontweight='bold')
    plt.tight_layout(pad=1.5)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=130, facecolor='#141414',
                edgecolor='none', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

# ── CHART 2: Coverage Timeline ────────────────────────────────────────────────

def create_timeline_chart(topics, video_duration):
    """Creates a visual timeline showing topic segments"""
    if not topics or video_duration == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 1.8))
    fig.patch.set_facecolor('#141414')
    ax.set_facecolor('#141414')

    colors_list = [
        '#6c47ff', '#a855f7', '#2dd4bf', '#4ade80',
        '#fbbf24', '#f87171', '#60a5fa', '#34d399',
        '#fb923c', '#a78bfa', '#38bdf8', '#f472b6',
        '#6c47ff', '#a855f7', '#2dd4bf', '#4ade80'
    ]

    for i, topic in enumerate(topics):
        start = topic.get('start_time', 0)
        end = topic.get('end_time', video_duration)
        color = colors_list[i % len(colors_list)]
        ax.barh(0, end - start, left=start, height=0.5,
                color=color, alpha=0.85, edgecolor='#0d0d0d', linewidth=0.5)

        mid = (start + end) / 2
        if (end - start) / video_duration > 0.06:
            ax.text(mid, 0, f'{i+1}', ha='center', va='center',
                    color='white', fontsize=7, fontweight='bold')

    # Time axis labels
    duration_min = int(video_duration / 60)
    ticks = list(range(0, int(video_duration) + 1,
                       max(60, (int(video_duration) // 8 // 60) * 60)))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [f"{t//3600}:{(t%3600)//60:02d}" if t >= 3600 else f"{t//60}:{t%60:02d}"
         for t in ticks],
        color='#888888', fontsize=7
    )
    ax.set_yticks([])
    ax.set_xlim(0, video_duration)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#333333')
    ax.tick_params(bottom=True, left=False, colors='#666666')
    plt.title('Video Timeline — Topic Coverage', color='#cccccc',
              fontsize=9, pad=6, fontweight='bold')
    plt.tight_layout(pad=1.0)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=130, facecolor='#141414',
                edgecolor='none', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

# ── CHART 3: Keywords Visual ──────────────────────────────────────────────────

def create_keywords_chart(keywords):
    """Creates a visual keyword frequency chart"""
    if not keywords or len(keywords) < 3:
        return None

    words = [k[0] for k in keywords[:10]]
    counts = [k[1] for k in keywords[:10]]

    fig, ax = plt.subplots(figsize=(7, 2.5))
    fig.patch.set_facecolor('#141414')
    ax.set_facecolor('#0d0d0d')

    bar_colors = ['#6c47ff' if i == 0 else '#a855f7' if i < 3
                  else '#2dd4bf' if i < 6 else '#4ade80'
                  for i in range(len(words))]

    bars = ax.bar(range(len(words)), counts, color=bar_colors,
                  alpha=0.85, width=0.65, edgecolor='none')

    ax.set_xticks(range(len(words)))
    ax.set_xticklabels(words, rotation=30, ha='right',
                       color='#cccccc', fontsize=8)
    ax.set_ylabel('Frequency', color='#888888', fontsize=8)
    ax.tick_params(colors='#666666', labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#333333')
    ax.spines['left'].set_color('#333333')

    plt.title('Key Topics & Concepts — Frequency', color='#cccccc',
              fontsize=9, pad=8, fontweight='bold')
    plt.tight_layout(pad=1.5)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=130, facecolor='#141414',
                edgecolor='none', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

# ── MAIN FUNCTION: Generate PDF ───────────────────────────────────────────────

def generate_report(video_data, output_path):
    """
    Master function — generates complete PDF report.

    video_data contains:
    - title, channel, duration, duration_formatted
    - thumbnail (URL), video_id
    - overall_summary (list of strings)
    - topics (list of topic dicts)

    output_path: where to save the PDF
    """

    styles = get_styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title=f"Clip Curator Report — {video_data.get('title', 'Video')}",
    )

    story = []
    width = A4[0] - 36*mm  # usable width

    title = video_data.get('title', 'Unknown Video')
    channel = video_data.get('channel', 'Unknown Channel')
    duration_fmt = video_data.get('duration_formatted', '0:00')
    video_duration = video_data.get('duration', 0)
    video_id = video_data.get('video_id', '')
    overall_summary = video_data.get('overall_summary', [])
    topics = video_data.get('topics', [])
    thumbnail_url = video_data.get('thumbnail', '')
    transcript_method = video_data.get('transcript_method', 'captions')
    duration_min = int(video_duration / 60)

    # ── HEADER BANNER ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<font color="#6c47ff">✂</font> <font color="#ffffff"><b>CLIP CURATOR</b></font>', ParagraphStyle(
            'brand', fontName='Helvetica-Bold', fontSize=13,
            textColor=WHITE, alignment=TA_LEFT
        )),
        Paragraph(
            f'<font color="#555555">Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
            ParagraphStyle('gen', fontName='Helvetica', fontSize=8,
                           textColor=HexColor('#555555'), alignment=TA_RIGHT)
        )
    ]]
    header_table = Table(header_data, colWidths=[width*0.6, width*0.4])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BG),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # ── VIDEO INFO + THUMBNAIL ─────────────────────────────────────────────────
    thumb_img = None
    thumb_buf = download_thumbnail(thumbnail_url)
    if thumb_buf:
        try:
            thumb_img = Image(thumb_buf, width=55*mm, height=31*mm)
        except Exception:
            thumb_img = None

    thumb_width = 57*mm if thumb_img else 0
    info_width = width - thumb_width - 5*mm if thumb_img else width

    info_content = [
        Paragraph(title[:80] + ('...' if len(title) > 80 else ''), styles['title']),
        Paragraph(f'📺 {channel}', styles['subtitle']),
        Paragraph(f'⏱ Duration: <b>{duration_fmt}</b>  ({duration_min} minutes)', styles['meta']),
        Paragraph(f'🔗 youtube.com/watch?v={video_id}', styles['meta']),
        Paragraph(
            f'Transcript: <font color="#4ade80">{"✅ YouTube Captions" if transcript_method == "captions" else "🎙 Whisper AI"}</font>',
            styles['meta']
        ),
        Spacer(1, 4),
        Paragraph(f'<font color="#888888">Topics: {len(topics)} sections identified</font>', styles['meta']),
    ]

    if thumb_img:
        info_row = [[info_content, thumb_img]]
        info_table = Table(info_row, colWidths=[info_width, thumb_width])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
            ('PADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
    else:
        info_table = Table([[info_content]], colWidths=[width])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
            ('PADDING', (0,0), (-1,-1), 12),
        ]))

    story.append(info_table)
    story.append(Spacer(1, 14))

    # ── OVERALL SUMMARY ────────────────────────────────────────────────────────
    story.append(Paragraph('📋 Overall Summary', styles['section_header']))
    story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=6))

    if overall_summary:
        summary_rows = []
        for i, point in enumerate(overall_summary):
            bullet_col = Paragraph(
                f'<font color="#6c47ff">▸</font>',
                ParagraphStyle('bul', fontName='Helvetica-Bold', fontSize=11,
                               textColor=PURPLE, alignment=TA_CENTER)
            )
            text_col = Paragraph(point, styles['body'])
            summary_rows.append([bullet_col, text_col])

        summary_table = Table(summary_rows, colWidths=[8*mm, width - 8*mm])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
            ('PADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (0,-1), 10),
            ('TOPPADDING', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 10),
        ]))
        story.append(summary_table)
    story.append(Spacer(1, 14))

    # ── CHARTS ────────────────────────────────────────────────────────────────

    # Timeline chart
    story.append(Paragraph('📊 Topic Coverage Timeline', styles['section_header']))
    story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=6))
    timeline_buf = create_timeline_chart(topics, video_duration)
    if timeline_buf:
        timeline_img = Image(timeline_buf, width=width, height=45*mm)
        story.append(timeline_img)
    story.append(Spacer(1, 10))

    # Duration bar chart
    if len(topics) > 2:
        story.append(Paragraph('📈 Time Distribution by Topic', styles['section_header']))
        story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=6))
        duration_buf = create_topic_duration_chart(topics, video_duration)
        if duration_buf:
            chart_height = max(50*mm, min(120*mm, len(topics[:12]) * 10*mm))
            duration_img = Image(duration_buf, width=width, height=chart_height)
            story.append(duration_img)
        story.append(Spacer(1, 10))

    # Keywords chart
    keywords = extract_keywords(topics)
    if keywords and len(keywords) >= 4:
        story.append(Paragraph('🔑 Key Concepts Frequency', styles['section_header']))
        story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=6))
        kw_buf = create_keywords_chart(keywords)
        if kw_buf:
            kw_img = Image(kw_buf, width=width, height=55*mm)
            story.append(kw_img)
        story.append(Spacer(1, 10))

    # ── TOPIC TABLE ────────────────────────────────────────────────────────────
    story.append(Paragraph('📋 Topics at a Glance', styles['section_header']))
    story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=6))

    table_header = [
        Paragraph('<b>#</b>', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=9, textColor=PURPLE_LIGHT, alignment=TA_CENTER)),
        Paragraph('<b>Topic</b>', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=9, textColor=PURPLE_LIGHT, alignment=TA_LEFT)),
        Paragraph('<b>Start</b>', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=9, textColor=PURPLE_LIGHT, alignment=TA_CENTER)),
        Paragraph('<b>End</b>', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=9, textColor=PURPLE_LIGHT, alignment=TA_CENTER)),
        Paragraph('<b>Duration</b>', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=9, textColor=PURPLE_LIGHT, alignment=TA_CENTER)),
    ]

    table_data = [table_header]
    for i, topic in enumerate(topics):
        start = topic.get('start_time', 0)
        end = topic.get('end_time', 0)
        dur_secs = end - start
        dur_min = dur_secs // 60
        dur_sec = dur_secs % 60
        dur_str = f"{int(dur_min)}m {int(dur_sec)}s"
        bg = CARD_BG if i % 2 == 0 else HexColor('#111111')

        row = [
            Paragraph(f'<font color="#a855f7"><b>{topic.get("topic_number", i+1):02d}</b></font>',
                      ParagraphStyle('num', fontName='Helvetica-Bold', fontSize=9,
                                     textColor=PURPLE_LIGHT, alignment=TA_CENTER)),
            Paragraph(topic.get('title', 'Unknown'), ParagraphStyle('tt',
                      fontName='Helvetica', fontSize=9, textColor=WHITE, alignment=TA_LEFT)),
            Paragraph(topic.get('start_formatted', '0:00'),
                      ParagraphStyle('ts', fontName='Helvetica', fontSize=9,
                                     textColor=TEAL, alignment=TA_CENTER)),
            Paragraph(topic.get('end_formatted', '0:00'),
                      ParagraphStyle('te', fontName='Helvetica', fontSize=9,
                                     textColor=TEAL, alignment=TA_CENTER)),
            Paragraph(dur_str, ParagraphStyle('td', fontName='Helvetica', fontSize=9,
                      textColor=HexColor('#888888'), alignment=TA_CENTER)),
        ]
        table_data.append(row)

    topic_table = Table(table_data,
                        colWidths=[12*mm, width - 80*mm, 18*mm, 18*mm, 18*mm])
    topic_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#1a1a2e')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [CARD_BG, HexColor('#111111')]),
        ('GRID', (0,0), (-1,-1), 0.3, HexColor('#2a2a2a')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 1, PURPLE),
    ]))
    story.append(topic_table)
    story.append(Spacer(1, 14))

    # ── DETAILED TOPIC SECTIONS ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('🎯 Detailed Topic Notes', styles['section_header']))
    story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=10))

    for i, topic in enumerate(topics):
        topic_num = topic.get('topic_number', i + 1)
        topic_title = topic.get('title', 'Unknown Topic')
        start_fmt = topic.get('start_formatted', '0:00')
        end_fmt = topic.get('end_formatted', '0:00')
        summary = topic.get('summary', '')
        youtube_link = topic.get('youtube_link', f'https://youtube.com/watch?v={video_id}')

        start = topic.get('start_time', 0)
        end = topic.get('end_time', 0)
        duration_secs = end - start
        dur_text = f"{int(duration_secs // 60)}m {int(duration_secs % 60)}s"

        topic_content = [
            [
                Paragraph(
                    f'<font color="#a855f7"><b>{topic_num:02d}</b></font>  '
                    f'<font color="#ffffff"><b>{topic_title}</b></font>',
                    ParagraphStyle('th2', fontName='Helvetica-Bold', fontSize=11,
                                   textColor=WHITE, alignment=TA_LEFT)
                ),
                Paragraph(
                    f'<font color="#2dd4bf">{start_fmt} → {end_fmt}</font>  '
                    f'<font color="#555555">({dur_text})</font>',
                    ParagraphStyle('ts2', fontName='Helvetica', fontSize=9,
                                   textColor=TEAL, alignment=TA_RIGHT)
                ),
            ],
            [
                Paragraph(summary, ParagraphStyle(
                    'sb', fontName='Helvetica', fontSize=9,
                    textColor=HexColor('#bbbbbb'), leading=13, alignment=TA_LEFT
                )),
                Paragraph(
                    f'<font color="#ff4444">▶ Open in YouTube</font>',
                    ParagraphStyle('link', fontName='Helvetica', fontSize=8,
                                   textColor=RED_ACCENT, alignment=TA_RIGHT)
                ),
            ]
        ]

        topic_table = Table(topic_content, colWidths=[width * 0.65, width * 0.35])
        topic_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
            ('LEFTBORDERPADDING', (0,0), (0,-1), 0),
            ('LINEBELOWSPACE', (0,0), (-1,0), 0.5),
            ('LINEBEFORE', (0,0), (0,-1), 3, PURPLE),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('SPAN', (0,1), (0,1)),
        ]))
        story.append(topic_table)
        story.append(Spacer(1, 6))

        # Page break after every 6 topics for long videos
        if (i + 1) % 6 == 0 and i < len(topics) - 1:
            story.append(PageBreak())

    # ── JUMP LINKS PAGE ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('🔗 Quick Jump Links', styles['section_header']))
    story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=8))
    story.append(Paragraph(
        'Click any timestamp below to jump directly to that moment on YouTube:',
        styles['body']
    ))
    story.append(Spacer(1, 8))

    # Create 2-column grid of jump links
    link_data = []
    row = []
    for i, topic in enumerate(topics):
        link_cell = Table([[
            Paragraph(
                f'<font color="#a855f7"><b>{topic.get("topic_number", i+1):02d}</b></font>  '
                f'<font color="#2dd4bf">{topic.get("start_formatted", "0:00")}</font>',
                ParagraphStyle('lts', fontName='Helvetica-Bold', fontSize=9,
                               textColor=TEAL, alignment=TA_LEFT)
            ),
        ], [
            Paragraph(
                topic.get('title', 'Unknown')[:35] + ('...' if len(topic.get('title', '')) > 35 else ''),
                ParagraphStyle('ln', fontName='Helvetica', fontSize=8,
                               textColor=HexColor('#cccccc'), alignment=TA_LEFT)
            ),
        ]], colWidths=[(width/2) - 6*mm])
        link_cell.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
            ('LINEBEFORE', (0,0), (0,-1), 2, PURPLE),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 6),
        ]))
        row.append(link_cell)
        if len(row) == 2:
            link_data.append(row)
            row = []

    if row:
        while len(row) < 2:
            row.append(Paragraph('', styles['body']))
        link_data.append(row)

    if link_data:
        links_table = Table(link_data, colWidths=[width/2 - 3*mm, width/2 - 3*mm],
                            hAlign='LEFT')
        links_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(links_table)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width=width, thickness=0.5, color=GRAY_MID, spaceAfter=6))
    story.append(Paragraph(
        f'Generated by <b>Clip Curator</b> — AI YouTube Summarizer  •  '
        f'{datetime.now().strftime("%d %B %Y")}',
        styles['footer']
    ))

    # Build PDF
    doc.build(story)
    print(f"✅ PDF report generated: {output_path}")
    return output_path