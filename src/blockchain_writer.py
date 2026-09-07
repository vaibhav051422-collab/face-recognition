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


def _format_tx_hash(tx_hash) -> str:
    hex_str = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    if hex_str.startswith("0x"):
        return hex_str
    return "0x" + hex_str


def explorer_url(tx_hash: str) -> str:
    return config.BLOCK_EXPLORER + _format_tx_hash(tx_hash)


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
    private_key = config.normalized_private_key()

    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC at {config.RPC_URL}")

    account = w3.eth.account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    if balance == 0:
        raise RuntimeError(
            f"Wallet {account.address} has 0 POL on Amoy. "
            "Fund it from a Polygon Amoy faucet first."
        )

    data_hex = w3.to_hex(text=record_hash)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    unsigned = {
        "from": account.address,
        "to": account.address,
        "value": 0,
        "nonce": nonce,
        "data": data_hex,
        "chainId": config.CHAIN_ID,
    }
    try:
        gas = w3.eth.estimate_gas(unsigned)
    except Exception:
        gas = 21000 + 16 * (len(data_hex) - 2) // 2

    tx = {**unsigned, "gas": gas, "gasPrice": gas_price}

    signed = account.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    print(f"  Broadcast. Waiting for confirmation...")
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    return _format_tx_hash(tx_hash)


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