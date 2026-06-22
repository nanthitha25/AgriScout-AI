import io
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_weekly_report_pdf(startups: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Generate a professional Weekly Market Intelligence PDF report using ReportLab.
    Returns a BytesIO stream containing the generated PDF data.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'), # Slate 900
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#10b981'), # Emerald 500
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1e293b'), # Slate 800
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'), # Slate 700
        spaceAfter=8
    )
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    # 1. Header Section
    story.append(Paragraph("AgriScout AI", title_style))
    story.append(Paragraph(f"AgTech Startup Weekly Market Intelligence Report — {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Executive Summary Metrics
    story.append(Paragraph("Executive Summary", h1_style))
    total_startups = len(startups)
    
    # Break down news types
    funding_count = sum(1 for s in startups if s.get("news_type", "").lower() == "funding")
    launch_count = sum(1 for s in startups if s.get("news_type", "").lower() == "product launch")
    acq_count = sum(1 for s in startups if s.get("news_type", "").lower() == "acquisition")
    partner_count = sum(1 for s in startups if s.get("news_type", "").lower() == "partnership")
    other_count = total_startups - (funding_count + launch_count + acq_count + partner_count)

    summary_text = (
        f"This week, AgriScout AI monitored the global AgTech startup landscape and tracked <b>{total_startups}</b> new "
        f"discoveries. Out of these, <b>{funding_count}</b> are related to funding rounds, <b>{launch_count}</b> represent "
        f"new product launches, <b>{acq_count}</b> acquisitions, <b>{partner_count}</b> strategic partnerships, and <b>{other_count}</b> general updates. "
        "The automated discovery crawler combined Google News RSS indexes and scraped announcements to extract the structured "
        "insights detailed below."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 12))
    
    # 3. Discovery Table
    story.append(Paragraph("New Discoveries Index", h1_style))
    
    table_data = [
        [
            Paragraph("Startup Name", table_header_style),
            Paragraph("Website", table_header_style),
            Paragraph("Country", table_header_style),
            Paragraph("Type", table_header_style),
            Paragraph("Stage", table_header_style),
            Paragraph("Funding", table_header_style)
        ]
    ]
    
    for startup in startups:
        table_data.append([
            Paragraph(startup.get("startup_name", "Unknown"), table_text_style),
            Paragraph(startup.get("startup_website", "Not Mentioned"), table_text_style),
            Paragraph(startup.get("country", "Unknown"), table_text_style),
            Paragraph(startup.get("news_type", "Other"), table_text_style),
            Paragraph(startup.get("funding_stage", "Unknown"), table_text_style),
            Paragraph(startup.get("funding_amount", "Unknown"), table_text_style)
        ])
        
    # Table dimensions: letter size width is 612pt. Margins are 40 + 40 = 80. Usable width = 532pt.
    col_widths = [110, 110, 80, 80, 80, 72]
    
    disc_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')), # Slate 900
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    
    story.append(disc_table)
    story.append(Spacer(1, 15))
    
    # 4. Detailed Breakdown Section
    story.append(Paragraph("Detailed Intel Profiles", h1_style))
    
    for idx, startup in enumerate(startups, 1):
        name = startup.get("startup_name", "Unknown")
        desc = startup.get("brief_description", "No description available.")
        news = startup.get("news_summary", "No news summary available.")
        news_type = startup.get("news_type", "Other")
        stage = startup.get("funding_stage", "Unknown")
        amount = startup.get("funding_amount", "Unknown")
        
        detail_title_style = ParagraphStyle(
            f'DetailTitle_{idx}',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        )
        
        profile_header = f"<b>{idx}. {name}</b> ({startup.get('country', 'Unknown')}) — <i>{news_type}</i>"
        story.append(Paragraph(profile_header, detail_title_style))
        
        meta_info = f"<b>Stage:</b> {stage} | <b>Funding Amount:</b> {amount}"
        story.append(Paragraph(meta_info, body_style))
        
        desc_para = f"<b>Core Technology:</b> {desc}"
        story.append(Paragraph(desc_para, body_style))
        
        news_para = f"<b>Market Insight:</b> {news}"
        story.append(Paragraph(news_para, body_style))
        
        story.append(Spacer(1, 5))

    doc.build(story)
    buffer.seek(0)
    return buffer
