
from dataclasses import dataclass
from typing import List
import tempfile
import urllib.request
import requests

from serpapi import GoogleSearch

from . import config


@dataclass
class SearchCandidate:
    url: str
    image_url: str


def _upload_image_temporarily(image_path: str) -> str:
    """Upload the local image to Catbox so Google Lens can fetch it."""
    with open(image_path, "rb") as image_file:
        response = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": image_file},
            timeout=30,
        )

    response.raise_for_status()
    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox.moe upload failed: {url}")
    return url


def reverse_image_search(image_path: str) -> List[SearchCandidate]:
    if not config.SERPAPI_KEY:
        raise RuntimeError("SERPAPI_KEY not set. Add it to your .env.")

    image_url = _upload_image_temporarily(image_path)

    search = GoogleSearch({
        "engine": "google_lens",
        "url": image_url,
        "api_key": config.SERPAPI_KEY,
    })
    results = search.get_dict()

    if "error" in results:
        raise RuntimeError(f"SerpApi error: {results['error']}")

    candidates: List[SearchCandidate] = []
    for match in results.get("visual_matches", []):
        link = match.get("link", "")
        if not _is_social_domain(link):
            continue
        img_url = match.get("thumbnail") or match.get("image") or link
        candidates.append(SearchCandidate(url=link, image_url=img_url))

    return candidates


def _is_social_domain(url: str) -> bool:
    return any(domain in url for domain in config.SOCIAL_DOMAINS)


def download_image(url: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        tmp.write(resp.read())
    tmp.close()
    return tmp.name