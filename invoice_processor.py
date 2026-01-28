import os
import re
import base64
import logging
from pathlib import Path
from config import OUTPUT_DIR, ALLOWED_EXTENSIONS, POST_UPLOAD_ACTION


INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1F]'
MAX_FILENAME_LENGTH = 150  # Safe margin for Windows paths

logger = logging.getLogger(__name__)

def _sanitize_filename(name: str) -> str:
    """
    Make filenames safe for Windows filesystems.
    """
    # Remove invalid characters
    name = re.sub(INVALID_CHARS, "", name)

    # Trim whitespace
    name = name.strip()

    # Prevent super long filenames
    if len(name) > MAX_FILENAME_LENGTH:
        base, ext = os.path.splitext(name)
        name = base[: (MAX_FILENAME_LENGTH - len(ext))] + ext

    # Fallback if name becomes empty
    if not name:
        name = "attachment"

    return name


def save_attachments(attachments, mailbox_folder):
    """
    Saves allowed attachments to:
      output/invoices/<mailbox_folder>/

    Returns list of saved file paths.
    """
    saved_files = []

    base_dir = Path(OUTPUT_DIR) / mailbox_folder
    base_dir.mkdir(parents=True, exist_ok=True)

    for att in attachments:
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue

        name = att.get("name")
        if not name:
            continue

        if not name.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        safe_name = _sanitize_filename(name)
        file_path = base_dir / safe_name

        try:
            content = att.get("contentBytes")
            if not content:
                continue

            with open(file_path, "wb") as f:
                f.write(base64.b64decode(content))

            saved_files.append(file_path)

        except Exception as exc:
            logger.warning(f"Failed to save attachment '{name}' for folder '{mailbox_folder}': {exc}")
            continue

    return saved_files


def cleanup_file(file_path, mailbox_folder):
    """
    Post-upload file handling controlled by POST_UPLOAD_ACTION:

    - ARCHIVE: move to Archived/<mailbox_folder>/
    - DELETE: delete the file from output
    """
    action = (POST_UPLOAD_ACTION or "ARCHIVE").upper()
    src = Path(file_path)

    if not src.exists():
        return

    if action == "DELETE":
        src.unlink()
        return

    # Default: ARCHIVE
    dest_dir = Path("Archived") / mailbox_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / src.name

    # If an archive file already exists, make it unique to avoid overwrite
    if dest.exists():
        base = dest.stem
        ext = dest.suffix
        i = 1
        while True:
            candidate = dest_dir / f"{base}_{i}{ext}"
            if not candidate.exists():
                dest = candidate
                break
            i += 1

    src.rename(dest)


# Backwards-compatible wrapper (older code may still call archive_file)
def archive_file(file_path, mailbox_folder):
    cleanup_file(file_path, mailbox_folder)
