"""Download candidate images and compare detected faces to the input face."""
from pathlib import Path
import hashlib
import requests
import numpy as np
import face_recognition
from .reverse_search import SearchResult

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def download_image(url: str, out_dir: str, index: int) -> Path | None:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        if not ctype.startswith("image/"):
            return None
        ext = ".jpg"
        if "png" in ctype: ext = ".png"
        elif "webp" in ctype: ext = ".webp"
        path = Path(out_dir) / f"candidate_{index}{ext}"
        path.write_bytes(r.content)
        return path
    except requests.RequestException:
        return None


def score_candidate(input_encoding, image_path: str):
    try:
        img = face_recognition.load_image_file(image_path)
        encs = face_recognition.face_encodings(img)
        if not encs:
            return None
        d = face_recognition.face_distance(encs, input_encoding)
        return float(np.min(d))
    except Exception:
        return None
