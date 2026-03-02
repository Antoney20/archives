import os
import re
from datetime import datetime


CATEGORY_MIME_MAP = {
    "images": {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "image/svg+xml", "image/bmp", "image/tiff",
    },
    "documents": {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
    "text": {
        "text/plain", "text/csv", "text/html", "text/markdown",
        "application/json", "application/xml", "text/xml",
    },
}


def resolve_category(mime_type: str) -> str:
    for category, mime_set in CATEGORY_MIME_MAP.items():
        if mime_type in mime_set:
            return category
    return "other"


def get_file_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[-1].lower() if len(parts) == 2 else "bin"


def normalize_filename(name: str) -> str:
    name = os.path.splitext(name)[0].lower()
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name[:10] or "file"


def generate_storage_name(original_name, record_id, ext):
    """
    filename format:
    name-YYYYMM-id.ext
    """

    base = normalize_filename(original_name)
    date_part = datetime.now().strftime("%Y%m")

    return f"{base}-{date_part}-{record_id}.{ext}"