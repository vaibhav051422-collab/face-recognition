"""
Stage 3: Write a tamper-evident record of the match to a public testnet
(Polygon Amoy by default). We hash the match data and embed the hash in
a transaction's `data` field — no smart contract required, but a
contract-based version (StoreMatch.sol) is included for extra structure.

Pattern: keep the FULL match record off-chain (records/ dir, JSON),
put only the SHA-256 hash on-chain. Anyone can re-hash the off-chain
record and compare it to what's on-chain to prove it hasn't been altered.
"""
import hashlib
import json
import os
from dataclasses import dataclass, asdict

from web3 import Web3

from . import config


@dataclass
class MatchRecord:
    source_image: str
    matched_url: str
    matched_image_url: str
    face_distance: float
    timestamp: str

    def to_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()


def save_record_locally(record: MatchRecord) -> str:
    os.makedirs(config.RECORDS_DIR, exist_ok=True)
    record_hash = record.to_hash()
    path = os.path.join(config.RECORDS_DIR, f"{record_hash}.json")
    with open(path, "w") as f:
        json.dump(asdict(record), f, indent=2)
    return path


def write_hash_to_chain(record_hash: str) -> str:
    """
    Sends a zero-value self-transaction carrying the record's SHA-256
    hash in the data field. Returns the transaction hash (hex string).
    """
    if not config.PRIVATE_KEY:
        raise RuntimeError(
            "PRIVATE_KEY not set. Add a TESTNET-ONLY wallet private key to your .env. "
            "Never use a wallet holding real funds."
        )

    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC at {config.RPC_URL}")

    account = w3.eth.account.from_key(config.PRIVATE_KEY)
    data_hex = w3.to_hex(text=record_hash)

    tx = {
        "to": account.address,          
        "value": 0,
        "gas": 21000 + 68 * (len(data_hex) - 2) // 2,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(account.address),
        "data": data_hex,
        "chainId": config.CHAIN_ID,
    }

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    return tx_hash.hex()


def verify_on_chain(tx_hash: str, expected_record_hash: str) -> bool:
    """
    Re-fetches the transaction and confirms the on-chain data matches
    the expected hash — this is the "tamper-evident" check anyone
    (including a judge) can run independently.
    """
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    tx = w3.eth.get_transaction(tx_hash)
    onchain_text = w3.to_text(tx["input"] if "input" in tx else tx["data"])
    return onchain_text == expected_record_hash