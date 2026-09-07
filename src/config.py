
import os
from dotenv import load_dotenv

load_dotenv()

FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
SERPAPI_KEY = os.getenv("SERPAPI_KEY")





SOCIAL_DOMAINS = [
    "instagram.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "linkedin.com",
    "tiktok.com",
    "reddit.com",
    "pinterest.com",
    "threads.net",
]


RPC_URL = os.getenv("RPC_URL", "https://rpc-amoy.polygon.technology")
CHAIN_ID = int(os.getenv("CHAIN_ID", "80002"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
BLOCK_EXPLORER = "https://amoy.polygonscan.com/tx/"


def normalized_private_key() -> str:
    """Return a 0x-prefixed 32-byte key, or raise a clear error."""
    raw = PRIVATE_KEY
    if not raw:
        raise RuntimeError(
            "PRIVATE_KEY not set. Add a TESTNET-ONLY wallet private key to your .env. "
            "Never use a wallet holding real funds."
        )
    key = raw.strip().strip('"').strip("'")
    if key.startswith("0x"):
        hex_body = key[2:]
    else:
        hex_body = key
        key = "0x" + key
    if len(hex_body) == 40:
        raise RuntimeError(
            "PRIVATE_KEY in .env is a wallet ADDRESS (20 bytes), not a private key. "
            "In MetaMask: Account details → Show private key. Paste the 64-hex-character "
            "secret (with or without 0x). Use a testnet-only wallet."
        )
    if len(hex_body) != 64:
        raise RuntimeError(
            "PRIVATE_KEY must be 64 hex characters (32 bytes), optionally prefixed with 0x."
        )
    return key


RECORDS_DIR = os.getenv("RECORDS_DIR", "records")