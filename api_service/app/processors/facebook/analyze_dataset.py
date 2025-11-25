"""Analyze a saved Facebook Apify dataset CSV and pick best publications.

Usage:
    python analyze_dataset.py --run-id <run_id> [--top N]

The script reads:
    api_service/datasets/saved_datasets/facebook/<run_id>/<run_id>.csv

It computes per-ad metrics and a heuristic score. The main public
functions are `analyze(csv_path, method, weights)` and
`analyze_jsonl(jsonl_path, method, weights)`.
"""
from __future__ import annotations

import ast
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_snapshot(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        obj = ast.literal_eval(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return None


def extract_media_urls(snapshot: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    if not isinstance(snapshot, dict):
        return urls
    for im in snapshot.get("images", []) or []:
        if isinstance(im, dict):
            u = im.get("original_image_url")
            if u:
                urls.append(str(u))
    for c in snapshot.get("cards", []) or []:
        if isinstance(c, dict):
            u = c.get("original_image_url")
            if u:
                urls.append(str(u))
    for v in snapshot.get("videos", []) or []:
        if isinstance(v, dict):
            u = v.get("video_preview_image_url") or v.get("video_sd_url")
            if u:
                urls.append(str(u))
    u = snapshot.get("page_profile_picture_url")
    if u:
        urls.append(str(u))
    return [x for x in urls if x]


def to_number(s: Any) -> Optional[float]:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None


def _compute_score(ent: Dict[str, Any], weights: Dict[str, float]) -> float:
    reach = ent.get("reach") or 0
    spend = ent.get("spend") or 0
    images = ent.get("images", 0) or 0
    videos = ent.get("videos", 0) or 0

    media = float(images + videos)
    has_video = 1.0 if videos > 0 else 0.0

    reach_s = math.log1p(reach) if reach else 0.0
    spend_s = math.log1p(spend) if spend else 0.0
    page_like_s = math.log1p(ent.get("page_like_count", 0) or 0)

    score = (
        weights.get("reach", 0.6) * reach_s
        + weights.get("spend", 0.2) * spend_s
        + weights.get("media", 1.0) * media
        + weights.get("video", 0.5) * has_video
        + weights.get("page_like", 0.1) * page_like_s
    )
    return float(score)


def analyze(
    csv_path: Path,
    method: str = "heuristic",
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, Any]]:
    if weights is None:
        weights = {}
    stats: Dict[str, Dict[str, Any]] = {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ad_id = row.get("ad_archive_id") or row.get("ad_id") or "unknown"
            raw = row.get("snapshot")
            snapshot = parse_snapshot(raw)
            imgs = 0
            vids = 0
            urls: List[str] = []
            page_like = None
            if snapshot:
                urls = extract_media_urls(snapshot)
                imgs = len(snapshot.get("images") or [])
                imgs += len(snapshot.get("cards") or [])
                vids = len(snapshot.get("videos") or [])
                page_like = to_number(snapshot.get("page_like_count"))
            reach = to_number(row.get("reach_estimate"))
            spend = to_number(row.get("spend"))

            ent = stats.setdefault(
                ad_id,
                {
                    "ad_id": ad_id,
                    "rows": 0,
                    "images": 0,
                    "videos": 0,
                    "urls": [],
                    "reach": None,
                    "spend": None,
                    "page_like_count": 0,
                },
            )
            ent["rows"] += 1
            ent["images"] += imgs
            ent["videos"] += vids
            ent["urls"].extend(urls)
            if page_like:
                cur = ent.get("page_like_count") or 0
                ent["page_like_count"] = max(cur, page_like)
            if reach is not None:
                ent["reach"] = max(reach, ent.get("reach") or 0)
            if spend is not None:
                ent["spend"] = max(spend, ent.get("spend") or 0)

    for ad_id, ent in stats.items():
        ent["urls"] = list(dict.fromkeys(ent["urls"]))
        ent["total_media"] = ent["images"] + ent["videos"]
        if method == "heuristic":
            ent["score"] = _compute_score(ent, weights)
        else:
            ent["score"] = float(ent["total_media"])
    return stats


def analyze_jsonl(
    jsonl_path: Path,
    method: str = "heuristic",
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, Any]]:
    if weights is None:
        weights = {}
    stats: Dict[str, Dict[str, Any]] = {}
    with jsonl_path.open("r", encoding="utf-8") as jf:
        for line in jf:
            try:
                item = json.loads(line)
            except Exception:
                continue
            ad_id = (
                item.get("ad_archive_id")
                or item.get("adArchiveID")
                or item.get("id")
                or "unknown"
            )
            snap = item.get("snapshot") or {}
            if isinstance(snap, dict):
                imgs = len(snap.get("images") or [])
                imgs += len(snap.get("cards") or [])
                vids = len(snap.get("videos") or [])
                urls = extract_media_urls(snap)
                page_like = to_number(snap.get("page_like_count"))
            else:
                imgs = 0
                vids = 0
                urls = []
                page_like = None

            reach = to_number(item.get("reach_estimate"))
            spend = to_number(item.get("spend"))

            ent = stats.setdefault(
                ad_id,
                {
                    "ad_id": ad_id,
                    "rows": 0,
                    "images": 0,
                    "videos": 0,
                    "urls": [],
                    "reach": None,
                    "spend": None,
                    "page_like_count": 0,
                },
            )
            ent["rows"] += 1
            ent["images"] += imgs
            ent["videos"] += vids
            ent["urls"].extend(urls)
            if page_like:
                cur = ent.get("page_like_count") or 0
                ent["page_like_count"] = max(cur, page_like)
            if reach is not None:
                ent["reach"] = max(reach, ent.get("reach") or 0)
            if spend is not None:
                ent["spend"] = max(spend, ent.get("spend") or 0)

    for ad_id, ent in stats.items():
        ent["urls"] = list(dict.fromkeys(ent["urls"]))
        ent["total_media"] = ent["images"] + ent["videos"]
        if method == "heuristic":
            ent["score"] = _compute_score(ent, weights)
        else:
            ent["score"] = float(ent["total_media"])

    return stats


def main(argv: Optional[List[str]] = None) -> int:
    import argparse as _arg

    parser = _arg.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--base-dir",
        default="datasets/saved_datasets/facebook",
        help="relative to api_service/ working dir",
    )
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args(argv)

    base = Path(args.base_dir)
    csv_path = base / args.run_id / f"{args.run_id}.csv"
    if not csv_path.exists():
        print("CSV not found:", csv_path)
        return 2

    stats = analyze(csv_path)
    items = sorted(
        stats.values(), key=lambda x: x.get("score", 0), reverse=True
    )
    print("Found", len(items), "distinct ads. Top", args.top, "by score:")
    for i, ent in enumerate(items[: args.top], 1):
        out = (
            f"{i}. ad_id={ent['ad_id']}, score={ent['score']:.2f}, "
            + f"images={ent['images']}, videos={ent['videos']}, "
            + f"reach={ent.get('reach')}, spend={ent.get('spend')}, "
            + f"urls={len(ent['urls'])}"
        )
        print(out)

    if items:
        top = items[0]
        print("\nSample URLs from best ad:")
        for j, u in enumerate(top["urls"][:50], 1):
            print(j, u)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
