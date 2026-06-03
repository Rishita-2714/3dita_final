#!/usr/bin/env python3
"""Submit the bundled sample_before.ply to the local backend with aggressive
repair and completion parameters, poll the job until complete, and download
the outputs into the backend static/mock folder for inspection.

Run from the repository root or the `Frontend_3dita` folder.
"""
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except Exception:
    print("The 'requests' package is required. Install with: python -m pip install requests")
    sys.exit(2)

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static" / "mock"
STATIC.mkdir(parents=True, exist_ok=True)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8010")

def submit_job(sample_path: Path) -> str:
    url = f"{BACKEND_URL}/api/reconstruct"
    params = {
        "enable_hole_detection": True,
        "enable_trimesh_repair": True,
        "force_completion": True,
        "profile": "hq",
        "mesh_method": "poisson",
        "central_void_min_ratio": 0.12,
        "central_void_cap_segments": 64,
        "preserve_output_density": True,
        "hole_detection_max_points": 140000,
        "hole_mask_padding": 0.42,
        "full_resolution_meshing": True,
        "detail": 11,
        "completion_model": "pointr",
    }

    with sample_path.open("rb") as fp:
        files = {"file": (sample_path.name, fp, "application/octet-stream")}
        data = {"model": "dl_completion", "params": json.dumps(params)}
        print(f"Posting {sample_path} to {url} with aggressive DL completion params...")
        resp = requests.post(url, files=files, data=data, timeout=60)

    resp.raise_for_status()
    body = resp.json()
    job_id = body.get("job_id")
    if not job_id:
        raise RuntimeError(f"Failed to get job id: {body}")
    print(f"Submitted job_id={job_id}")
    return job_id


def poll_job(job_id: str, interval: float = 3.0, timeout: float = 600.0) -> dict:
    url = f"{BACKEND_URL}/api/job/{job_id}"
    start = time.time()
    while True:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            body = resp.json()
            status = body.get("status")
            progress = body.get("progress")
            print(f"job={job_id} status={status} progress={progress}")
            if status in {"done", "complete", "completed"}:
                return body
            if status in {"failed", "error"}:
                raise RuntimeError(f"Job failed: {body.get('message')}")
        else:
            print(f"Unexpected status when polling job: {resp.status_code} {resp.text}")

        if time.time() - start > timeout:
            raise TimeoutError("Polling timed out")
        time.sleep(interval)


def download_url(url: str, target: Path) -> None:
    if not url:
        return
    print(f"Downloading {url} -> {target}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    target.write_bytes(resp.content)


def main():
    sample = STATIC / "sample_before.ply"
    if not sample.exists():
        # Maybe the frontend mock has it; try relative path
        alt = BASE.parent / "frontend" / "public" / "mock" / "sample_before.ply"
        if alt.exists():
            sample = alt
        else:
            print("Could not find sample_before.ply in backend static or frontend mock.")
            sys.exit(2)

    job_id = submit_job(sample)
    result = poll_job(job_id, interval=3.0, timeout=1800.0)

    after_url = result.get("after_url")
    added_url = result.get("added_geometry_url")
    restored_url = result.get("restored_regions_url")
    panel_url = result.get("restoration_panel_url")

    out_dir = STATIC
    if after_url:
        download_url(after_url, out_dir / f"{job_id}_after.ply")
    if added_url:
        download_url(added_url, out_dir / f"{job_id}_added.ply")
    if restored_url:
        download_url(restored_url, out_dir / f"{job_id}_restored_regions.ply")
    if panel_url:
        download_url(panel_url, out_dir / f"{job_id}_panel.ply")

    metadata = result.get("metadata") or {}
    print("Job completed. Metadata summary:")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}")
        raise
