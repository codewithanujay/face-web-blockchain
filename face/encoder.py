"""Face detection and encoding using the face_recognition library."""
from pathlib import Path
from typing import List
import face_recognition
import numpy as np


def load_image(path: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input image not found: {p}")
    return face_recognition.load_image_file(str(p))


def encode_faces(path: str) -> List[np.ndarray]:
    image = load_image(path)
    locations = face_recognition.face_locations(image, model="hog")
    if not locations:
        raise ValueError("No face detected in the input image.")
    return face_recognition.face_encodings(image, known_face_locations=locations)


def best_match(input_encoding: np.ndarray, candidate_encodings: List[np.ndarray]):
    if not candidate_encodings:
        return None, None
    distances = face_recognition.face_distance(candidate_encodings, input_encoding)
    idx = int(np.argmin(distances))
    return idx, float(distances[idx])
