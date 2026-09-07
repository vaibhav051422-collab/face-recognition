# Face ID + Blockchain Verification Pipeline

Detects a face in an input photo, finds a genuine matching social media post via
a real reverse-image search, verifies the match by re-encoding the found face,
and writes a tamper-evident hash of that match to a public blockchain.

## Functionality

The pipeline runs in four stages:

1. **Face detection & encoding**
   Uses the `face_recognition` Python library (dlib HOG detector + ResNet
   encoder) to detect a face in the input image and produce a 128-dimensional
   encoding vector representing that face.

2. **Genuine reverse-image search**
   The input image is uploaded and searched using **SerpApi's Google Lens
   API**, which performs a real, live reverse-image search against Google's
   index — this is not a mocked or hardcoded result set; every run queries the
   live API and returns whatever visual matches currently exist on the web.
   Results are then filtered down to known social media domains (Instagram,
   X/Twitter, Reddit, Facebook, LinkedIn, Pinterest, TikTok, Threads).

3. **Match verification**
   Reverse-image search alone only proves *visual similarity*, not that a
   face actually matches — a wallpaper, meme, or edited image can visually
   resemble the input without being a real match. To close that gap, the
   pipeline downloads each candidate social media image, re-runs face
   detection/encoding on it, and computes the Euclidean distance between that
   encoding and the original face's encoding. Only candidates at or below
   `FACE_MATCH_THRESHOLD` (default `0.6`) are treated as a genuine, verified
   match.

4. **Blockchain write (tamper-evident record)**
   The verified match record — source image, matched post URL, face distance,
   timestamp — is hashed with SHA-256. The full record is saved locally as
   JSON under `records/`, and **only the hash** is written on-chain, as the
   `data` field of a zero-value self-transaction on the **Polygon Amoy
   testnet**, signed by a dedicated testnet-only wallet. Anyone can
   independently re-hash the local JSON record and compare it to what's
   stored on-chain — if they match, the record is provably unaltered since
   the moment it was written.

## How to run it

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
`face_recognition` depends on `dlib`, which compiles from source and needs
CMake + a C++ compiler installed first:
- **Ubuntu:** `sudo apt install cmake build-essential`
- **Mac:** `brew install cmake`
- **Windows:** Visual Studio Build Tools ("Desktop development with C++") + CMake, added to PATH

### 2. Set up reverse-image search (SerpApi)
- Create a free account at [serpapi.com](https://serpapi.com) and copy your API key.
- Add it to your `.env` file as `SERPAPI_KEY`.

### 3. Set up a blockchain wallet
- Install [MetaMask](https://metamask.io) and create a **new, dedicated
  wallet** — never one holding real funds, since its private key will live in
  a local config file.
- Add the **Polygon Amoy testnet** to MetaMask manually:
  - Network name: `Polygon Amoy Testnet`
  - RPC URL: `https://rpc-amoy.polygon.technology` (or an alternate public RPC
    if that one is unreachable, e.g. `https://polygon-amoy.drpc.org`)
  - Chain ID: `80002`
  - Currency symbol: `POL`
  - Block explorer: `https://amoy.polygonscan.com`
- Fund the wallet with free test POL from the
  [Polygon faucet](https://faucet.polygon.technology/).
- Export the wallet's private key (MetaMask → Account details → Show private
  key) and add it to `.env`.

### 4. Configure environment
```bash
cp .env.example .env
# then fill in SERPAPI_KEY, RPC_URL, CHAIN_ID, PRIVATE_KEY
```

### 5. Run the pipeline
```bash
python -m src.main path/to/photo.jpg
```

Example output:
```
[1/4] Detecting and encoding face in photo.jpg ...
  ✓ Face encoded.
[2/4] Running reverse-image search (SerpApi / Google Lens) ...
  ✓ 10 social-media candidate page(s) found.
[3/4] Verifying candidates against source face ...
    - https://instagram.com/p/xyz  (distance=0.412)
  ✓ Verified match: https://instagram.com/p/xyz (distance=0.412)
[4/4] Writing tamper-evident record to blockchain ...
  ✓ Record written.
============================================================
Matched post   : https://instagram.com/p/xyz
Local record   : records/<hash>.json
Record hash    : <sha256 hash>
Transaction    : 0x...
Block explorer : https://amoy.polygonscan.com/tx/0x...
============================================================
```

## Which blockchain

**Polygon Amoy testnet** (chain ID `80002`) — a free, faucet-funded test
network that is fully EVM-compatible, meaning the same code would work
unmodified against Ethereum mainnet or any other EVM chain by only changing
`RPC_URL` and `CHAIN_ID`. Every transaction can be independently verified by
anyone, with no special access required, via the public block explorer:
**https://amoy.polygonscan.com**

To verify a record: take the transaction hash printed by the pipeline, open
it on PolygonScan, and check the "Input Data" field — it will contain the
same SHA-256 hash as the locally saved `records/<hash>.json` file for that
match. If they match, the record is confirmed authentic and unaltered.

## Known limitations

- **Face detection accuracy**: the default HOG-based detector can miss faces
  at extreme angles, in low light, or when partially occluded. A CNN-based
  detector is more accurate but much slower without a GPU.
- **Single-face assumption**: images containing more than one face are
  rejected by default rather than guessing which face to encode.
- **Search coverage is index-dependent**: SerpApi/Google Lens can only surface
  posts that are indexed, publicly accessible, and not behind a login wall —
  a genuine matching post may exist and still not appear if it isn't indexed.
- **Visual similarity ≠ face match**: the reverse-image search step alone can
  surface wallpapers, memes, or edited images that are visually similar but
  not a real face match; the separate face-verification step exists
  specifically to filter these out, but very heavily filtered, cropped, or
  low-resolution images can still push a genuine match's distance score above
  threshold (a false negative).
- **Testnet, not mainnet**: Polygon Amoy is a test network with no real
  economic security behind it — the record is cryptographically
  tamper-evident, but for production use a mainnet or an established public
  chain would be more appropriate.
- **Rate limits and cost**: SerpApi's free tier has a limited number of
  monthly searches; heavy use requires a paid plan.
- **Privacy and consent**: this pipeline processes biometric data and
  cross-references it against public social media presence. It should only
  be run on images the user has the rights or consent to use.

## Project structure
```
face-blockchain-pipeline/
├── src/
│   ├── config.py            # env-driven settings
│   ├── face_encoder.py      # Stage 1: face detection/encoding
│   ├── reverse_search.py    # Stage 2: reverse-image search
│   ├── blockchain_writer.py # Stage 4: hashing + on-chain write
│   └── main.py               # CLI entry point, ties all stages together
├── contracts/
│   └── StoreMatch.sol        # optional structured on-chain storage (extra credit)
├── requirements.txt
├── .env.example
└── README.md
