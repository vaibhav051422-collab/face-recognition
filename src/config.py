
import os
from dotenv import load_dotenv

load_dotenv()

FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
SERPAPI_KEY = os.getenv("SERPAPI_KEY")



# GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
# # Path to your GCP service-account JSON key file.

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


RECORDS_DIR = os.getenv("RECORDS_DIR", "records")