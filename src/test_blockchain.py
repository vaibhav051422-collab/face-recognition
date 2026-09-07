
from datetime import datetime, timezone

from src import config
from src.blockchain_writer import (
    MatchRecord,
    explorer_url,
    save_record_locally,
    verify_on_chain,
    write_hash_to_chain,
)
from web3 import Web3


def main() -> None:
    private_key = config.normalized_private_key()
    if not config.RPC_URL:
        raise SystemExit("RPC_URL missing from .env")

    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    if not w3.is_connected():
        raise SystemExit(f"Could not connect to {config.RPC_URL}")

    account = w3.eth.account.from_key(private_key)
    balance_pol = w3.from_wei(w3.eth.get_balance(account.address), "ether")

    print("=== Isolated blockchain write test (Polygon Amoy) ===")
    print(f"RPC:     {config.RPC_URL}")
    print(f"Chain:   {config.CHAIN_ID}")
    print(f"Wallet:  {account.address}")
    print(f"Balance: {balance_pol} POL")
    print()

    record = MatchRecord(
        source_image="isolated-test",
        matched_url="https://example.com/isolated-test",
        matched_image_url="https://example.com/isolated-test.jpg",
        face_distance=0.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    record_hash = record.to_hash()
    path = save_record_locally(record)

    print(f"Local record: {path}")
    print(f"SHA-256:      {record_hash}")
    print("Sending zero-value self-tx with hash in data field...")

    tx_hash = write_hash_to_chain(record_hash)
    url = explorer_url(tx_hash)
    ok = verify_on_chain(tx_hash, record_hash)

    print()
    print("=== Result ===")
    print(f"tx hash:     {tx_hash}")
    print(f"PolygonScan: {url}")
    print(f"on-chain hash matches local record: {ok}")
    if not ok:
        raise SystemExit("On-chain data did not match the local SHA-256 hash.")
    print()
    print("Paste the tx hash into https://amoy.polygonscan.com to show judges.")
    print(f"Input data should decode to: {record_hash}")


if __name__ == "__main__":
    main()
