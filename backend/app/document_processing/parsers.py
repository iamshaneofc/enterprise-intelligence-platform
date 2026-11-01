"""Document parsers for PDF, Markdown, Plain Text, CSV, and JSON."""
import io
import csv
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from backend.app.core.exceptions import DocumentProcessingError
from backend.app.core.logging import logger


@dataclass
class ParsedBlock:
    """Represents a coherent section or page of extracted text with structural metadata."""
    text: str
    page_number: int = 1
    section_header: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentParser:
    """Multi-format document parser extracting structured text and section boundaries."""

    @classmethod
    def parse(cls, file_path: str, file_type: str) -> List[ParsedBlock]:
        """Dispatch to appropriate parser based on file extension/type."""
        clean_type = file_type.lower().lstrip(".")
        if clean_type == "pdf":
            return cls.parse_pdf(file_path)
        elif clean_type in ("md", "markdown"):
            return cls.parse_markdown(file_path)
        elif clean_type == "txt":
            return cls.parse_text(file_path)
        elif clean_type == "csv":
            return cls.parse_csv(file_path)
        elif clean_type == "json":
            return cls.parse_json(file_path)
        else:
            raise DocumentProcessingError(f"Unsupported document format: {file_type}")

    @classmethod
    def parse_pdf(cls, file_path: str) -> List[ParsedBlock]:
        """Extract text page by page from PDF using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            blocks = []
            
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if not text:
                    continue
                
                # Check for probable section header in first 3 lines
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                header = lines[0] if lines and len(lines[0]) < 80 else None

                blocks.append(
                    ParsedBlock(
                        text=text,
                        page_number=page_idx + 1,
                        section_header=header,
                        metadata={"total_pages": len(reader.pages)},
                    )
                )
            
            if not blocks:
                logger.warning(f"PDF {file_path} contained no extractable text")
                blocks.append(ParsedBlock(text="[Empty PDF Document]", page_number=1))
            return blocks
        except Exception as e:
            raise DocumentProcessingError(f"Failed to parse PDF document: {str(e)}")

    @classmethod
    def parse_markdown(cls, file_path: str) -> List[ParsedBlock]:
        """Parse Markdown file preserving section headers (# and ##)."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            blocks = []
            current_header = "Introduction"
            current_lines = []
            
            for line in content.splitlines():
                header_match = re.match(r"^(#{1,3})\s+(.*)$", line)
                if header_match:
                    if current_lines:
                        text_block = "\n".join(current_lines).strip()
                        if text_block:
                            blocks.append(
                                ParsedBlock(
                                    text=text_block,
                                    page_number=1,
                                    section_header=current_header,
                                )
                            )
                    current_header = header_match.group(2).strip()
                    current_lines = [line]
                else:
                    current_lines.append(line)

            if current_lines:
                text_block = "\n".join(current_lines).strip()
                if text_block:
                    blocks.append(
                        ParsedBlock(
                            text=text_block,
                            page_number=1,
                            section_header=current_header,
                        )
                    )

            return blocks or [ParsedBlock(text=content.strip(), page_number=1)]
        except Exception as e:
            raise DocumentProcessingError(f"Failed to parse Markdown document: {str(e)}")

    @classmethod
    def parse_text(cls, file_path: str) -> List[ParsedBlock]:
        """Parse plain text file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            return [ParsedBlock(text=content, page_number=1)]
        except Exception as e:
            raise DocumentProcessingError(f"Failed to parse text document: {str(e)}")

    @classmethod
    def parse_csv(cls, file_path: str) -> List[ParsedBlock]:
        """Parse CSV file into formatted tabular text representation."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if not rows:
                return [ParsedBlock(text="[Empty CSV]", page_number=1)]
            
            headers = rows[0]
            blocks = []
            # Group rows into batches of 20
            batch_size = 20
            for i in range(1, len(rows), batch_size):
                chunk_rows = rows[i:i+batch_size]
                text_lines = [f"Columns: {', '.join(headers)}"]
                for r in chunk_rows:
                    formatted_row = " | ".join(f"{h}: {val}" for h, val in zip(headers, r))
                    text_lines.append(formatted_row)
                
                blocks.append(
                    ParsedBlock(
                        text="\n".join(text_lines),
                        page_number=(i // batch_size) + 1,
                        section_header=f"Rows {i} to {min(i + batch_size - 1, len(rows) - 1)}",
                        metadata={"row_count": len(rows)},
                    )
                )
            return blocks
        except Exception as e:
            raise DocumentProcessingError(f"Failed to parse CSV document: {str(e)}")

    @classmethod
    def parse_json(cls, file_path: str) -> List[ParsedBlock]:
        """Parse JSON file into formatted structured text."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            formatted = json.dumps(data, indent=2)
            return [ParsedBlock(text=formatted, page_number=1)]
        except Exception as e:
            raise DocumentProcessingError(f"Failed to parse JSON document: {str(e)}")

