"""
Google Lens reverse-image search using SerpApi.

This module:
- Accepts a local image path.
- Compresses/resizes the image when necessary.
- Uploads the image to SerpApi.
- Searches Google Lens.
- Collects exact matches, visual matches, and organic results.
- Prioritizes social-media results.
- Returns SearchResult objects compatible with app.py.
"""

from dataclasses import dataclass, asdict
from typing import List
from pathlib import Path
import json
import os
import tempfile

from PIL import Image

try:
    import serpapi
except ImportError:
    serpapi = None


# ============================================================
# RESULT DATA STRUCTURE
# ============================================================

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    image_url: str = ""


# ============================================================
# SOCIAL MEDIA DOMAINS
# ============================================================

SOCIAL_DOMAINS = (
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "reddit.com",
)


def is_social_url(url: str) -> bool:
    """Check whether a URL belongs to a social-media website."""

    if not url:
        return False

    url = url.lower()

    return any(
        domain in url
        for domain in SOCIAL_DOMAINS
    )


# ============================================================
# PREPARE IMAGE
# ============================================================

def prepare_image(image_path: str) -> str:
    """
    Prepare the image for SerpApi.

    The image is:
    - converted to RGB
    - resized if very large
    - compressed as JPEG
    - reduced to approximately <= 450 KB

    Returns:
        Path to temporary JPEG image.
    """

    source = Path(image_path)

    if not source.exists():
        raise FileNotFoundError(
            f"Image file does not exist:\n{source}"
        )

    temp_dir = Path(tempfile.gettempdir())

    output_path = (
        temp_dir / "face_reverse_search_upload.jpg"
    )

    try:
        image = Image.open(source)

        # Convert PNG/RGBA/etc. to RGB.
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Reduce very large images.
        max_dimension = 1600

        if max(image.size) > max_dimension:

            ratio = (
                max_dimension /
                max(image.size)
            )

            new_width = int(
                image.width * ratio
            )

            new_height = int(
                image.height * ratio
            )

            image = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

        # Try several JPEG qualities.
        qualities = [
            85,
            75,
            65,
            55,
            45,
            35,
        ]

        for quality in qualities:

            image.save(
                output_path,
                format="JPEG",
                quality=quality,
                optimize=True
            )

            size_kb = (
                output_path.stat().st_size /
                1024
            )

            if size_kb <= 450:
                break

        return str(output_path)

    except Exception as exc:

        raise RuntimeError(
            "Could not prepare image for "
            f"reverse search: {exc}"
        ) from exc


# ============================================================
# SERPAPI CLIENT
# ============================================================

def get_serpapi_client():
    """
    Create SerpApi client using SERPAPI_API_KEY.
    """

    if serpapi is None:

        raise RuntimeError(
            "The 'serpapi' package is not installed.\n\n"
            "Run:\n"
            "pip install serpapi"
        )

    api_key = os.getenv(
        "SERPAPI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "SERPAPI_API_KEY is not configured.\n\n"
            "Create a .env file in the project folder "
            "containing:\n\n"
            "SERPAPI_API_KEY=YOUR_API_KEY"
        )

    return serpapi.Client(
        api_key=api_key
    )


# ============================================================
# SAFE VALUE EXTRACTION
# ============================================================

def get_value(
    item,
    *keys
) -> str:
    """
    Get the first available value from a dictionary.
    """

    if not isinstance(item, dict):
        return ""

    for key in keys:

        value = item.get(key)

        if value is not None and value != "":
            return str(value)

    return ""


# ============================================================
# PARSE GOOGLE LENS RESULTS
# ============================================================

def parse_lens_results(
    data: dict,
    max_results: int = 10
) -> List[SearchResult]:
    """
    Extract results from a Google Lens response.

    Searches:
    1. exact_matches
    2. visual_matches
    3. organic_results
    """

    results: List[SearchResult] = []

    seen_urls = set()

    def add_result(item):

        if not isinstance(item, dict):
            return

        # Possible URL fields returned by SerpApi.
        url = get_value(
            item,
            "link",
            "url",
            "source"
        )

        if not url:
            return

        # Remove duplicates.
        if url in seen_urls:
            return

        title = get_value(
            item,
            "title",
            "name",
            "text"
        )

        if not title:
            title = "Google Lens result"

        snippet = get_value(
            item,
            "snippet",
            "description"
        )

        image_url = get_value(
            item,
            "thumbnail",
            "thumbnail_url",
            "image",
            "image_url"
        )

        seen_urls.add(url)

        results.append(
            SearchResult(
                title=title[:300],
                url=url,
                snippet=snippet[:1000],
                image_url=image_url,
            )
        )

    # --------------------------------------------------------
    # EXACT MATCHES
    # --------------------------------------------------------

    exact_matches = data.get(
        "exact_matches",
        []
    )

    if isinstance(exact_matches, list):

        for item in exact_matches:

            add_result(item)

            if len(results) >= max_results:
                return results

    # --------------------------------------------------------
    # VISUAL MATCHES
    # --------------------------------------------------------

    visual_matches = data.get(
        "visual_matches",
        []
    )

    if isinstance(visual_matches, list):

        for item in visual_matches:

            add_result(item)

            if len(results) >= max_results:
                return results

    # --------------------------------------------------------
    # ORGANIC RESULTS
    # --------------------------------------------------------

    organic_results = data.get(
        "organic_results",
        []
    )

    if isinstance(organic_results, list):

        for item in organic_results:

            add_result(item)

            if len(results) >= max_results:
                return results

    return results


