from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - runtime dependency
    o3d = None

from .merge import merge_observed_and_completed
from .pointr_adapter import PoinTrAdapter
from .grnet_adapter import GRNetAdapter

_POINTR_ADAPTER: PoinTrAdapter | None = None
_GRNET_ADAPTER: GRNetAdapter | None = None


def _copy_cloud(point_cloud):
    copied = o3d.geometry.PointCloud()
    copied.points = o3d.utility.Vector3dVector(point_cloud.points)
    if point_cloud.has_colors():
        copied.colors = o3d.utility.Vector3dVector(point_cloud.colors)
    if point_cloud.has_normals():
        copied.normals = o3d.utility.Vector3dVector(point_cloud.normals)
    return copied


def _get_pointr_adapter() -> PoinTrAdapter:
    global _POINTR_ADAPTER
    if _POINTR_ADAPTER is None:
        _POINTR_ADAPTER = PoinTrAdapter()
    return _POINTR_ADAPTER


def _get_grnet_adapter() -> GRNetAdapter:
    global _GRNET_ADAPTER
    if _GRNET_ADAPTER is None:
        _GRNET_ADAPTER = GRNetAdapter()
    return _GRNET_ADAPTER


def _select_completion_model(model_name: str | None = None):
    """Select the completion model to use.
    
    Priority:
    1. Explicit model_name parameter
    2. COMPLETION_MODEL environment variable
    3. Auto-select best available (GRNet > PointR)
    """
    if model_name is None:
        model_name = os.environ.get("COMPLETION_MODEL", "auto").lower()
    
    if model_name == "auto":
        # Try GRNet first (better quality), fall back to PointR
        grnet_adapter = _get_grnet_adapter()
        if grnet_adapter.is_available():
            return grnet_adapter, "grnet"
        pointr_adapter = _get_pointr_adapter()
        if pointr_adapter.is_available():
            return pointr_adapter, "pointr"
        # Neither available
        return None, "none"
    elif model_name == "grnet":
        grnet_adapter = _get_grnet_adapter()
        return grnet_adapter, "grnet"
    elif model_name == "pointr":
        pointr_adapter = _get_pointr_adapter()
        return pointr_adapter, "pointr"
    else:
        raise ValueError(f"Unknown completion model: {model_name}")


def _cloud_extent(point_cloud) -> float:
    extent = point_cloud.get_axis_aligned_bounding_box().get_extent()
    return max(float(np.linalg.norm(extent)), 1e-6)


def _shape_flatness(point_cloud) -> float:
    points = np.asarray(point_cloud.points)
    if len(points) < 16:
        return 1.0

    centered = points - np.mean(points, axis=0)
    eigenvalues = np.linalg.eigvalsh(np.cov(centered.T))
    largest = max(float(eigenvalues[-1]), 1e-9)
    return max(float(eigenvalues[0]) / largest, 0.0)


def _principal_axis_basis(points: np.ndarray):
    center = np.median(points, axis=0)
    centered = points - center
    covariance = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    axis = eigenvectors[:, np.argsort(eigenvalues)[-1]]
    axis = axis / max(np.linalg.norm(axis), 1e-9)

    helper = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(axis, helper))) > 0.88:
        helper = np.array([0.0, 1.0, 0.0])

    side_a = np.cross(axis, helper)
    side_a = side_a / max(np.linalg.norm(side_a), 1e-9)
    side_b = np.cross(axis, side_a)
    side_b = side_b / max(np.linalg.norm(side_b), 1e-9)
    basis = np.column_stack([axis, side_a, side_b])
    return center, basis


def _rotation_about_axis(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = axis / max(np.linalg.norm(axis), 1e-9)
    x, y, z = axis
    cosine = np.cos(angle)
    sine = np.sin(angle)
    cross_matrix = np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ]
    )
    outer = np.outer(axis, axis)
    return cosine * np.eye(3) + sine * cross_matrix + (1.0 - cosine) * outer


