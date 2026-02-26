"""
PDF formatter for professional reports.
"""
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from research_agent.formatters.base import BaseFormatter


class PDFFormatter(BaseFormatter):
    """
    Formatter for PDF output.
    Best for: Professional reports, printable documents, presentations
    """
    
    @property
    def file_extension(self) -> str:
        return "pdf"
    
    def format(
        self, 
        data: List[Dict[str, Any]], 
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Format data as PDF bytes."""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#16213e'),
            spaceAfter=12
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        # Title
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            subtitle_style
        ))
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary
        if metadata and 'summary' in metadata:
            elements.append(Paragraph("Summary", heading_style))
            elements.append(Paragraph(metadata['summary'], body_style))
            elements.append(Spacer(1, 0.2*inch))
        
        # Data sections
        elements.append(Paragraph("Research Findings", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        for i, item in enumerate(data, 1):
            item_title = item.get('title', item.get('name', f"Item {i}"))
            elements.append(Paragraph(f"{i}. {item_title}", styles['Heading3']))
            
            # Create table for item details
            table_data = []
            for key, value in item.items():
                if key in ['title', 'name']:
                    continue
                
                # Format value
                if isinstance(value, list):
                    formatted_value = ", ".join(str(v) for v in value)
                elif isinstance(value, dict):
                    formatted_value = "; ".join(f"{k}: {v}" for k, v in value.items())
                else:
                    formatted_value = str(value)
                
                # Clean up text for PDF
                formatted_value = formatted_value.replace('<', '&lt;').replace('>', '&gt;')
                if len(formatted_value) > 500:
                    formatted_value = formatted_value[:497] + "..."
                
                table_data.append([
                    Paragraph(self._format_key(key), styles['Heading6']),
                    Paragraph(formatted_value, body_style)
                ])
            
            if table_data:
                table = Table(table_data, colWidths=[1.5*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
                ]))
                elements.append(table)
            
            elements.append(Spacer(1, 0.15*inch))
            
            # Add page break every 3 items
            if i % 3 == 0 and i < len(data):
                elements.append(PageBreak())
        
        # Sources
        if metadata and 'sources' in metadata:
            elements.append(PageBreak())
            elements.append(Paragraph("Sources", heading_style))
            for source in metadata['sources']:
                source_text = f"• {source.get('title', 'Unknown')}: {source.get('link', 'N/A')}"
                elements.append(Paragraph(source_text, body_style))
        
        # Build PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _format_key(self, key: str) -> str:
        """Convert snake_case to Title Case."""
        return key.replace('_', ' ').replace('-', ' ').title()
    
    def save(
        self, 
        content: bytes, 
        filename: str
    ) -> Path:
        """Save PDF content to file."""
        filepath = self.output_dir / f"{filename}.pdf"
        filepath.write_bytes(content)
        return filepath
    
    def format_and_save(
        self, 
        data: List[Dict[str, Any]], 
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Format data as PDF and save to file."""
        content = self.format(data, filename, metadata)
        return self.save(content, filename)