# ============================================================
# PRIORITIZE SOCIAL MEDIA
# ============================================================

def prioritize_social_results(
    results: List[SearchResult]
) -> List[SearchResult]:
    """
    Put social-media results before normal web results.
    """

    social_results = []
    normal_results = []

    for result in results:

        if is_social_url(result.url):

            social_results.append(result)

        else:

            normal_results.append(result)

    return (
        social_results +
        normal_results
    )


# ============================================================
# GOOGLE LENS SEARCH
# ============================================================

def google_lens_search(
    image_path: str,
    max_results: int = 10
) -> List[SearchResult]:
    """
    Perform a genuine reverse-image search
    using Google Lens through SerpApi.

    Args:
        image_path:
            Path to the local image.

        max_results:
            Maximum number of results.

    Returns:
        List[SearchResult]
    """

    image_path = str(
        Path(image_path).resolve()
    )

    if not Path(image_path).exists():

        raise FileNotFoundError(
            f"Input image not found:\n{image_path}"
        )

    print(
        "        Preparing image for "
        "reverse search..."
    )

    prepared_image = prepare_image(
        image_path
    )

    try:

        # ----------------------------------------------------
        # CONNECT TO SERPAPI
        # ----------------------------------------------------

        print(
            "        Connecting to SerpApi..."
        )

        client = get_serpapi_client()

        # ----------------------------------------------------
        # UPLOAD IMAGE
        # ----------------------------------------------------

        print(
            "        Uploading image "
            "to Google Lens..."
        )

        upload_response = (
            client.upload_image(
                prepared_image
            )
        )

        if not upload_response:

            raise RuntimeError(
                "SerpApi returned an empty "
                "upload response."
            )

        image_id = upload_response.get(
            "image_id"
        )

        if not image_id:

            raise RuntimeError(
                "Image upload failed.\n\n"
                f"SerpApi response:\n"
                f"{upload_response}"
            )

        print(
            "        Image uploaded successfully."
        )

        # ----------------------------------------------------
        # GOOGLE LENS SEARCH
        # ----------------------------------------------------

        print(
            "        Searching Google Lens..."
        )

        search_params = {
            "engine": "google_lens",
            "image_id": image_id,
            "hl": "en",
            "country": "us",
        }

        response = client.search(
            search_params
        )

        if response is None:

            print(
                "        WARNING: Empty "
                "Google Lens response."
            )

            return []

        # Convert response to dictionary.
        try:
            data = dict(response)
        except Exception:

            data = response

        if not isinstance(data, dict):

            print(
                "        WARNING: Invalid "
                "Google Lens response."
            )

            return []

        # ----------------------------------------------------
        # PARSE RESULTS
        # ----------------------------------------------------

        results = parse_lens_results(
            data,
            max_results=max_results
        )

        # ----------------------------------------------------
        # SOCIAL MEDIA FIRST
        # ----------------------------------------------------

        results = prioritize_social_results(
            results
        )

        results = results[
            :max_results
        ]

        return results

    finally:

        # ----------------------------------------------------
        # DELETE TEMPORARY IMAGE
        # ----------------------------------------------------

        try:

            temp_file = Path(
                prepared_image
            )

            if temp_file.exists():
                temp_file.unlink()

        except Exception:
            pass


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    results: List[SearchResult],
    path: str
):
    """
    Save search results to JSON.
    """

    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        json.dumps(
            [
                asdict(result)
                for result in results
            ],
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Google Lens reverse-image "
            "search using SerpApi"
        )
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Path to input image"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of results"
    )

    parser.add_argument(
        "--output",
        default="search_results.json",
        help="Output JSON file"
    )

    args = parser.parse_args()

    print()
    print("=" * 60)
    print(
        "Google Lens Reverse Image Search"
    )
    print("=" * 60)
    print()

    try:

        results = google_lens_search(
            args.image,
            args.max_results
        )

        print()
        print(
            f"Found {len(results)} result(s)."
        )
        print()

        for index, result in enumerate(
            results,
            start=1
        ):

            print(
                f"[{index}] {result.title}"
            )

            print(
                f"    URL: {result.url}"
            )

            if result.snippet:

                print(
                    f"    {result.snippet}"
                )

            print()

        save_results(
            results,
            args.output
        )

        print(
            f"Results saved to: {args.output}"
        )

    except Exception as exc:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print()
        print(exc)
        print()

        raise