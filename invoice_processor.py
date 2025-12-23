import base64
from pathlib import Path
from config import OUTPUT_DIR, ALLOWED_EXTENSIONS

def save_attachments(attachments):
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    for att in attachments:
        if att["@odata.type"] != "#microsoft.graph.fileAttachment":
            continue

        name = att["name"]
        if not name.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        content = base64.b64decode(att["contentBytes"])
        path = Path(OUTPUT_DIR) / name

        with open(path, "wb") as f:
            f.write(content)