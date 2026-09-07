
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone


def _safe_print(*args, **kwargs) -> None:
    text = " ".join(str(a) for a in args)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.buffer.write((text + kwargs.get("end", "\n")).encode(encoding, errors="replace"))
    sys.stdout.buffer.flush()

from src import config
from src.blockchain_writer import (
    MatchRecord,
    explorer_url,
    save_record_locally,
    verify_on_chain,
    write_hash_to_chain,
)
from src.face_encoder import (
    MultipleFacesError,
    NoFaceFoundError,
    compare_encodings,
    encode_face,
    is_match,
)
from src.reverse_search import download_image, reverse_image_search


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _encode_source(image_path: str):
    try:
        return encode_face(image_path, allow_multiple=False)
    except MultipleFacesError:
        _safe_print("  Multiple faces in source photo; using the first detected face.")
        return encode_face(image_path, allow_multiple=True)


def run_pipeline(image_path: str, skip_chain: bool = False, max_candidates: int = 12) -> int:
    if not os.path.isfile(image_path):
        _safe_print(f"Image not found: {image_path}")
        return 1

    abs_path = os.path.abspath(image_path)
    _safe_print("=== Face + blockchain verification pipeline ===")
    _safe_print(f"Source image: {abs_path}")
    _safe_print(f"Match threshold (lower = stricter): {config.FACE_MATCH_THRESHOLD}")
    _safe_print()

    _safe_print("[1/5] Detecting and encoding face in source image...")
    try:
        source_encoding = _encode_source(abs_path)
    except NoFaceFoundError as exc:
        _safe_print(f"  Failed: {exc}")
        return 1
    _safe_print("  Face encoded (128-d vector).")
    _safe_print()

    _safe_print("[2/5] Reverse-image search (Google Lens via SerpApi), social domains only...")
    candidates = reverse_image_search(abs_path)
    _safe_print(f"  Social-domain candidates (raw): {len(candidates)}")
    if max_candidates > 0:
        candidates = candidates[:max_candidates]
        _safe_print(f"  Checking first {len(candidates)} (--max-candidates={max_candidates})")
    for i, candidate in enumerate(candidates, start=1):
        _safe_print(f"    {i}. {candidate.url}")
    if not candidates:
        _safe_print("  No social-media candidates. Nothing to verify or write on-chain.")
        return 0
    _safe_print()

    _safe_print("[3/5] Downloading candidates and confirming with face encodings...")
    verified = []
    for i, candidate in enumerate(candidates, start=1):
        _safe_print(f"  Candidate {i}/{len(candidates)}: {candidate.url}")
        try:
            local_path = download_image(candidate.image_url)
        except Exception as exc:
            _safe_print(f"    Skip - could not download image: {exc}")
            continue

        try:
            candidate_encoding = encode_face(local_path, allow_multiple=True)
        except NoFaceFoundError:
            _safe_print("    Skip - no face detected in candidate image.")
            continue
        except Exception as exc:
            _safe_print(f"    Skip - encode failed: {exc}")
            continue

        distance = compare_encodings(source_encoding, candidate_encoding)
        matched = is_match(source_encoding, candidate_encoding, config.FACE_MATCH_THRESHOLD)
        _safe_print(f"    Face distance: {distance:.4f}  match={matched}")
        if matched:
            verified.append((candidate, distance))

    _safe_print()
    _safe_print(f"  Verified face matches: {len(verified)}")
    if not verified:
        _safe_print("  Visual hits existed, but none passed face-encoding confirmation.")
        _safe_print("  No record will be written to the chain.")
        return 0

    verified.sort(key=lambda item: item[1])
    best_candidate, best_distance = verified[0]
    _safe_print(f"  Best match: {best_candidate.url}  (distance {best_distance:.4f})")
    _safe_print()

    _safe_print("[4/5] Saving verified match record locally...")
    record = MatchRecord(
        source_image=abs_path,
        matched_url=best_candidate.url,
        matched_image_url=best_candidate.image_url,
        face_distance=round(best_distance, 6),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    record_path = save_record_locally(record)
    record_hash = record.to_hash()
    _safe_print(f"  JSON:    {os.path.abspath(record_path)}")
    _safe_print(f"  SHA-256: {record_hash}")
    _safe_print(f"  Source file SHA-256 (not on-chain, for your notes): {_file_sha256(abs_path)}")
    _safe_print()

    if skip_chain:
        _safe_print("[5/5] Skipping blockchain write (--skip-chain).")
        return 0

    _safe_print("[5/5] Writing SHA-256 hash to Polygon Amoy...")
    tx_hash = write_hash_to_chain(record_hash)
    url = explorer_url(tx_hash)
    ok = verify_on_chain(tx_hash, record_hash)

    _safe_print()
    _safe_print("=== Pipeline result ===")
    _safe_print(f"Matched URL:  {best_candidate.url}")
    _safe_print(f"Distance:     {best_distance:.4f}")
    _safe_print(f"Record JSON:  {os.path.abspath(record_path)}")
    _safe_print(f"Record hash:  {record_hash}")
    _safe_print(f"Tx hash:      {tx_hash}")
    _safe_print(f"PolygonScan:  {url}")
    _safe_print(f"Verified:     {ok}")
    if not ok:
        _safe_print("WARNING: RPC re-read did not match the local hash.")
        return 1
    _safe_print()
    _safe_print("Open the PolygonScan link and confirm Input Data equals the SHA-256 above.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Face match + Polygon Amoy verification pipeline")
    parser.add_argument("image", help="Path to the source photo")
    parser.add_argument(
        "--skip-chain",
        action="store_true",
        help="Run search + face confirm only; do not send a transaction",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=12,
        help="Max social-domain hits to download and face-compare (default 12)",
    )
    args = parser.parse_args()
    raise SystemExit(
        run_pipeline(
            args.image,
            skip_chain=args.skip_chain,
            max_candidates=args.max_candidates,
        )
    )


if __name__ == "__main__":
    main()
