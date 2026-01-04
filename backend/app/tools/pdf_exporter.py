"""
PDF Export utility for chat sessions.
Generates formatted PDF documents with all messages, agent thoughts, and metadata.
"""

from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    Flowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


class CodeBlock(Flowable):
    """Custom flowable for displaying code blocks with syntax highlighting."""

    def __init__(self, text: str, width=None, height=None):
        super().__init__()
        self.text = text
        self.width = width or 5 * inch
        self.height = height or 0.5 * inch

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(colors.HexColor("#f3f4f6"))
        canvas.rect(0, 0, self.width, self.height, fill=True, stroke=False)
        canvas.setFillColor(colors.HexColor("#1f2937"))
        canvas.setFont("Courier", 9)
        text_obj = canvas.beginText(10, self.height - 15)
        for line in self.text.split("\n")[:20]:  # Limit lines
            text_obj.textLine(line[:100])  # Limit line length
        canvas.drawText(text_obj)


class AgentThoughtBlock(Flowable):
    """Custom flowable for displaying agent thoughts with color coding."""

    def __init__(self, agent_type: str, content: str, width=None, height=None):
        super().__init__()
        self.agent_type = agent_type
        self.content = content
        self.width = width or 5.5 * inch
        self.height = height or 0.3 * inch

    def draw(self):
        canvas = self.canv
        agent_colors = {
            "master": colors.HexColor("#8b5cf6"),  # Purple
            "planner": colors.HexColor("#3b82f6"),  # Blue
            "researcher": colors.HexColor("#22c55e"),  # Green
            "tools": colors.HexColor("#f97316"),  # Orange
            "database": colors.HexColor("#ec4899"),  # Pink
        }
        color = agent_colors.get(self.agent_type, colors.HexColor("#6b7280"))

        # Draw colored border on the left
        canvas.setFillColor(color)
        canvas.rect(0, 0, 5, self.height, fill=True, stroke=False)

        # Draw background
        canvas.setFillColor(colors.HexColor("#f9fafb"))
        canvas.rect(5, 0, self.width - 5, self.height, fill=True, stroke=False)

        # Draw agent label
        canvas.setFillColor(colors.HexColor("#374151"))
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(15, self.height - 18, f"[{self.agent_type.upper()}]")

        # Draw content
        canvas.setFillColor(colors.HexColor("#4b5563"))
        canvas.setFont("Helvetica", 9)
        text_obj = canvas.beginText(15, self.height - 35)
        for line in self.content.split("\n")[:10]:
            text_obj.textLine(line[:80])
        canvas.drawText(text_obj)


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def sanitize_filename(title: str) -> str:
    """Sanitize session title for use in filename."""
    import re

    # Replace special characters with underscores
    filename = re.sub(r"[^\w\s-]", "", title)
    # Replace spaces with underscores
    filename = re.sub(r"\s+", "_", filename)
    # Limit length
    return filename[:50]


