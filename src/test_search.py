
import sys
from src.reverse_search import reverse_image_search, _upload_image_temporarily
from serpapi import GoogleSearch
from src import config

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_search.py <path_to_image>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Uploading image...")
    image_url = _upload_image_temporarily(image_path)
    print(f"Uploaded to: {image_url}\n")

    print("Querying SerpApi...")
    search = GoogleSearch({
        "engine": "google_lens",
        "url": image_url,
        "api_key": config.SERPAPI_KEY,
    })
    results = search.get_dict()

    if "error" in results:
        print(f"SerpApi error: {results['error']}")
        sys.exit(1)

    matches = results.get("visual_matches", [])
    print(f"Total raw visual matches from Lens: {len(matches)}\n")

    for m in matches[:15]:
        print(f"  - {m.get('link')}")

    print("\n--- Now filtering to social domains only ---")
    candidates = reverse_image_search(image_path)
    print(f"Social-domain matches: {len(candidates)}")
    for c in candidates:
        print(f"  - {c.url}")