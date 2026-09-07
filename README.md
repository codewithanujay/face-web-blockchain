# Face → Web/Social Search → Blockchain Verification

An end-to-end Python pipeline that:

1. Detects and encodes a face from an input image.
2. Performs a **real reverse-image search** using Google Lens through Playwright.
3. Collects genuine web results (which may include social-media/public-post URLs).
4. Creates a deterministic fingerprint of the discovered result metadata with SHA-256.
5. Registers that fingerprint and source URL on a local Ethereum-compatible EVM chain.
6. Reads the record back from the chain and re-computes the comparison to demonstrate tamper-evident verification.

## Architecture

`Input image → Face encoding → Google Lens reverse-image search → discovered URL → SHA-256 → local EVM blockchain → re-verification`

## Tech stack

- Python 3.10+
- `face_recognition` + dlib for face detection/encoding
- Playwright for a genuine Google Lens browser search
- Web3.py
- `eth-tester` + Py-EVM for a local Ethereum-compatible blockchain
- Solidity smart contract

## Setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

If `face-recognition`/dlib installation fails on Windows, use Python 3.10/3.11 and install the required C++ build tools, or use WSL/Linux.

## Run

Put a test image in `input/person.jpg`, then:

```powershell
python app.py --image input/person.jpg
```

The first run may take time because the Solidity compiler is downloaded and Chromium is started.

Outputs:

- `output/search_results.json` — genuine reverse-search results
- `output/discovered_post_metadata.json` — exact metadata that was hashed
- `output/verification_report.json` — blockchain transaction + verification result

## Blockchain

The demo uses a **local Ethereum-compatible EVM** through `eth-tester` and Py-EVM. This avoids requiring real funds or a wallet while still deploying and calling a Solidity smart contract and producing a transaction receipt.

The contract is `contracts/ContentRegistry.sol`. It stores:

- SHA-256 content fingerprint as `bytes32`
- source URL
- block timestamp
- submitting address

## Important limitation

Reverse-image search services and social-media platforms can change their HTML, restrict automated access, require authentication, or present CAPTCHA challenges. This project does not bypass those controls. If Google Lens is unavailable in the environment, use a permitted reverse-image-search API and adapt `search/reverse_search.py`.

The included demo registers the **discovered result's title + URL metadata**. It does not claim that the blockchain proves the identity of the person or the truthfulness of a post. The blockchain only proves that the exact fingerprint recorded at registration matches the data later verified.

For a stronger production implementation, the next step is to download the actual public post image/text (where permitted), hash those bytes/content, and store that hash instead of only the search-result metadata.

## Privacy / ethics

Only test with images and public content you are authorized to process. Face recognition is sensitive biometric processing; do not use this project to identify or track people without an appropriate lawful basis and consent.
