"""Download images and video previews from a saved Facebook Apify dataset CSV.

Usage:
    python download_images_from_csv.py --run-id yHAmj34fDeR94qUrh

This script expects datasets saved under:
    api_service/datasets/saved_datasets/facebook/<run_id>/<run_id>.csv

It parses the `snapshot` column (string or JSON) and extracts image/video URLs
from keys like `images[*].original_image_url`, `cards[*].original_image_url`,
`videos[*].video_preview_image_url`, `page_profile_picture_url`, etc.

Outputs:
 - media files saved under: api_service/datasets/saved_datasets/facebook/<run_id>/media/
 - a small report JSON saved as media/report.json with counts and failures.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse, unquote

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


LOG = logging.getLogger("download_images")


def make_session(retries: int = 3, backoff: float = 0.5, status_forcelist=(500, 502, 503, 504)) -> requests.Session:
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist,
                  allowed_methods=["GET", "HEAD"])  # type: ignore[arg-type]
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "facebook-dataset-downloader/1.0"})
    return s


def sanitize_filename(s: str) -> str:
    s = unquote(s)
    # keep common filename chars, replace others
    s = re.sub(r"[^0-9A-Za-z._-]", "_", s)
    return s[:200]


def extract_urls_from_snapshot(snapshot: Any) -> List[str]:
    urls: List[str] = []
    if not isinstance(snapshot, dict):
        return urls

    # page profile picture
    p = snapshot.get("page_profile_picture_url")
    if p:
        urls.append(p)

    # page-level images inside nested page/ad_library_page_info
    page = snapshot.get("page")
    if isinstance(page, dict):
        about = page.get("about")
        # profile and cover inside ad_library_page_info
    ad_info = snapshot.get("ad_library_page_info") or snapshot.get(
        "ad_library_page_info")
    if isinstance(ad_info, dict):
        page_info = ad_info.get("page_info")
        if isinstance(page_info, dict):
            pf = page_info.get("profile_photo") or page_info.get(
                "page_cover_photo")
            if pf:
                urls.append(pf)

    # cards
    for c in snapshot.get("cards", []) or []:
        if isinstance(c, dict):
            v = c.get("original_image_url") or c.get("resized_image_url")
            if v:
                urls.append(v)

    # images
    for im in snapshot.get("images", []) or []:
        if isinstance(im, dict):
            for k in ("original_image_url", "resized_image_url", "resized_image_url", "watermarked_resized_image_url"):
                vv = im.get(k)
                if vv:
                    urls.append(vv)

    # extra_images
    for ei in snapshot.get("extra_images", []) or []:
        if isinstance(ei, dict):
            for k in ("original_image_url", "resized_image_url"):
                vv = ei.get(k)
                if vv:
                    urls.append(vv)

    # videos: prefer preview image, then SD/HD urls (we won't attempt to store full mp4 unless asked)
    for vid in snapshot.get("videos", []) or []:
        if isinstance(vid, dict):
            for k in ("video_preview_image_url", "video_sd_url", "video_hd_url"):
                vv = vid.get(k)
                if vv:
                    urls.append(vv)

    # fallback: any key that looks like an image url
    def find_urls(obj: Any) -> Iterable[str]:
        if isinstance(obj, str):
            if obj.startswith("http") and (".jpg" in obj or ".png" in obj or ".jpeg" in obj or ".webp" in obj):
                yield obj
        elif isinstance(obj, dict):
            for val in obj.values():
                yield from find_urls(val)
        elif isinstance(obj, list):
            for item in obj:
                yield from find_urls(item)

    # try to gather any additional image-like urls
    for u in find_urls(snapshot):
        urls.append(u)

    # unique while preserving order
    seen: Set[str] = set()
    out: List[str] = []
    for u in urls:
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def parse_snapshot_field(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    # many CSVs store a Python repr (single quotes). Try ast.literal_eval first.
    try:
        obj = ast.literal_eval(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # try JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # last resort: try to massage quotes: replace single quotes with double when safe
    try:
        raw2 = raw.replace("\\'", "'")
        raw2 = raw2.replace("'", '"')
        obj = json.loads(raw2)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None


def iter_csv_snapshot_rows(csv_path: Path) -> Iterable[Tuple[Dict[str, str], Optional[Dict[str, Any]]]]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw = row.get("snapshot") or row.get("snapshot", "")
            parsed = parse_snapshot_field(raw)
            yield row, parsed


def download_one(session: requests.Session, url: str, out_dir: Path, prefix: Optional[str] = None, timeout: int = 30) -> Tuple[str, Optional[str]]:
    # returns (url, saved_path or None)
    try:
        parsed = urlparse(url)
        name = Path(parsed.path).name or parsed.netloc
        if not name:
            name = parsed.netloc
        name = sanitize_filename(name)
        if prefix:
            name = f"{sanitize_filename(prefix)}_{name}"
        out_path = out_dir / name
        # avoid overwriting
        base = out_path.stem
        ext = out_path.suffix
        i = 1
        while out_path.exists():
            out_path = out_dir / f"{base}_{i}{ext}"
            i += 1
        resp = session.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(8192):
                if chunk:
                    fh.write(chunk)
        return url, str(out_path)
    except Exception as exc:
        LOG.debug("failed to download %s: %s", url, exc)
        return url, None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True,
                        help="Run id (folder name) in saved_datasets/facebook/")
    parser.add_argument("--base-dir", default="api_service/datasets/saved_datasets/facebook",
                        help="Base dir where runs are saved")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max number of images to download (0 = unlimited)")
    parser.add_argument("--workers", type=int, default=6,
                        help="Concurrent download workers")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only list URLs, do not download")
    parser.add_argument("--report", action="store_true",
                        help="Save a JSON report in the media folder")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    base = Path(args.base_dir)
    run_dir = base / args.run_id
    csv_path = run_dir / f"{args.run_id}.csv"
    if not csv_path.exists():
        LOG.error("CSV not found: %s", csv_path)
        return 2

    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    found_urls: List[Tuple[str, str]] = []  # (ad_id, url)
    failures: List[Tuple[str, str]] = []

    for row, snapshot in iter_csv_snapshot_rows(csv_path):
        ad_id = row.get("ad_archive_id") or row.get(
            "ad_id") or row.get("adArchiveId") or "unknown"
        if not snapshot:
            continue
        urls = extract_urls_from_snapshot(snapshot)
        for u in urls:
            found_urls.append((ad_id, u))

    LOG.info("Found %d unique urls in snapshots", len(found_urls))

    if args.dry_run:
        # print first 100
        for i, (ad_id, u) in enumerate(found_urls[:100], 1):
            print(i, ad_id, u)
        return 0

    session = make_session()

    to_download = found_urls
    if args.limit and args.limit > 0:
        to_download = to_download[: args.limit]

    saved: List[Tuple[str, str, str]] = []  # (ad_id, url, path)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = []
        for ad_id, url in to_download:
            futures.append(ex.submit(download_one, session,
                           url, media_dir, prefix=ad_id))
        for fut in as_completed(futures):
            url, path = fut.result()
            if path:
                saved.append((ad_id, url, path))
            else:
                failures.append((ad_id, url))

    LOG.info("Downloaded %d files, %d failures", len(saved), len(failures))

    if args.report:
        report = {
            "run_id": args.run_id,
            "total_found": len(found_urls),
            "downloaded": len(saved),
            "failures": len(failures),
            "files": [s[2] for s in saved],
        }
        with open(media_dir / "report.json", "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

    # print short summary
    print(
        f"Found {len(found_urls)} urls; downloaded {len(saved)} files; failures {len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
