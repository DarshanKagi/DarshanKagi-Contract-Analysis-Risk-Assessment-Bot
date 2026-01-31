"""
PDF Generator Module
Generates professional PDF reports for contract analysis.
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from config import EXPORTS_DIR


def ensure_exports_dir():
    """Ensure the exports directory exists."""
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR)


def get_styles():
    """Get custom paragraph styles for the report."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1e3a5f')
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#2c5282'),
        borderWidth=1,
        borderColor=colors.HexColor('#e2e8f0'),
        borderPadding=5
    ))
    
    # Normal text
    styles.add(ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    ))
    
    # Risk high
    styles.add(ParagraphStyle(
        name='RiskHigh',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#dc2626'),
        backColor=colors.HexColor('#fee2e2'),
        borderPadding=5
    ))
    
    # Risk medium
    styles.add(ParagraphStyle(
        name='RiskMedium',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#d97706'),
        backColor=colors.HexColor('#fef3c7'),
        borderPadding=5
    ))
    
    # Risk low
    styles.add(ParagraphStyle(
        name='RiskLow',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#16a34a'),
        backColor=colors.HexColor('#dcfce7'),
        borderPadding=5
    ))
    
    return styles


def generate_report(analysis: Dict[str, Any], output_path: str = None) -> str:
    """
    Generate a PDF report from contract analysis results.
    
    Args:
        analysis: Analysis results dictionary
        output_path: Optional output path (auto-generated if not provided)
        
    Returns:
        Path to the generated PDF
    """
    ensure_exports_dir()
    
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = analysis.get('filename', 'contract').replace('.', '_')
        output_path = os.path.join(EXPORTS_DIR, f"analysis_{filename}_{timestamp}.pdf")
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = get_styles()
    story = []
    
    # Title
    story.append(Paragraph("Contract Analysis Report", styles['ReportTitle']))
    story.append(Spacer(1, 20))
    
    # Metadata table
    metadata = [
        ['File Analyzed:', analysis.get('filename', 'Unknown')],
        ['Contract Type:', analysis.get('contract_type', 'Unknown')],
        ['Language:', 'Hindi' if analysis.get('language') == 'hi' else 'English'],
        ['Analysis Date:', datetime.now().strftime("%B %d, %Y at %H:%M")],
    ]
    
    metadata_table = Table(metadata, colWidths=[3*cm, 10*cm])
    metadata_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 20))
    
    # Risk Assessment Dashboard
    story.append(Paragraph("1. Risk Assessment Summary", styles['SectionHeader']))
    
    risk_score = analysis.get('overall_risk_score', 0)
    risk_level = analysis.get('overall_risk_level', 'Unknown')
    
    risk_style = 'RiskHigh' if risk_level == 'High' else ('RiskMedium' if risk_level == 'Medium' else 'RiskLow')
    
    risk_text = f"<b>Overall Risk Level: {risk_level}</b> (Score: {risk_score}/100)"
    story.append(Paragraph(risk_text, styles[risk_style]))
    story.append(Spacer(1, 10))
    
    # Risk breakdown
    risk_details = analysis.get('risk_details', {})
    risk_data = [
        ['Risk Category', 'Count'],
        ['High Risk Clauses', str(risk_details.get('high_risk_count', 0))],
        ['Medium Risk Clauses', str(risk_details.get('medium_risk_count', 0))],
        ['Low Risk Clauses', str(risk_details.get('low_risk_count', 0))],
    ]
    
    risk_table = Table(risk_data, colWidths=[8*cm, 4*cm])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("2. Executive Summary", styles['SectionHeader']))
    summary = analysis.get('summary', 'No summary available.')
    # Clean up the summary for PDF
    summary_clean = summary.replace('**', '').replace('*', '')
    story.append(Paragraph(summary_clean, styles['NormalText']))
    story.append(Spacer(1, 15))
    
    # Key Entities
    story.append(Paragraph("3. Key Information Extracted", styles['SectionHeader']))
    
    entities = analysis.get('entities', {})
    parties = entities.get('parties', []) + entities.get('organizations', [])
    amounts = entities.get('amounts', [])
    dates = entities.get('dates', [])
    
    entity_data = [['Category', 'Values']]
    
    if parties:
        entity_data.append(['Parties', ', '.join(parties[:5])])
    if amounts:
        entity_data.append(['Financial Amounts', ', '.join(amounts[:5])])
    if dates:
        entity_data.append(['Key Dates', ', '.join(dates[:5])])
    
    key_terms = analysis.get('key_terms', {})
    if key_terms.get('governing_law'):
        entity_data.append(['Governing Law', key_terms['governing_law']])
    if key_terms.get('notice_period'):
        entity_data.append(['Notice Period', key_terms['notice_period']])
    if key_terms.get('dispute_resolution'):
        entity_data.append(['Dispute Resolution', key_terms['dispute_resolution']])
    
    if len(entity_data) > 1:
        entity_table = Table(entity_data, colWidths=[4*cm, 9*cm])
        entity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(entity_table)
    
    story.append(PageBreak())
    
    # High Risk Clauses
    story.append(Paragraph("4. High Risk Clauses Requiring Attention", styles['SectionHeader']))
    
    clauses = analysis.get('clauses', [])
    high_risk_clauses = [c for c in clauses if c.get('risk_level') == 'High']
    
    if high_risk_clauses:
        for i, clause in enumerate(high_risk_clauses[:5], 1):
            title = f"<b>{i}. {clause.get('title', f'Clause {i}')}</b> - Risk Score: {clause.get('risk_score', 0)}/100"
            story.append(Paragraph(title, styles['RiskHigh']))
            
            story.append(Spacer(1, 5))
            story.append(Paragraph("<b>Original Text:</b>", styles['NormalText']))
            clause_text = clause.get('text', '')[:500]
            if len(clause.get('text', '')) > 500:
                clause_text += "..."
            story.append(Paragraph(clause_text, styles['NormalText']))
            
            if clause.get('explanation'):
                story.append(Spacer(1, 5))
                story.append(Paragraph("<b>Explanation:</b>", styles['NormalText']))
                story.append(Paragraph(clause['explanation'], styles['NormalText']))
            
            if clause.get('suggested_alternative'):
                story.append(Spacer(1, 5))
                story.append(Paragraph("<b>Suggested Alternative:</b>", styles['NormalText']))
                story.append(Paragraph(clause['suggested_alternative'], styles['NormalText']))
            
            story.append(Spacer(1, 15))
    else:
        story.append(Paragraph("No high-risk clauses identified.", styles['NormalText']))
    
    # Compliance Issues
    story.append(Paragraph("5. Compliance Concerns", styles['SectionHeader']))
    
    compliance_issues = analysis.get('compliance_issues', [])
    if compliance_issues:
        for issue in compliance_issues[:5]:
            severity = issue.get('severity', 'Medium')
            style = 'RiskHigh' if severity == 'High' else ('RiskMedium' if severity == 'Medium' else 'RiskLow')
            
            issue_text = f"<b>{issue.get('issue', 'Unknown Issue')}</b>"
            story.append(Paragraph(issue_text, styles[style]))
            
            if issue.get('relevant_law'):
                story.append(Paragraph(f"Relevant Law: {issue['relevant_law']}", styles['NormalText']))
            if issue.get('recommendation'):
                story.append(Paragraph(f"Recommendation: {issue['recommendation']}", styles['NormalText']))
            
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("No significant compliance concerns identified.", styles['NormalText']))
    
    # Recommendations
    story.append(Paragraph("6. Recommendations", styles['SectionHeader']))
    
    recommendations = analysis.get('recommendations', [])
    if recommendations:
        items = []
        for rec in recommendations[:7]:
            items.append(ListItem(Paragraph(rec, styles['NormalText'])))
        story.append(ListFlowable(items, bulletType='bullet'))
    else:
        story.append(Paragraph("No specific recommendations at this time.", styles['NormalText']))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("─" * 50, styles['NormalText']))
    footer_text = """
    <b>Disclaimer:</b> This analysis is generated by an AI system and is intended for informational purposes only. 
    It does not constitute legal advice. Please consult with a qualified legal professional before making 
    any decisions based on this analysis.
    """
    story.append(Paragraph(footer_text, styles['NormalText']))
    
    # Build PDF
    doc.build(story)
    
    return output_path


