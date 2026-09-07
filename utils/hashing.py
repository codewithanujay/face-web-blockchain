from hashlib import sha256
from pathlib import Path


def sha256_file(path: str) -> str:
    h = sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()
