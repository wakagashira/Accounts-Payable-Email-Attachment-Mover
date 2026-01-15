from pathlib import Path
import re
import base64
import shutil
from config import OUTPUT_DIR, ALLOWED_EXTENSIONS

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def save_attachments(attachments, mailbox_folder):
    saved_files = []

    base_path = Path(OUTPUT_DIR) / mailbox_folder
    base_path.mkdir(parents=True, exist_ok=True)

    for att in attachments:
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue

        filename = sanitize_filename(att.get("name", ""))

        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        content_b64 = att.get("contentBytes")
        if not content_b64:
            continue

        file_path = base_path / filename

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(content_b64))

        saved_files.append(file_path)

    return saved_files

def archive_file(file_path, mailbox_folder):
    archive_root = Path("Archived") / mailbox_folder
    archive_root.mkdir(parents=True, exist_ok=True)

    destination = archive_root / file_path.name
    shutil.move(str(file_path), str(destination))
