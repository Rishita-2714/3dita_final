#!/usr/bin/env python3
"""
GRNet-compatible point cloud completion inference script.

Implements high-quality algorithmic completion that works on CPU without any
pre-trained checkpoint. Optimised for rotationally-symmetric archaeological
artefacts (rings, amalaka, bangles, seals).

Interface expected by grnet_adapter.py:
    python inference.py <config> <checkpoint>
        --pc         input.npy          (Nx3 float32, normalised)
        --out_pc_root  output/          (directory)
        --device     cpu
        --profile    balanced|hq|preview

Writes:  output/<stem>/fine.npy   (2048 x 3, float32)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree  # type: ignore[import]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_input(pc_path: Path) -> np.ndarray:
    data = np.load(str(pc_path)).astype(np.float64)
    if data.ndim == 3:
        data = data[0]
    if data.shape[0] == 3 and data.ndim == 2:
        data = data.T          # (3, N) -> (N, 3)
    return data[:, :3].copy()


# ---------------------------------------------------------------------------
# Geometry utilities
# ---------------------------------------------------------------------------

def _principal_axes(points: np.ndarray):
    """Return (center, eigenvectors sorted ascending) via PCA."""
    center = np.median(points, axis=0)
    centered = points - center
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    order = np.argsort(eigenvalues)
    return center, eigenvectors[:, order], eigenvalues[order]


def _local_frame(axis: np.ndarray):
    """Build orthonormal frame (axis, u, v)."""
    axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
    helper = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(axis, helper))) > 0.88:
        helper = np.array([0.0, 1.0, 0.0])
    u = np.cross(axis, helper)
    u /= max(float(np.linalg.norm(u)), 1e-9)
    v = np.cross(axis, u)
    v /= max(float(np.linalg.norm(v)), 1e-9)
    return u, v


def _cloud_extent(points: np.ndarray) -> float:
    return max(float(np.linalg.norm(points.max(axis=0) - points.min(axis=0))), 1e-6)


# ---------------------------------------------------------------------------
# Core completion strategies
# ---------------------------------------------------------------------------

def _cylindrical_completion(
    points: np.ndarray,
    axis: np.ndarray,
    center: np.ndarray,
    profile: str,
) -> np.ndarray:
    """
    Fill missing angular/axial sectors of a cylindrical object by inferring
    the radial profile from occupied cells and generating support points.
    """
    u, v = _local_frame(axis)
    centered = points - center
    t = centered @ axis
    pu = centered @ u
    pv = centered @ v
    r = np.sqrt(pu ** 2 + pv ** 2)
    theta = np.arctan2(pv, pu)

    axial_bins  = 128 if profile == "hq" else 96 if profile == "balanced" else 72
    angular_bins = 192 if profile == "hq" else 160 if profile == "balanced" else 128

    t_min, t_max = float(np.percentile(t, 1.5)), float(np.percentile(t, 98.5))
    if t_max <= t_min:
        t_min, t_max = float(t.min()), float(t.max())
    if t_max <= t_min:
        return np.empty((0, 3))

    t_edges     = np.linspace(t_min, t_max, axial_bins + 1)
    theta_edges = np.linspace(-np.pi, np.pi, angular_bins + 1)
    t_centers   = (t_edges[:-1] + t_edges[1:]) * 0.5
    theta_centers = (theta_edges[:-1] + theta_edges[1:]) * 0.5

    ti  = np.clip(np.searchsorted(t_edges,     t,     side="right") - 1, 0, axial_bins  - 1)
    thi = np.clip(np.searchsorted(theta_edges, theta, side="right") - 1, 0, angular_bins - 1)

    radius_sums   = np.zeros((axial_bins, angular_bins))
    radius_counts = np.zeros((axial_bins, angular_bins), dtype=np.int32)
    np.add.at(radius_sums,   (ti, thi), r)
    np.add.at(radius_counts, (ti, thi), 1)

    dense    = radius_counts >= 2
    occupied = radius_counts >  0
    mean_r   = np.where(occupied, radius_sums / np.maximum(radius_counts, 1), 0.0)

    new_pts: list[np.ndarray] = []
    for ti_idx in range(axial_bins):
        row_occ   = occupied[ti_idx]
        row_dense = dense[ti_idx]
        occ_count = int(row_occ.sum())
        if occ_count < max(8, angular_bins // 10):
            continue
        ring_r = float(np.median(mean_r[ti_idx, row_occ]))
        if ring_r <= 1e-6:
            continue
        # Interpolate missing sectors from neighbours
        for thi_idx in range(angular_bins):
            if row_dense[thi_idx]:
                continue
            left  = (thi_idx - 1) % angular_bins
            right = (thi_idx + 1) % angular_bins
            if not (row_occ[left] or row_occ[right]):
                if occ_count < angular_bins // 4:
                    continue
            ang = theta_centers[thi_idx]
            tval = t_centers[ti_idx]
            pt = (tval * axis
                  + np.cos(ang) * ring_r * u
                  + np.sin(ang) * ring_r * v)
            new_pts.append(pt)

    if not new_pts:
        return np.empty((0, 3))
    return np.asarray(new_pts, dtype=np.float64) + center


def _rotational_completion(
    points: np.ndarray,
    axis: np.ndarray,
    center: np.ndarray,
    profile: str,
) -> np.ndarray:
    """
    Generate candidate points by rotating a seed subset around the symmetry
    axis at several angles and keeping only those that land in sparse regions.
    """
    n_steps = 9 if profile == "hq" else 7 if profile == "balanced" else 5
    angles  = [2.0 * np.pi * k / n_steps for k in range(1, n_steps)]

    max_seed = min(len(points), 20000)
    seed_idx = np.linspace(0, len(points) - 1, max_seed, dtype=int)
    seed     = points[seed_idx]

    def _rot(pts, angle):
        ax = axis / max(float(np.linalg.norm(axis)), 1e-9)
        x, y, z = ax
        c, s = np.cos(angle), np.sin(angle)
        R = np.array([
            [c + x*x*(1-c),   x*y*(1-c) - z*s, x*z*(1-c) + y*s],
            [y*x*(1-c) + z*s, c + y*y*(1-c),   y*z*(1-c) - x*s],
            [z*x*(1-c) - y*s, z*y*(1-c) + x*s, c + z*z*(1-c)  ],
        ])
        return (pts - center) @ R.T + center

    extent       = _cloud_extent(points)
    sparse_r     = max(extent / 200.0, 0.005)
    max_gap      = max(extent / 5.0,   sparse_r * 12.0)

    kd    = cKDTree(points)
    candidates: list[np.ndarray] = []
    for angle in angles:
        rot = _rot(seed, angle)
        dists, _ = kd.query(rot, k=1)
        mask = (dists >= sparse_r) & (dists <= max_gap)
        if mask.any():
            candidates.append(rot[mask])

    if not candidates:
        return np.empty((0, 3))
    return np.concatenate(candidates, axis=0)


def _surface_interpolation(points: np.ndarray, profile: str) -> np.ndarray:
    """
    Simple surface diffusion: project candidate points onto the locally
    estimated tangent plane to create smooth in-fill near boundaries.
    """
    if len(points) < 32:
        return np.empty((0, 3))

    extent  = _cloud_extent(points)
    radius  = max(extent / 60.0, 0.01)
    kd      = cKDTree(points)
    rng     = np.random.default_rng(0)

    # Sample boundary region: points with low local density
    counts  = kd.query_ball_point(points, radius, return_length=True)
    sparse_mask = counts < int(np.percentile(counts, 20))
    if not sparse_mask.any():
        return np.empty((0, 3))

    sparse_pts = points[sparse_mask]
    interp: list[np.ndarray] = []
    max_gen = 5000 if profile == "hq" else 3000 if profile == "balanced" else 1500

    for i in range(0, min(len(sparse_pts), max_gen)):
        pt = sparse_pts[i]
        idxs = kd.query_ball_point(pt, radius * 2.5)
        if len(idxs) < 4:
            continue
        neighbourhood = points[np.asarray(idxs)]
        local_center  = neighbourhood.mean(axis=0)
        cov           = np.cov((neighbourhood - local_center).T)
        eigvals, eigvecs = np.linalg.eigh(cov)
        normal = eigvecs[:, 0]           # smallest eigenvalue → normal direction
        # Project a small random displacement onto the tangent plane
        disp   = rng.normal(0, radius * 0.4, size=3)
        disp   -= normal * float(np.dot(disp, normal))
        candidate = pt + disp
        interp.append(candidate)

    if not interp:
        return np.empty((0, 3))
    return np.asarray(interp, dtype=np.float64)


# ---------------------------------------------------------------------------
# Deduplication / subsampling helpers
# ---------------------------------------------------------------------------

def _voxel_downsample(points: np.ndarray, voxel_size: float) -> np.ndarray:
    if len(points) == 0:
        return points
    voxel_size = max(float(voxel_size), 1e-9)
    keys = np.floor(points / voxel_size).astype(np.int64)
    _, unique_idx = np.unique(keys, axis=0, return_index=True)
    return points[unique_idx]


def _remove_outliers(points: np.ndarray, nb_neighbors: int = 20, std_ratio: float = 2.2) -> np.ndarray:
    if len(points) < nb_neighbors + 1:
        return points
    kd     = cKDTree(points)
    dists, _ = kd.query(points, k=nb_neighbors + 1)
    mean_d = dists[:, 1:].mean(axis=1)
    mu, sigma = float(mean_d.mean()), float(mean_d.std())
    keep = mean_d <= mu + std_ratio * sigma
    return points[keep]


def _to_target(points: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    if len(points) >= n:
        idx = np.linspace(0, len(points) - 1, n, dtype=int)
        return points[idx]
    # Upsample with tiny jitter
    extent  = _cloud_extent(points)
    needed  = n - len(points)
    extra_i = rng.integers(0, len(points), size=needed)
    jitter  = rng.normal(0, extent * 0.003, size=(needed, 3))
    return np.concatenate([points, points[extra_i] + jitter], axis=0)


# ---------------------------------------------------------------------------
# Main completion pipeline
# ---------------------------------------------------------------------------

TARGET_POINTS = 2048


def complete(points: np.ndarray, profile: str) -> np.ndarray:
    rng = np.random.default_rng(42)

    if len(points) < 8:
        return _to_target(points if len(points) > 0 else np.zeros((1, 3)), TARGET_POINTS, rng)

    center, eigvecs, eigvals = _principal_axes(points)
    # Primary axis = largest eigenvalue (longest dimension)
    primary_axis = eigvecs[:, -1]

    extent      = _cloud_extent(points)
    voxel_small = max(extent / 1400.0, 0.003)
    voxel_merge = max(extent / 700.0,  0.006)

    # --- Strategy 1: cylindrical ring completion ---
    cyl_pts = _cylindrical_completion(points, primary_axis, center, profile)

    # --- Strategy 2: rotational symmetry completion ---
    rot_pts = _rotational_completion(points, primary_axis, center, profile)

    # --- Strategy 3: surface interpolation near boundaries ---
    surf_pts = _surface_interpolation(points, profile)

    # Merge all candidates
    pieces = [points]
    for extra in (cyl_pts, rot_pts, surf_pts):
        if len(extra) > 0:
            pieces.append(extra)

    merged = np.concatenate(pieces, axis=0)
    merged = _voxel_downsample(merged, voxel_small)
    merged = _remove_outliers(merged, nb_neighbors=16, std_ratio=2.5)

    # Remove candidates that are too far from the original surface
    if len(merged) > 0 and len(points) > 0:
        kd     = cKDTree(points)
        dists, _ = kd.query(merged, k=1)
        max_reach = max(extent / 3.0, voxel_merge * 20.0)
        merged = merged[dists <= max_reach]

    if len(merged) == 0:
        merged = points.copy()

    merged = _voxel_downsample(merged, voxel_merge)
    merged = _to_target(merged, TARGET_POINTS, rng)

    print(
        f"[GRNet-geometric] {len(points)} partial -> {len(merged)} completed  "
        f"(cyl={len(cyl_pts)}, rot={len(rot_pts)}, surf={len(surf_pts)})",
        file=sys.stderr,
        flush=True,
    )

    return merged.astype(np.float32)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="GRNet-compatible inference")
    parser.add_argument("config",      type=str, help="Path to config YAML (unused)")
    parser.add_argument("checkpoint",  type=str, help="Path to checkpoint (unused)")
    parser.add_argument("--pc",          required=True, help="Input .npy point cloud")
    parser.add_argument("--out_pc_root", required=True, help="Output root directory")
    parser.add_argument("--device",      default="cpu")
    parser.add_argument("--profile",     default="balanced",
                        choices=["hq", "balanced", "preview"])
    args = parser.parse_args()

    pc_path  = Path(args.pc)
    out_root = Path(args.out_pc_root)

    points    = load_input(pc_path)
    completed = complete(points, args.profile)

    out_dir = out_root / pc_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(str(out_dir / "fine.npy"), completed)

    print(
        f"[GRNet] Wrote {len(completed)} points to {out_dir / 'fine.npy'}",
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    main()
