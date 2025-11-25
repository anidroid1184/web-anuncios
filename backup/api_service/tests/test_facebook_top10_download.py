from app.processors.facebook.download_images_from_csv import (
    iter_csv_snapshot_rows,
    extract_urls_from_snapshot,
)
from app.processors.facebook.analyze_dataset import analyze
import sys
from pathlib import Path
import csv


# Ensure api_service packages are importable when tests run from this folder
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# import after path tweak


def create_test_csv(csv_path: Path, ads: int = 12):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["ad_archive_id", "snapshot", "reach_estimate", "spend"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for i in range(1, ads + 1):
            ad_id = f"ad_{i}"
            # create varying number of images per ad
            imgs = []
            for j in range(1, (i % 4) + 2):
                imgs.append(
                    {"original_image_url": f"http://example.com/{ad_id}_img{j}.jpg"}
                )
            snapshot = {"images": imgs, "videos": []}
            # set reach so that higher i -> higher reach
            reach = i * 100
            spend = i * 5
            # write as Python repr so parse_snapshot (ast.literal_eval) can load it
            writer.writerow([ad_id, repr(snapshot), str(reach), str(spend)])


def test_top10_and_download_simulation(tmp_path: Path):
    run_id = "test_run"
    run_dir = tmp_path / run_id
    csv_path = run_dir / f"{run_id}.csv"

    # create CSV with 12 ads
    create_test_csv(csv_path, ads=12)

    # analyze and pick top ads
    stats = analyze(csv_path)
    items = sorted(
        stats.values(), key=lambda x: x.get("score", 0), reverse=True
    )
    top_ads = [it.get("ad_id") for it in items[:10]]

    assert len(top_ads) == 10

    # simulate download: create media dir and create files only for top_ads
    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    expected_files = []
    # iterate rows and for top ads, 'download' each URL by creating a file
    total_urls = 0
    for row, snapshot in iter_csv_snapshot_rows(csv_path):
        ad_id = row.get("ad_archive_id") or row.get("ad_id") or "unknown"
        if ad_id not in top_ads:
            continue
        if not snapshot:
            continue
        urls = extract_urls_from_snapshot(snapshot)
        for u in urls:
            total_urls += 1
            fname = u.split("/")[-1]
            fpath = media_dir / f"{ad_id}_{fname}"
            fpath.write_bytes(b"fakeimage")
            expected_files.append(str(fpath))

    # assert files created equals expected count
    created = list(media_dir.iterdir())
    assert len(created) == total_urls

    # cross-check: expected_files exist
    for p in expected_files:
        assert Path(p).exists()
