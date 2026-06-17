import io
from typing import BinaryIO

class FileParser:
    def parse_txt(self, file_content: bytes) -> str:
        return file_content.decode("utf-8", errors="ignore")

    def parse_pdf(self, file_content: bytes) -> str:
        import pdfplumber
        text_content = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return "\n".join(text_content)

    def parse_docx(self, file_content: bytes) -> str:
        import docx
        doc = docx.Document(io.BytesIO(file_content))
        return "\n".join([para.text for para in doc.paragraphs])

    def parse_url(self, url: str) -> str:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted = trafilatura.extract(downloaded)
            return extracted or ""
        return ""

    def parse(self, file_name: str, file_content: bytes) -> str:
        ext = file_name.split(".")[-1].lower()
        if ext == "pdf":
            return self.parse_pdf(file_content)
        elif ext in ["docx", "doc"]:
            return self.parse_docx(file_content)
        elif file_name.startswith("http://") or file_name.startswith("https://"):
            return self.parse_url(file_name)
        else:
            return self.parse_txt(file_content)
