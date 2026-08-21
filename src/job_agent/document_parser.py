"""PDF text extraction for CVs and cover letters."""

from pathlib import Path

from pypdf import PdfReader


class PdfDocumentParser:
	"""Extract normalized text from a PDF document."""

	def __init__(self, document_path: Path) -> None:
		self.document_path = document_path

	def parse(self) -> str:
		"""Extract non-empty text from every page in document."""
		if self.document_path.suffix.lower() != ".pdf":
			raise ValueError("Document must be a PDF file.")

		if not self.document_path.is_file():
			raise FileNotFoundError(self.document_path)

		reader = PdfReader(self.document_path)
		text = "\n".join(page.extract_text() or "" for page in reader.pages)
		normalized_text = "\n".join(
			line.strip() for line in text.splitlines() if line.strip()
		)

		if not normalized_text:
			raise ValueError("PDF contains no extractable text.")

		return normalized_text
