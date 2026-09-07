import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from face.encoder import encode_faces
from search.reverse_search import google_lens_search, save_results, SearchResult
from search.matcher import download_image, score_candidate
from blockchain.local_chain import register_and_verify
from utils.hashing import sha256_file


def main():
    parser = argparse.ArgumentParser(description="Face -> Web Search -> Blockchain verification pipeline")
    parser.add_argument("--image", required=True, help="Input face image")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--source-url", help="Optional URL to hash instead of a downloaded candidate image")
    args = parser.parse_args()

    out = Path("output")
    out.mkdir(exist_ok=True)

    print("[1/4] Detecting and encoding face...")
    encodings = encode_faces(args.image)
    input_encoding = encodings[0]
    print(f"      OK: {len(encodings)} face(s) detected; using face #1")

    print("[2/4] Performing genuine reverse-image web search...")
    results = google_lens_search(args.image, args.max_results)
    save_results(results, str(out / "search_results.json"))
    print(f"      OK: {len(results)} web result(s) collected")
    if results:
        for r in results[:5]:
            print(f"      - {r.title[:80]} -> {r.url}")
    else:
        raise RuntimeError("No web results found. Search manually or retry later; nothing is hardcoded.")

    print("[3/5] Verifying candidate faces...")
    ranked = []
    for i, result in enumerate(results):
        if not result.image_url:
            continue
        candidate_path = download_image(result.image_url, str(out), i)
        if not candidate_path:
            continue
        distance = score_candidate(input_encoding, str(candidate_path))
        if distance is not None:
            ranked.append((distance, result, candidate_path))
    if not ranked:
        raise RuntimeError("Search returned results, but no accessible candidate image contained a detectable face.")
    ranked.sort(key=lambda x: x[0])
    distance, selected, candidate_path = ranked[0]
    print(f"      Best face distance: {distance:.4f}")
    if distance > 0.65:
        raise RuntimeError("No candidate passed the face-match threshold (0.65). Nothing is registered on-chain.")
    print(f"      MATCH: {selected.title[:100]}")
    print(f"      URL:   {selected.url}")

    print("[4/5] Fingerprinting discovered content...")
    digest = sha256_file(str(candidate_path))
    metadata_file = out / "discovered_post_metadata.json"
    metadata_file.write_text(json.dumps({
        "title": selected.title, "url": selected.url,
        "image_url": selected.image_url, "face_distance": distance,
        "sha256_target": digest
    }, indent=2), encoding="utf-8")

    print("[5/5] Registering SHA-256 fingerprint on local EVM blockchain...")
    chain = register_and_verify(digest, selected.url)
    print(f"      Transaction: {chain['transaction_hash']}")
    print(f"      Contract:    {chain['contract_address']}")
    print(f"      Hash:        {digest}")

    print("[6/6] Re-verifying against on-chain record...")
    print(f"      Local hash:  {digest}")
    print(f"      Chain hash:  {chain['on_chain_hash']}")
    print("      RESULT:      " + ("VERIFIED" if chain["verified"] else "TAMPERED"))

    report = {"selected_result": selected.__dict__, "face_distance": distance, "hashed_file": str(candidate_path), "sha256": digest, "blockchain": chain}
    (out / "verification_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nReport written to output/verification_report.json")


if __name__ == "__main__":
    main()