def generate_report_bytes(analysis: Dict[str, Any]) -> bytes:
    """
    Generate a PDF report and return as bytes (for Gradio download).
    
    Args:
        analysis: Analysis results dictionary
        
    Returns:
        PDF content as bytes
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = get_styles()
    story = []
    
    # Build the same content as generate_report
    # (Simplified version for bytes output)
    
    story.append(Paragraph("Contract Analysis Report", styles['ReportTitle']))
    story.append(Spacer(1, 20))
    
    # Basic info
    story.append(Paragraph(f"<b>File:</b> {analysis.get('filename', 'Unknown')}", styles['NormalText']))
    story.append(Paragraph(f"<b>Type:</b> {analysis.get('contract_type', 'Unknown')}", styles['NormalText']))
    story.append(Paragraph(f"<b>Risk Level:</b> {analysis.get('overall_risk_level', 'Unknown')} ({analysis.get('overall_risk_score', 0)}/100)", styles['NormalText']))
    story.append(Spacer(1, 20))
    
    # Summary
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))
    summary = analysis.get('summary', 'No summary available.').replace('**', '').replace('*', '')
    story.append(Paragraph(summary, styles['NormalText']))
    
    # Recommendations
    story.append(Paragraph("Recommendations", styles['SectionHeader']))
    for rec in analysis.get('recommendations', [])[:5]:
        story.append(Paragraph(f"• {rec}", styles['NormalText']))
    
    doc.build(story)
    
    return buffer.getvalue()
