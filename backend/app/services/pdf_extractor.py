from dataclasses import dataclass
from pathlib import Path

import fitz

@dataclass
class ExtractedPage:
    page_number: int
    text: str

class PDFExtractor:

    def extract(
            self,
            file_path: str,
    ) -> list[ExtractedPage]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"PDF file not found: {file_path}"
            )
        pages: list[ExtractedPage] = []

        with fitz.open(path) as pdf:
            for index, page in enumerate(pdf):
                text = page.get_text("text").strip()

                if not text:
                    continue

                pages.append(
                    ExtractedPage(
                        page_number=index + 1,
                        text=text
                    )
                )
        return pages