def _build_cylindrical_surface_completion(point_cloud, profile: str, params: Dict[str, Any]):
    points = np.asarray(point_cloud.points)
    if len(points) < 200:
        return None, {
            "completion_model": "local_cylindrical_surface",
            "completion_status": "too-few-points",
            "completion_used": False,
        }

    extent = _cloud_extent(point_cloud)
    center, basis = _principal_axis_basis(points)
    local_points = (points - center) @ basis
    t_values = local_points[:, 0]
    u_values = local_points[:, 1]
    v_values = local_points[:, 2]
    radii = np.sqrt((u_values * u_values) + (v_values * v_values))
    theta_values = (np.arctan2(v_values, u_values) + (2.0 * np.pi)) % (2.0 * np.pi)

    axial_bins = int(params.get("surface_completion_axial_bins", 160))
    angular_bins = int(params.get("surface_completion_angular_bins", 220))
    axial_bins = max(48, min(axial_bins, 180))
    angular_bins = max(64, min(angular_bins, 240))

    t_min = float(np.percentile(t_values, 1.0))
    t_max = float(np.percentile(t_values, 99.0))
    if not np.isfinite(t_min) or not np.isfinite(t_max) or t_max <= t_min:
        return None, {
            "completion_model": "local_cylindrical_surface",
            "completion_status": "invalid-axis-range",
            "completion_used": False,
        }

    t_edges = np.linspace(t_min, t_max, axial_bins + 1)
    theta_edges = np.linspace(0.0, 2.0 * np.pi, angular_bins + 1)
    t_indices = np.clip(np.searchsorted(t_edges, t_values, side="right") - 1, 0, axial_bins - 1)
    theta_indices = np.clip(
        np.searchsorted(theta_edges, theta_values, side="right") - 1,
        0,
        angular_bins - 1,
    )

    radius_sums = np.zeros((axial_bins, angular_bins), dtype=np.float64)
    radius_counts = np.zeros((axial_bins, angular_bins), dtype=np.int32)
    np.add.at(radius_sums, (t_indices, theta_indices), radii)
    np.add.at(radius_counts, (t_indices, theta_indices), 1)

    occupied = radius_counts > 0
    dense = radius_counts >= 3
    mean_radii = np.divide(
        radius_sums,
        np.maximum(radius_counts, 1),
        out=np.zeros_like(radius_sums),
        where=radius_counts > 0,
    )

    observed_cloud = point_cloud
    generated_points = []
    angular_centers = (theta_edges[:-1] + theta_edges[1:]) * 0.5
    t_centers = (t_edges[:-1] + t_edges[1:]) * 0.5

    for t_index in range(axial_bins):
        row_occupied = occupied[t_index]
        row_dense = dense[t_index]
        occupied_count = int(row_occupied.sum())
        if occupied_count < max(10, angular_bins // 8):
            continue

        occupied_radii = mean_radii[t_index, row_occupied]
        ring_radius = float(np.median(occupied_radii))
        if not np.isfinite(ring_radius) or ring_radius <= 1e-6:
            continue

        for theta_index in range(angular_bins):
            if row_dense[theta_index]:
                continue

            left = (theta_index - 1) % angular_bins
            right = (theta_index + 1) % angular_bins
            local_neighbors = row_dense[left] or row_dense[right]
            # Fill broad missing sectors too, but skip fully unreliable rings.
            if not local_neighbors and occupied_count < angular_bins // 3:
                continue

            theta = angular_centers[theta_index]
            radius = ring_radius
            local = np.array([
                t_centers[t_index],
                np.cos(theta) * radius,
                np.sin(theta) * radius,
            ])
            generated_points.append(local @ basis.T + center)

    if not generated_points:
        return None, {
            "completion_model": "local_cylindrical_surface",
            "completion_status": "no-empty-surface-cells",
            "completion_used": False,
        }

    candidate_points = np.asarray(generated_points, dtype=np.float64)
    candidate_cloud = o3d.geometry.PointCloud()
    candidate_cloud.points = o3d.utility.Vector3dVector(candidate_points)
    distances = np.asarray(candidate_cloud.compute_point_cloud_distance(observed_cloud))

    sparse_radius = float(params.get("surface_completion_radius", 0.0) or 0.0)
    if sparse_radius <= 0:
        sparse_radius = max(extent / 260.0, 0.006)

    max_gap = float(params.get("surface_completion_max_gap", 0.0) or 0.0)
    if max_gap <= 0:
        max_gap = max(extent / 5.5, sparse_radius * 10.0)

    keep_mask = (distances >= sparse_radius) & (distances <= max_gap)
    kept_points = candidate_points[keep_mask]
    if len(kept_points) == 0:
        return None, {
            "completion_model": "local_cylindrical_surface",
            "completion_status": "surface-candidates-too-close-or-far",
            "completion_used": False,
            "completion_radius": round(sparse_radius, 6),
        }

    max_ratio = 0.9 if profile == "hq" else 0.72 if profile == "balanced" else 0.58
    max_points = max(1, int(len(points) * max_ratio))
    if len(kept_points) > max_points:
        selection = np.linspace(0, len(kept_points) - 1, max_points, dtype=int)
        kept_points = kept_points[selection]

    completed_cloud = o3d.geometry.PointCloud()
    completed_cloud.points = o3d.utility.Vector3dVector(kept_points)
    completed_cloud = completed_cloud.voxel_down_sample(max(sparse_radius * 0.32, extent / 1800.0))

    return completed_cloud, {
        "completion_model": "local_cylindrical_surface",
        "completion_status": "local-cylindrical-surface-fallback",
        "completion_axis": [round(float(value), 5) for value in basis[:, 0]],
        "completion_axial_bins": axial_bins,
        "completion_angular_bins": angular_bins,
        "completion_candidate_points": int(len(candidate_points)),
        "completion_radius": round(sparse_radius, 6),
        "completion_max_gap": round(max_gap, 6),
        "completion_used": len(completed_cloud.points) > 0,
    }


def _build_rotational_candidates(point_cloud, profile: str, params: Dict[str, Any]):
    points = np.asarray(point_cloud.points)
    if len(points) < 64:
        return None, {
            "completion_model": "local_rotational_symmetry",
            "completion_status": "too-few-points",
            "completion_used": False,
        }

    extent = _cloud_extent(point_cloud)
    center, basis = _principal_axis_basis(points)
    axis = basis[:, 0]
    max_seed_points = int(params.get("local_completion_seed_points", 65000))
    max_seed_points = max(4000, min(max_seed_points, len(points)))

    if len(points) > max_seed_points:
        seed_indices = np.linspace(0, len(points) - 1, max_seed_points, dtype=int)
    else:
        seed_indices = np.arange(len(points))

    seed_points = points[seed_indices]
    seed_colors = None
    seed_normals = None
    if point_cloud.has_colors() and len(point_cloud.colors) == len(point_cloud.points):
        seed_colors = np.asarray(point_cloud.colors)[seed_indices]
    if point_cloud.has_normals() and len(point_cloud.normals) == len(point_cloud.points):
        seed_normals = np.asarray(point_cloud.normals)[seed_indices]

    angle_count = int(params.get("rotational_completion_steps", 8))
    angle_count = max(4, min(angle_count, 12))
    angles = [2.0 * np.pi * step / angle_count for step in range(1, angle_count)]
    rotated_points = []
    rotated_colors = []
    rotated_normals = []

    for angle in angles:
        rotation = _rotation_about_axis(axis, angle)
        rotated_points.append((seed_points - center) @ rotation.T + center)
        if seed_colors is not None:
            rotated_colors.append(seed_colors)
        if seed_normals is not None:
            rotated_normals.append(seed_normals @ rotation.T)

    if not rotated_points:
        return None, {
            "completion_model": "local_rotational_symmetry",
            "completion_status": "no-candidates",
            "completion_used": False,
        }

    candidate_points = np.concatenate(rotated_points, axis=0)
    candidate_cloud = o3d.geometry.PointCloud()
    candidate_cloud.points = o3d.utility.Vector3dVector(candidate_points)
    distances = np.asarray(candidate_cloud.compute_point_cloud_distance(point_cloud))

    sparse_radius = float(params.get("local_completion_radius", 0.0) or 0.0)
    if sparse_radius <= 0:
        sparse_radius = max(extent / 240.0, 0.006)

    max_gap = float(params.get("local_completion_max_gap", 0.0) or 0.0)
    if max_gap <= 0:
        max_gap = max(extent / 7.0, sparse_radius * 8.0)

    keep_mask = (distances >= sparse_radius) & (distances <= max_gap)
    kept_points = candidate_points[keep_mask]
    if len(kept_points) == 0:
        return None, {
            "completion_model": "local_rotational_symmetry",
            "completion_status": "no-sparse-regions",
            "completion_used": False,
            "completion_radius": round(sparse_radius, 6),
        }

    max_ratio = 1.1 if profile == "hq" else 0.9 if profile == "balanced" else 0.72
    max_points = max(1, int(len(points) * max_ratio))
    kept_indices = np.flatnonzero(keep_mask)
    if len(kept_points) > max_points:
        selection = np.linspace(0, len(kept_points) - 1, max_points, dtype=int)
        kept_points = kept_points[selection]
        kept_indices = kept_indices[selection]

    completed_cloud = o3d.geometry.PointCloud()
    completed_cloud.points = o3d.utility.Vector3dVector(kept_points)

    if rotated_colors:
        candidate_colors = np.concatenate(rotated_colors, axis=0)
        completed_cloud.colors = o3d.utility.Vector3dVector(candidate_colors[kept_indices])

    if rotated_normals:
        candidate_normals = np.concatenate(rotated_normals, axis=0)
        completed_cloud.normals = o3d.utility.Vector3dVector(candidate_normals[kept_indices])

    completed_cloud = completed_cloud.voxel_down_sample(max(sparse_radius * 0.45, extent / 1400.0))

    return completed_cloud, {
        "completion_model": "local_rotational_symmetry",
        "completion_status": "local-rotational-geometric-fallback",
        "completion_axis": [round(float(value), 5) for value in axis],
        "completion_radius": round(sparse_radius, 6),
        "completion_max_gap": round(max_gap, 6),
        "completion_seed_points": int(len(seed_points)),
        "completion_candidate_points": int(len(candidate_points)),
        "completion_used": len(completed_cloud.points) > 0,
    }


def _make_local_completion(point_cloud, profile: str, params: Dict[str, Any]):
    if not params.get("force_completion"):
        return None, {
            "completion_model": "conservative_surface",
            "completion_status": "skipped-local-hallucination-guard",
            "completion_used": False,
        }

    flatness = _shape_flatness(point_cloud)
    if flatness < 0.22 and not params.get("force_completion"):
        return None, {
            "completion_model": "conservative_surface",
            "completion_status": "skipped-flat-architectural-scan",
            "completion_flatness": round(flatness, 6),
            "completion_used": False,
        }

    surface_cloud, surface_metadata = _build_cylindrical_surface_completion(point_cloud, profile, params)
    rotational_cloud, rotational_metadata = _build_rotational_candidates(point_cloud, profile, params)
    completion_clouds = [
        cloud for cloud in (surface_cloud, rotational_cloud)
        if cloud is not None and len(cloud.points) > 0
    ]

    if completion_clouds:
        combined_cloud = o3d.geometry.PointCloud()
        combined_points = [np.asarray(cloud.points) for cloud in completion_clouds]
        combined_cloud.points = o3d.utility.Vector3dVector(np.concatenate(combined_points, axis=0))
        combined_cloud = combined_cloud.voxel_down_sample(max(_cloud_extent(point_cloud) / 1600.0, 0.006))
        return combined_cloud, {
            "completion_model": "local_hybrid_surface",
            "completion_status": "local-cylindrical-and-rotational-fallback",
            "surface_completion": surface_metadata,
            "rotational_completion": rotational_metadata,
            "completion_used": len(combined_cloud.points) > 0,
        }

    points = np.asarray(point_cloud.points)
    if len(points) < 32:
        return None, {
            "completion_model": "local_symmetry",
            "completion_status": "too-few-points",
            "completion_used": False,
        }

    axis_name = str(params.get("symmetry_axis", "x")).lower()
    axis_index = {"x": 0, "y": 1, "z": 2}.get(axis_name, 0)
    center = np.median(points, axis=0)
    mirrored_points = points.copy()
    mirrored_points[:, axis_index] = (2.0 * center[axis_index]) - mirrored_points[:, axis_index]

    extent = _cloud_extent(point_cloud)
    neighbor_radius = float(params.get("local_completion_radius", 0.0) or 0.0)
    if neighbor_radius <= 0:
        neighbor_radius = max(extent / 320.0, 0.0035)

    tree = o3d.geometry.KDTreeFlann(point_cloud)
    keep_mask = np.zeros(len(mirrored_points), dtype=bool)
    for index, point in enumerate(mirrored_points):
        neighbor_count, _, _ = tree.search_radius_vector_3d(point, neighbor_radius)
        keep_mask[index] = neighbor_count <= 2

    candidate_points = mirrored_points[keep_mask]
    if len(candidate_points) == 0:
        return None, {
            "completion_model": "local_symmetry",
            "completion_status": "no-sparse-regions",
            "completion_used": False,
        }

    max_ratio = 0.75 if profile == "hq" else 0.58 if profile == "balanced" else 0.42
    max_points = max(1, int(len(points) * max_ratio))
    if len(candidate_points) > max_points:
        selection = np.linspace(0, len(candidate_points) - 1, max_points, dtype=int)
        candidate_points = candidate_points[selection]
        kept_indices = np.flatnonzero(keep_mask)[selection]
    else:
        kept_indices = np.flatnonzero(keep_mask)

    completed_cloud = o3d.geometry.PointCloud()
    completed_cloud.points = o3d.utility.Vector3dVector(candidate_points)

    if point_cloud.has_colors() and len(point_cloud.colors) == len(point_cloud.points):
        completed_cloud.colors = o3d.utility.Vector3dVector(np.asarray(point_cloud.colors)[kept_indices])

    if point_cloud.has_normals() and len(point_cloud.normals) == len(point_cloud.points):
        mirrored_normals = np.asarray(point_cloud.normals)[kept_indices].copy()
        mirrored_normals[:, axis_index] *= -1.0
        completed_cloud.normals = o3d.utility.Vector3dVector(mirrored_normals)

    completed_cloud = completed_cloud.voxel_down_sample(max(neighbor_radius * 0.55, extent / 1000.0))

    return completed_cloud, {
        "completion_model": "local_symmetry",
        "completion_status": "local-geometric-fallback",
        "completion_axis": axis_name if axis_name in {"x", "y", "z"} else "x",
        "completion_radius": round(neighbor_radius, 6),
        "completion_used": len(completed_cloud.points) > 0,
    }


def _merge_completion(point_cloud, generated_cloud, profile: str, params: Dict[str, Any], metadata: Dict[str, Any]):
    if generated_cloud is None or len(generated_cloud.points) == 0:
        metadata.update(
            {
                "completion_used": False,
                "generated_points": 0,
                "merged_points": len(point_cloud.points),
            }
        )
        return _copy_cloud(point_cloud), metadata

    extent = _cloud_extent(point_cloud)
    merge_radius = float(params.get("merge_radius", 0.0) or 0.0)
    if merge_radius <= 0:
        merge_radius = max(extent / 360.0, 0.0035)

    if metadata.get("completion_model") == "local_hybrid_surface":
        max_added_ratio = 0.22 if profile == "hq" else 0.16 if profile == "balanced" else 0.1
    elif metadata.get("completion_model") == "local_cylindrical_surface":
        max_added_ratio = 0.18 if profile == "hq" else 0.12 if profile == "balanced" else 0.08
    elif metadata.get("completion_model") == "local_rotational_symmetry":
        max_added_ratio = 0.2 if profile == "hq" else 0.14 if profile == "balanced" else 0.09
    else:
        max_added_ratio = 0.16 if profile == "hq" else 0.1 if profile == "balanced" else 0.06

    max_added_ratio = float(params.get("max_added_ratio", max_added_ratio))
    max_added_ratio = max(0.0, min(max_added_ratio, 0.3))

    merged_cloud, generated_points = merge_observed_and_completed(
        point_cloud,
        generated_cloud,
        neighbor_radius=merge_radius,
        max_added_ratio=max_added_ratio,
    )
    metadata.update(
        {
            "generated_points": generated_points,
            "merged_points": len(merged_cloud.points),
            "completion_used": generated_points > 0,
            "merge_radius": round(merge_radius, 6),
        }
    )
    return merged_cloud, metadata


def complete_point_cloud(point_cloud, reconstruction_mode: str, profile: str, params: Dict[str, Any]):
    if o3d is None:
        raise RuntimeError("Open3D is required for completion runtime.")

    if reconstruction_mode != "dl_completion":
        return _copy_cloud(point_cloud), {
            "completion_mode": "geometry_only",
            "completion_used": False,
            "completion_status": "skipped",
            "generated_points": 0,
        }

    # Select model based on parameter or environment
    model_name = params.get("completion_model")
    adapter, selected_model = _select_completion_model(model_name)
    
    import sys
    print(f"[completion] Selected model: {selected_model}, adapter: {adapter}", file=sys.stderr, flush=True)
    print(f"[completion] Profile: {profile}, force_completion: {params.get('force_completion')}", file=sys.stderr, flush=True)
    
    if adapter is None:
        print(f"[completion] No DL model available, using local geometric fallback", file=sys.stderr, flush=True)
        generated_cloud, metadata = _make_local_completion(point_cloud, profile, params)
        metadata.update({
            "completion_mode": "dl_completion",
            "external_completion_status": "no-models-available",
        })
        return _merge_completion(point_cloud, generated_cloud, profile, params, metadata)

    try:
        print(f"[completion] Attempting inference with {selected_model}...", file=sys.stderr, flush=True)
        result = adapter.infer(point_cloud, profile, params)
        print(f"[completion] {selected_model} inference succeeded, {len(result.point_cloud.points)} output points", file=sys.stderr, flush=True)
    except Exception as exc:
        print(f"[completion] {selected_model} inference failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        generated_cloud, metadata = _make_local_completion(point_cloud, profile, params)
        metadata.update({
            "completion_mode": "dl_completion",
            "completion_model": selected_model,
            "completion_status": "local-geometric-fallback",
            "external_completion_status": f"failed:{type(exc).__name__}",
            "completion_error": str(exc),
        })
        return _merge_completion(point_cloud, generated_cloud, profile, params, metadata)

    generated_cloud = result.point_cloud
    metadata = dict(result.metadata)
    metadata["completion_mode"] = "dl_completion"

    return _merge_completion(point_cloud, generated_cloud, profile, params, metadata)
