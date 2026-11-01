"""Secure local document storage manager."""
import os
import hashlib
import re
from typing import Tuple
from backend.app.core.config import settings
from backend.app.core.exceptions import DocumentProcessingError


# Maximum document content size in characters (prevents pathological inputs)
MAX_CONTENT_CHARS = 1_000_000  # ~1MB of text

# Control characters that are allowed (common whitespace)
_ALLOWED_CONTROL_CHARS = {"\n", "\r", "\t"}


class DocumentStorageManager:
    """Handles secure file persistence, path sanitization, and SHA-256 deduplication."""
    def __init__(self, base_dir: str = settings.STORAGE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    @staticmethod
    def calculate_sha256(content: bytes) -> str:
        """Compute SHA-256 hexadecimal digest of byte payload."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strip dangerous path characters to prevent directory traversal attacks."""
        clean = os.path.basename(filename)
        clean = re.sub(r"[^\w\.\-\s]", "_", clean).strip()
        return clean or "unnamed_document"

    @staticmethod
    def sanitize_content(content: bytes) -> bytes:
        """
        Sanitize document content for safe storage and processing.

        Removes null bytes and disallowed control characters, normalizes
        whitespace, and enforces maximum content length. Does NOT remove
        prompt injection patterns — document content is treated as untrusted
        data at the LLM prompt layer (see rag/prompt_templates.py).

        Args:
            content: Raw document content bytes

        Returns:
            Sanitized content bytes

        Raises:
            DocumentProcessingError: If content exceeds maximum length
        """
        if len(content) > MAX_CONTENT_CHARS:
            raise DocumentProcessingError(
                f"Document content exceeds maximum allowed length of {MAX_CONTENT_CHARS:,} characters"
            )

        # Decode as UTF-8, replacing invalid sequences
        text = content.decode("utf-8", errors="replace")

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove disallowed control characters (keep \n, \r, \t)
        text = "".join(
            ch for ch in text
            if ord(ch) >= 32 or ch in _ALLOWED_CONTROL_CHARS
        )

        # Normalize excessive whitespace (more than 2 consecutive newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.encode("utf-8")

    def save_document(self, workspace_id: str, filename: str, content: bytes) -> Tuple[str, str, int]:
        """
        Validate and save document content to disk.
        Returns: (file_path, sha256_hash, file_size_bytes)
        """
        # Sanitize content before processing
        content = self.sanitize_content(content)

        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise DocumentProcessingError(
                f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
            )

        sanitized = self.sanitize_filename(filename)
        _, ext = os.path.splitext(sanitized.lower())
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise DocumentProcessingError(
                f"File extension '{ext}' is not supported. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        file_hash = self.calculate_sha256(content)
        
        # Workspace-scoped storage folder
        ws_dir = os.path.join(self.base_dir, workspace_id)
        os.makedirs(ws_dir, exist_ok=True)
        
        stored_filename = f"{file_hash[:12]}_{sanitized}"
        target_path = os.path.join(ws_dir, stored_filename)

        with open(target_path, "wb") as f:
            f.write(content)

        return target_path, file_hash, len(content)

    def delete_document(self, file_path: str) -> bool:
        """Remove file from storage if it exists."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False


storage_manager = DocumentStorageManager()

