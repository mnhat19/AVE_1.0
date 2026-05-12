from __future__ import annotations

from email import policy
from email.parser import BytesParser


def parse_eml(path: str) -> dict:
    """Parse EML message into content and metadata."""
    with open(path, "rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    body = ""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = message.get_content()

    return {
        "content": body or "",
        "metadata": {
            "sender": message.get("From"),
            "date": message.get("Date"),
            "subject": message.get("Subject"),
        },
    }


def parse_pst(path: str) -> dict:
    """Parse PST mailbox content into a text summary."""
    try:
        import pypff
    except Exception as exc:
        return {"content": "", "metadata": {}, "error": f"pst_not_supported:{exc}"}

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

    return {"content": "\n\n".join(texts), "metadata": {"messages": len(texts)}}
