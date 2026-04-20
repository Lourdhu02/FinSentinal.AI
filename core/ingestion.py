from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.ocr_parser import OCRParser


@dataclass(slots=True)
class IngestedDocument:
    path: str
    file_type: str
    text: str
    error: str | None = None


class IngestionService:
    SUPPORTED_SUFFIXES = {
        ".pdf": "pdf",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".bmp": "image",
        ".tif": "image",
        ".tiff": "image",
        ".txt": "text",
        ".md": "text",
        ".csv": "text",
        ".json": "text",
        ".xml": "text",
        ".html": "text",
        ".htm": "text",
    }

    def __init__(self, parser: OCRParser | None = None) -> None:
        self.parser = parser or OCRParser()

    def ingest(self, source_path: str | Path) -> list[IngestedDocument]:
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        return [self._ingest_file(file_path) for file_path in self.get_supported_files(path)]

    def ingest_text(self, source_path: str | Path) -> str:
        documents = self.ingest(source_path)
        return "\n\n".join(document.text for document in documents if document.text)

    def detect_file_type(self, file_path: str | Path) -> str:
        return self.SUPPORTED_SUFFIXES.get(Path(file_path).suffix.lower(), "unknown")

    def get_supported_files(self, source_path: str | Path) -> list[Path]:
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        if path.is_file():
            return [path] if path.suffix.lower() in self.SUPPORTED_SUFFIXES else []
        allowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg"}
        return sorted(
            file_path
            for file_path in path.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in allowed_suffixes
        )

    def _ingest_file(self, file_path: Path) -> IngestedDocument:
        file_type = self.detect_file_type(file_path)
        try:
            text = self.parser.parse_path(file_path)
            return IngestedDocument(path=str(file_path), file_type=file_type, text=text)
        except Exception as exc:
            return IngestedDocument(path=str(file_path), file_type=file_type, text="", error=str(exc))
