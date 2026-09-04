

from typing import Optional
import numpy as np
import face_recognition


class NoFaceFoundError(Exception):
    pass


class MultipleFacesError(Exception):
    pass


def encode_face(image_path: str, allow_multiple: bool = False) -> np.ndarray:
    """
    Detect a face in the given image and return its 128-d encoding.

    Raises NoFaceFoundError if no face is detected.
    Raises MultipleFacesError if >1 face is found and allow_multiple=False.
    """
    image = face_recognition.load_image_file(image_path)
    locations = face_recognition.face_locations(image, model="hog")
    

    if len(locations) == 0:
        raise NoFaceFoundError(f"No face detected in {image_path}")

    if len(locations) > 1 and not allow_multiple:
        raise MultipleFacesError(
            f"{len(locations)} faces detected in {image_path}; "
            "pass allow_multiple=True to encode the first one anyway."
        )

    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    return encodings[0]


def compare_encodings(known_encoding: np.ndarray, candidate_encoding: np.ndarray) -> float:
    """
    Returns the euclidean face distance between two encodings.
    Lower = more similar. < ~0.6 is generally considered a match.
    """
    distance = face_recognition.face_distance([known_encoding], candidate_encoding)[0]
    return float(distance)


def is_match(known_encoding: np.ndarray, candidate_encoding: np.ndarray, threshold: float) -> bool:
    return compare_encodings(known_encoding, candidate_encoding) <= threshold