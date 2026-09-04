

from dataclasses import dataclass
from typing import List
import tempfile
import urllib.request

from google.cloud import vision

from . import config


@dataclass
class SearchCandidate:
    url: str          # page URL where a matching/visually-similar image was found
    image_url: str     # direct URL of the image on that page, if available


def reverse_image_search(image_path: str) -> List[SearchCandidate]:
    """
    Run Google Cloud Vision Web Detection on the given image and return
    candidate pages, filtered to known social media domains.
    """
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.web_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    web_detection = response.web_detection
    candidates: List[SearchCandidate] = []

    for page in list(web_detection.pages_with_matching_images):
        if not _is_social_domain(page.url):
            continue
        image_url = page.url
        if page.full_matching_images:
            image_url = page.full_matching_images[0].url
        elif page.partial_matching_images:
            image_url = page.partial_matching_images[0].url
        candidates.append(SearchCandidate(url=page.url, image_url=image_url))

    return candidates


def _is_social_domain(url: str) -> bool:
    return any(domain in url for domain in config.SOCIAL_DOMAINS)


def download_image(url: str) -> str:
    """
    Downloads an image to a temp file and returns the local path.
    Used so we can re-run face encoding on candidate images to verify a
    genuine face match (not just visual similarity).
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        tmp.write(resp.read())
    tmp.close()
    return tmp.name