def generate_pdf(
    session_data: Dict[str, Any],
    output_path: Optional[str] = None,
    page_size: str = "letter",
) -> BytesIO:
    """
    Generate a PDF document from session data.

    Args:
        session_data: Dictionary containing session and messages
        output_path: Optional path to save PDF file
        page_size: Page size ('letter' or 'A4')

    Returns:
        BytesIO object containing PDF data
    """
    # Set page size
    pagesize = letter if page_size == "letter" else A4

    # Create buffer
    buffer = BytesIO()

    # Create document template
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Create custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1f2937"),
    )

    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor("#374151"),
        borderPadding=5,
        backColor=colors.HexColor("#e5e7eb"),
    )

    user_message_style = ParagraphStyle(
        "UserMessage",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=12,
        textColor=colors.HexColor("#1f2937"),
        leftIndent=20,
        rightIndent=20,
    )

    assistant_message_style = ParagraphStyle(
        "AssistantMessage",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=15,
        textColor=colors.HexColor("#374151"),
        leftIndent=20,
        rightIndent=20,
    )

    metadata_style = ParagraphStyle(
        "Metadata",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=8,
    )

    code_style = ParagraphStyle(
        "Code",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#1f2937"),
        leftIndent=30,
        rightIndent=30,
        spaceBefore=5,
        spaceAfter=5,
        backColor=colors.HexColor("#f3f4f6"),
    )

    # Build story (document content)
    story = []

    # Title
    title = session_data.get("title", "Chat Session")
    story.append(Paragraph(f"Chat Session: {title}", title_style))
    story.append(Spacer(1, 12))

    # Metadata table
    metadata = []
    created_at = session_data.get("created_at", "")
    if created_at:
        metadata.append(
            [
                "Created:",
                format_timestamp(
                    datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                ),
            ]
        )
    updated_at = session_data.get("updated_at", "")
    if updated_at:
        metadata.append(
            [
                "Last Updated:",
                format_timestamp(
                    datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                ),
            ]
        )
    metadata.append(["Session ID:", session_data.get("id", "N/A")])

    if metadata:
        meta_table = Table(metadata, colWidths=[1.5 * inch, 4 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7280")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#374151")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 20))

    # Divider
    story.append(
        Paragraph(
            "─" * 60,
            ParagraphStyle("Divider", parent=styles["Normal"], alignment=TA_CENTER),
        )
    )
    story.append(Spacer(1, 20))

    # Messages
    messages = session_data.get("messages", [])

    for idx, message in enumerate(messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        agent_type = message.get("agent_type")
        created_at_msg = message.get("created_at", "")
        metadata_info = message.get("metadata", {})

        # Message header
        if role == "user":
            header_text = f"👤 USER • {format_timestamp(datetime.fromisoformat(created_at_msg.replace('Z', '+00:00'))) if created_at_msg else ''}"
            story.append(Paragraph(header_text, header_style))
            story.append(Paragraph(content, user_message_style))

        elif role == "assistant":
            header_text = f"🤖 ASSISTANT"
            if agent_type:
                header_text += f" • {agent_type.upper()}"
            if created_at_msg:
                header_text += f" • {format_timestamp(datetime.fromisoformat(created_at_msg.replace('Z', '+00:00'))) if created_at_msg else ''}"

            story.append(Paragraph(header_text, header_style))

            # Check if content contains code blocks
            if "```" in content:
                # Split content by code blocks
                parts = content.split("```")
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        # Regular text
                        if part.strip():
                            story.append(
                                Paragraph(part.strip(), assistant_message_style)
                            )
                    else:
                        # Code block
                        code_lines = part.strip().split("\n")
                        language = code_lines[0] if code_lines else ""
                        code_content = (
                            "\n".join(code_lines[1:]) if len(code_lines) > 1 else ""
                        )
                        if language:
                            story.append(
                                Paragraph(
                                    f"[{language}]",
                                    ParagraphStyle(
                                        "CodeLang",
                                        parent=styles["Normal"],
                                        size=9,
                                        textColor=colors.HexColor("#6b7280"),
                                    ),
                                )
                            )
                        if code_content:
                            code_block = CodeBlock(code_content)
                            story.append(code_block)
            else:
                # Regular content
                story.append(Paragraph(content, assistant_message_style))

            # Check for agent thoughts in metadata
            if metadata_info and isinstance(metadata_info, dict):
                # Check for thinking/thoughts
                if "thinking" in metadata_info or "thoughts" in metadata_info:
                    thoughts = metadata_info.get("thinking") or metadata_info.get(
                        "thoughts"
                    )
                    if thoughts:
                        for thought in (
                            thoughts if isinstance(thoughts, list) else [thoughts]
                        ):
                            if isinstance(thought, dict):
                                agent = thought.get("agent", agent_type or "master")
                                content_t = thought.get("content", "")
                                if content_t:
                                    thought_block = AgentThoughtBlock(agent, content_t)
                                    story.append(thought_block)
                            elif isinstance(thought, str):
                                thought_block = AgentThoughtBlock(
                                    agent_type or "master", thought
                                )
                                story.append(thought_block)

        else:
            # System message
            header_text = f"⚙️ SYSTEM • {format_timestamp(datetime.fromisoformat(created_at_msg.replace('Z', '+00:00'))) if created_at_msg else ''}"
            story.append(Paragraph(header_text, header_style))
            story.append(Paragraph(content, assistant_message_style))

        # Add metadata footer for assistant messages
        if role == "assistant" and metadata_info:
            meta_parts = []
            if metadata_info.get("model"):
                meta_parts.append(f"Model: {metadata_info['model']}")
            if metadata_info.get("tokens"):
                meta_parts.append(f"Tokens: {metadata_info['tokens']}")
            if metadata_info.get("duration"):
                meta_parts.append(f"Duration: {metadata_info['duration']}s")

            if meta_parts:
                meta_text = " • ".join(meta_parts)
                story.append(Paragraph(f"⟳ {meta_text}", metadata_style))

        # Add spacer between messages
        story.append(Spacer(1, 10))

        # Add page break every 5 messages to prevent overflow
        if (idx + 1) % 5 == 0:
            story.append(PageBreak())

    # Build PDF
    doc.build(story)

    # If output path provided, save to file
    if output_path:
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())

    return buffer


def export_session_to_pdf(
    session_data: Dict[str, Any], filename: Optional[str] = None
) -> tuple:
    """
    Export session data to PDF and return filename and PDF data.

    Args:
        session_data: Session data dictionary
        filename: Optional custom filename

    Returns:
        Tuple of (filename, pdf_bytes)
    """
    # Generate filename if not provided
    if not filename:
        title = session_data.get("title", "session")
        date_str = datetime.now().strftime("%Y%m%d")
        sanitized = sanitize_filename(title)
        filename = f"{sanitized}_{date_str}.pdf"

    # Generate PDF
    pdf_buffer = generate_pdf(session_data)

    return filename, pdf_buffer.getvalue()
