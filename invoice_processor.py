import os
import re
from pathlib import Path
from config import OUTPUT_DIR, ALLOWED_EXTENSIONS


INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1F]'
MAX_FILENAME_LENGTH = 150  # Safe margin for Windows paths


def _sanitize_filename(name: str) -> str:
    """
    Make filenames safe for Windows filesystems.
    """
    # Remove invalid characters
    name = re.sub(INVALID_CHARS, "", name)

    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)

    # Strip leading/trailing spaces and dots
    name = name.strip(" .")

    # Enforce max length (preserve extension)
    stem, ext = os.path.splitext(name)
    if len(name) > MAX_FILENAME_LENGTH:
        stem = stem[: MAX_FILENAME_LENGTH - len(ext)]
        name = f"{stem}{ext}"

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
                f.write(bytes(att["contentBytes"], encoding="latin1"))

            saved_files.append(file_path)

        except Exception:
            # If one attachment fails, keep going
            continue

    return saved_files


def archive_file(file_path, mailbox_folder):
    """
    Moves a processed file to:
      Archived/<mailbox_folder>/
    """
    src = Path(file_path)
    dest_dir = Path("Archived") / mailbox_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / src.name
    src.rename(dest)
