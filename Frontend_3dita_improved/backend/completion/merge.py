from __future__ import annotations

from typing import Tuple

import numpy as np

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - runtime dependency
    o3d = None


def _copy_cloud(point_cloud):
    copied = o3d.geometry.PointCloud()
    copied.points = o3d.utility.Vector3dVector(np.asarray(point_cloud.points).copy())

    if point_cloud.has_colors() and len(point_cloud.colors) == len(point_cloud.points):
        copied.colors = o3d.utility.Vector3dVector(np.asarray(point_cloud.colors).copy())

    if point_cloud.has_normals() and len(point_cloud.normals) == len(point_cloud.points):
        copied.normals = o3d.utility.Vector3dVector(np.asarray(point_cloud.normals).copy())

    return copied


def merge_observed_and_completed(
    observed_cloud,
    completed_cloud,
    neighbor_radius: float,
    max_added_ratio: float = 0.55,
) -> Tuple[object, int]:
    """Keep observed geometry authoritative and add only sparse-region support."""
    if o3d is None:
        raise RuntimeError("Open3D is required for point-cloud merging.")

    observed_points = np.asarray(observed_cloud.points)
    completed_points = np.asarray(completed_cloud.points)
    if len(observed_points) == 0 or len(completed_points) == 0:
        return _copy_cloud(observed_cloud), 0

    merged_cloud = _copy_cloud(observed_cloud)
    kdtree = o3d.geometry.KDTreeFlann(observed_cloud)

    keep_mask = np.zeros(len(completed_points), dtype=bool)
    sparse_radius = max(float(neighbor_radius), 1e-4)

    for index, point in enumerate(completed_points):
        count, _, _ = kdtree.search_radius_vector_3d(point, sparse_radius)
        # Only admit generated points where observed support is weak.
        if count <= 2:
            keep_mask[index] = True

    kept_points = completed_points[keep_mask]
    if len(kept_points) == 0:
        return merged_cloud, 0

    max_added_points = int(len(observed_points) * max_added_ratio)
    if len(kept_points) > max_added_points > 0:
        selection = np.linspace(0, len(kept_points) - 1, max_added_points, dtype=int)
        kept_points = kept_points[selection]
        kept_indices = np.flatnonzero(keep_mask)[selection]
    else:
        kept_indices = np.flatnonzero(keep_mask)

    merged_points = np.concatenate([observed_points, kept_points], axis=0)
    merged_cloud.points = o3d.utility.Vector3dVector(merged_points)

    if observed_cloud.has_colors() and len(observed_cloud.colors) == len(observed_cloud.points):
        observed_colors = np.asarray(observed_cloud.colors)
        if completed_cloud.has_colors() and len(completed_cloud.colors) == len(completed_cloud.points):
            completed_colors = np.asarray(completed_cloud.colors)[kept_indices]
        else:
            completed_colors = np.zeros((len(kept_points), 3))
            observed_color_tree = o3d.geometry.KDTreeFlann(observed_cloud)
            for color_index, point in enumerate(kept_points):
                _, nn_indices, _ = observed_color_tree.search_knn_vector_3d(point, 1)
                completed_colors[color_index] = observed_colors[nn_indices[0]]

        merged_cloud.colors = o3d.utility.Vector3dVector(
            np.concatenate([observed_colors, completed_colors], axis=0)
        )

    if observed_cloud.has_normals() and len(observed_cloud.normals) == len(observed_cloud.points):
        observed_normals = np.asarray(observed_cloud.normals)
        if completed_cloud.has_normals() and len(completed_cloud.normals) == len(completed_cloud.points):
            completed_normals = np.asarray(completed_cloud.normals)[kept_indices]
        else:
            completed_normals = np.zeros((len(kept_points), 3))
            observed_normal_tree = o3d.geometry.KDTreeFlann(observed_cloud)
            for normal_index, point in enumerate(kept_points):
                _, nn_indices, _ = observed_normal_tree.search_knn_vector_3d(point, 1)
                completed_normals[normal_index] = observed_normals[nn_indices[0]]

        merged_cloud.normals = o3d.utility.Vector3dVector(
            np.concatenate([observed_normals, completed_normals], axis=0)
        )

    return merged_cloud, len(kept_points)
