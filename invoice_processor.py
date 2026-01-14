from pathlib import Path
import re
import base64
from config import OUTPUT_DIR, ALLOWED_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    Removes characters invalid on Windows filesystems.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def save_attachments(attachments, mailbox_folder):
    base_path = Path(OUTPUT_DIR) / mailbox_folder
    base_path.mkdir(parents=True, exist_ok=True)

    for att in attachments:
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue

        original_name = att.get("name", "")
        filename = sanitize_filename(original_name)

        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        content_b64 = att.get("contentBytes")
        if not content_b64:
            continue

        file_path = base_path / filename

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(content_b64))
