import os
import json
import logging
import html
import re
from typing import List, Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

def setup_unicode_font() -> str:
    """
    Registers a TrueType Unicode font supporting multi-language glyphs 
    (Vietnamese, Thai, Southeast Asian scripts, special symbols, etc.).
    """
    font_candidates = [
        # macOS paths
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        # Linux paths
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        # Windows paths
        "C:\\Windows\\Fonts\\arialuni.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    
    font_name = "UnicodeFont"
    for candidate in font_candidates:
        if os.path.exists(candidate):
            try:
                pdfmetrics.registerFont(TTFont(font_name, candidate))
                logger.info(f"Registered Unicode font '{font_name}' from: {candidate}")
                return font_name
            except Exception as e:
                logger.warning(f"Could not load font {candidate}: {e}")
                
    return "Helvetica"


def clean_and_repair_text(text: Any) -> str:
    """
    1. Fixes common HTTP latin1/windows-1252 mojibake.
    2. Escapes HTML/XML special characters (&, <, >) for ReportLab Paragraphs.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    
    text = text.strip()
    if not text:
        return ""
        
    # Attempt Mojibake repair if corrupted byte sequences are detected
    if any(seq in text for seq in ['æ•', 'æŠ', 'ç”', 'èµ', 'ä¿', 'ç‰', 'å·']):
        try:
            repaired = text.encode('windows-1252', errors='ignore').decode('utf-8', errors='ignore')
            if len(repaired) > 0:
                text = repaired
        except Exception:
            pass
            
    return html.escape(text)


def is_valid_policy_record(policy: Dict[str, Any]) -> bool:
    """
    Filters out obvious web scraping noise/spam (forums, download portals, search engines).
    """
    title = str(policy.get("policy_title", "")).lower()
    sources = " ".join(str(s) for s in policy.get("sources", [])).lower()
    
    # Obvious non-policy noise filters
    junk_indicators = [
        "download movies", "baidu", "3dm", "addon", "plugin", "warcraft", 
        "youtube", "tripadvisor", "gep/agree", "board.php"
    ]
    
    if any(junk in title or junk in sources for junk in junk_indicators):
        return False
        
    # Filter out entries where policy title is purely corrupted symbols
    if title in ["ç™¾åº¦é¦–é¡µ", "度页", "unknown", "n/a"]:
        return False
        
    return True


class ReportGenerator:
    def __init__(self, output_path: str = "output/labour_policy_report.pdf"):
        self.output_path = output_path
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
        self.font_name = setup_unicode_font()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Sets up Paragraph styles with full Unicode font support."""
        fn = self.font_name
        
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontName=fn,
            alignment=TA_CENTER,
            fontSize=16,
            leading=20,
            spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name='CountryHeader',
            parent=self.styles['Heading1'],
            fontName=fn,
            fontSize=14,
            leading=18,
            textColor=colors.black,
            spaceBefore=24,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name='IssueHeader',
            parent=self.styles['Heading2'],
            fontName=fn,
            fontSize=12,
            leading=16,
            spaceBefore=16,
            spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name='PolicySubHeader',
            parent=self.styles['Normal'],
            fontName=fn,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceBefore=8,
            spaceAfter=3
        ))
        self.styles.add(ParagraphStyle(
            name='PolicyText',
            parent=self.styles['Normal'],
            fontName=fn,
            fontSize=9,
            spaceAfter=6,
            leading=13
        ))

    def generate_from_file(self, json_file_path: str = "data/policies.json"):
        """Reads policies from JSON and builds the PDF."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                policies = json.load(f)
            self.generate(policies)
        except Exception as e:
            logger.error(f"Failed to generate report from file: {e}")

    def generate(self, policies: List[Dict[str, Any]]):
        """Builds the clean PDF document with verified policies."""
        doc = SimpleDocTemplate(
            self.output_path, 
            pagesize=letter,
            rightMargin=72, 
            leftMargin=72,
            topMargin=72, 
            bottomMargin=36
        )
        
        story = []
        
        # --- TITLE SECTION ---
        story.append(Paragraph("LABOUR MARKET POLICY DEVELOPMENTS", self.styles['ReportTitle']))
        story.append(Paragraph("PEER COUNTRIES", self.styles['ReportTitle']))
        story.append(Paragraph("2024–2026", self.styles['ReportTitle']))
        story.append(Spacer(1, 24))
        
        # --- FILTER & GROUP DATA ---
        grouped_data = {}
        for p in policies:
            if not is_valid_policy_record(p):
                continue
                
            country = clean_and_repair_text(p.get("country", "Unknown")).upper()
            issue = clean_and_repair_text(p.get("labour_market_issue") or p.get("issue") or "Uncategorized")
            
            if country not in grouped_data:
                grouped_data[country] = {}
            if issue not in grouped_data[country]:
                grouped_data[country][issue] = []
            
            grouped_data[country][issue].append(p)
            
        # --- RENDER SECTIONS ---
        for country in sorted(grouped_data.keys()):
            # Country Heading
            story.append(Paragraph(country, self.styles['CountryHeader']))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=16))
            
            issues = grouped_data[country]
            for issue_idx, issue in enumerate(sorted(issues.keys()), 1):
                # Issue Subheading
                story.append(Paragraph(f"{issue_idx}. {issue}", self.styles['IssueHeader']))
                
                for p in issues[issue]:
                    # Policy Title
                    story.append(Paragraph("<b>Policy:</b>", self.styles['PolicySubHeader']))
                    title = clean_and_repair_text(p.get("policy_title", "N/A"))
                    story.append(Paragraph(title, self.styles['PolicyText']))
                    
                    # Status
                    story.append(Paragraph("<b>Status:</b>", self.styles['PolicySubHeader']))
                    status_text = clean_and_repair_text(p.get("status", "N/A"))
                    eff_date = clean_and_repair_text(p.get("effective_date", ""))
                    if eff_date and eff_date != "Unknown":
                        status_text += f" (Effective: {eff_date})"
                    story.append(Paragraph(status_text, self.styles['PolicyText']))
                    
                    # Key Provisions (Bullets)
                    provisions = p.get("key_provisions", [])
                    if provisions:
                        story.append(Paragraph("<b>Key provisions:</b>", self.styles['PolicySubHeader']))
                        bullet_items = [
                            ListItem(Paragraph(clean_and_repair_text(prov), self.styles['PolicyText']))
                            for prov in provisions if clean_and_repair_text(prov)
                        ]
                        if bullet_items:
                            story.append(ListFlowable(bullet_items, bulletType='bullet', spaceAfter=8))
                        
                    # Target Groups
                    t_groups = p.get("target_groups", [])
                    if t_groups:
                        cleaned_tg = [clean_and_repair_text(tg) for tg in t_groups if clean_and_repair_text(tg)]
                        if cleaned_tg:
                            story.append(Paragraph("<b>Target groups:</b>", self.styles['PolicySubHeader']))
                            story.append(Paragraph(", ".join(cleaned_tg), self.styles['PolicyText']))
                        
                    # Labour-market relevance
                    relevance = clean_and_repair_text(p.get("policy_objective", ""))
                    if relevance:
                        story.append(Paragraph("<b>Labour-market relevance:</b>", self.styles['PolicySubHeader']))
                        story.append(Paragraph(relevance, self.styles['PolicyText']))
                        
                    # Sources (Enumerated)
                    sources = p.get("sources", [])
                    if sources:
                        story.append(Paragraph("<b>Sources:</b>", self.styles['PolicySubHeader']))
                        for src_idx, src in enumerate(sources, 1):
                            story.append(Paragraph(f"[{src_idx}] {clean_and_repair_text(src)}", self.styles['PolicyText']))
                            
                    story.append(Spacer(1, 16))
                    
        # Build the PDF
        try:
            doc.build(story)
            logger.info(f"Clean report successfully generated at {self.output_path}")
        except Exception as e:
            logger.error(f"Failed to build PDF report: {e}")
