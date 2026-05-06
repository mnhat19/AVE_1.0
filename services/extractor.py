from pathlib import Path
from email import policy
from email.parser import BytesParser

import pandas as pd
import pdfplumber
import pytesseract
from docx import Document
from PIL import Image


def extract_pdf(path: str) -> dict:
    text_parts: list[str] = []
    tables: list[dict] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text_parts.append(page.extract_text() or "")
                page_tables = page.extract_tables() or []
                for table_index, table in enumerate(page_tables, start=1):
                    if not table:
                        continue
                    tables.append({"page": page_index, "index": table_index, "rows": table})
            page_count = len(pdf.pages)
    except Exception as exc:
        return {"type": "text", "content": "", "error": f"pdf_parse_error:{exc}"}
    return {
        "type": "text",
        "content": "\n".join(text_parts),
        "pages": page_count,
        "tables": tables,
    }


def extract_docx(path: str) -> dict:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    tables = []
    for table in doc.tables:
        rows = [[cell.text for cell in row.cells] for row in table.rows]
        tables.append(rows)
    return {"type": "text", "content": "\n".join(paragraphs), "tables": tables}


def extract_excel(path: str) -> dict:
    xl = pd.ExcelFile(path)
    sheets = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        sheets[sheet] = df.to_dict(orient="records")
    return {"type": "table", "content": sheets, "sheet_names": xl.sheet_names}


def extract_csv(path: str) -> dict:
    df = pd.read_csv(path, encoding="utf-8-sig")
    return {"type": "table", "content": df.to_dict(orient="records"), "columns": list(df.columns)}


def extract_text(path: str) -> dict:
    content = Path(path).read_text(encoding="utf-8", errors="ignore")
    return {"type": "text", "content": content}


def extract_image(path: str) -> dict:
    img = Image.open(path)
    try:
        text = pytesseract.image_to_string(img, lang="vie+eng")
    except Exception as exc:
        return {"type": "text", "content": "", "error": f"ocr_unavailable:{exc}"}
    return {"type": "text", "content": text}


def extract_eml(path: str) -> dict:
    with open(path, "rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    body = ""
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_content()
                break
    else:
        body = message.get_content()

    return {
        "type": "text",
        "content": body or "",
        "metadata": {
            "sender": message.get("From"),
            "date": message.get("Date"),
            "subject": message.get("Subject"),
        },
    }


def extract_pst(path: str) -> dict:
    try:
        import pypff
    except Exception as exc:
        return {"type": "text", "content": "", "error": f"pst_not_supported:{exc}"}

    pst = pypff.file()
    pst.open(path)
    texts: list[str] = []

    def walk(folder) -> None:
        for index in range(folder.number_of_messages):
            message = folder.get_message(index)
            subject = message.subject or ""
            body = message.plain_text_body or ""
            if subject or body:
                texts.append(f"Subject: {subject}\n{body}")
            if len(texts) >= 200:
                return
        for idx in range(folder.number_of_sub_folders):
            walk(folder.get_sub_folder(idx))
            if len(texts) >= 200:
                return

    try:
        root = pst.get_root_folder()
        walk(root)
    finally:
        pst.close()

    return {"type": "text", "content": "\n\n".join(texts), "metadata": {"messages": len(texts)}}


EXTRACTORS = {
    "PDF": extract_pdf,
    "DOCX": extract_docx,
    "XLSX": extract_excel,
    "CSV": extract_csv,
    "TXT": extract_text,
    "IMAGE": extract_image,
    "EML": extract_eml,
    "PST": extract_pst,
}


def extract(file_record) -> dict:
    fn = EXTRACTORS.get(file_record.format)
    if not fn:
        return {"type": "text", "content": "", "error": "unsupported format"}
    return fn(file_record.file_path)
