from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - runtime dependency
    o3d = None


@dataclass
class CompletionResult:
    point_cloud: Optional[object]
    metadata: Dict[str, Any]


class GRNetAdapter:
    """Adapter for GRNet (Gated Recurrent Unit Network) point cloud completion.
    
    GRNet provides superior point cloud completion through:
    - Gated recurrent units for feature learning
    - Coarse-to-fine hierarchical generation
    - Better shape preservation and detail
    
    Configuration via environment variables:
    - GRNET_DEVICE: GPU device (default: cuda:0)
    - GRNET_INPUT_POINTS: Input point count (default: 2048)
    - GRNET_PYTHON_BIN: Python executable path (default: system Python)
    - GRNET_REPO_PATH: Path to GRNet repository
    - GRNET_CONFIG_PATH: Path to config YAML
    - GRNET_CHECKPOINT_PATH: Path to checkpoint file
    """

    def __init__(self) -> None:
        self._availability_reason = ""
        self._device = os.environ.get("GRNET_DEVICE", "cuda:0")
        self._input_points = int(os.environ.get("GRNET_INPUT_POINTS", "2048"))
        self._python_bin = os.environ.get("GRNET_PYTHON_BIN", "").strip() or sys.executable
        self._repo_path = Path(os.environ.get("GRNET_REPO_PATH", "").strip()) if os.environ.get("GRNET_REPO_PATH", "").strip() else None
        self._config_path = Path(os.environ.get("GRNET_CONFIG_PATH", "").strip()) if os.environ.get("GRNET_CONFIG_PATH", "").strip() else None
        self._checkpoint_path = Path(os.environ.get("GRNET_CHECKPOINT_PATH", "").strip()) if os.environ.get("GRNET_CHECKPOINT_PATH", "").strip() else None
        self._validated = False
        self._inference_script: Optional[Path] = None

    def is_available(self) -> bool:
        if self._validated:
            return self._availability_reason == ""

        python_path = Path(self._python_bin)
        if not python_path.exists():
            self._availability_reason = "python-bin-missing"
            self._validated = True
            return False

        if self._repo_path is None:
            self._availability_reason = "repo-not-configured"
            self._validated = True
            return False

        if not self._repo_path.exists():
            self._availability_reason = "repo-missing"
            self._validated = True
            return False

        self._inference_script = self._repo_path / "tools" / "inference.py"
        if not self._inference_script.exists():
            self._availability_reason = "inference-script-missing"
            self._validated = True
            return False

        if self._config_path is None:
            self._availability_reason = "config-not-configured"
            self._validated = True
            return False

        if not self._config_path.exists():
            self._availability_reason = "config-missing"
            self._validated = True
            return False

        if self._checkpoint_path is None:
            self._availability_reason = "checkpoint-not-configured"
            self._validated = True
            return False

        if not self._checkpoint_path.exists():
            self._availability_reason = "checkpoint-missing"
            self._validated = True
            return False

        self._availability_reason = ""
        self._validated = True
        return True

    def availability_reason(self) -> str:
        return self._availability_reason or "available"

    def infer(self, point_cloud, profile: str, params: Dict[str, Any]) -> CompletionResult:
        if o3d is None:
            raise RuntimeError("Open3D is required for GRNet integration.")

        if not self.is_available():
            return CompletionResult(
                point_cloud=None,
                metadata={
                    "completion_model": "grnet",
                    "completion_used": False,
                    "completion_status": self.availability_reason(),
                },
            )

        input_cloud, metadata = self._prepare_model_input(point_cloud, params)
        completed_cloud, post_metadata = self._run_local_grnet_inference(input_cloud, profile, params)
        metadata.update(post_metadata)
        return CompletionResult(
            point_cloud=completed_cloud,
            metadata={
                "completion_model": "grnet",
                "completion_used": True,
                "completion_status": "local-inference",
                "completion_device": self._device,
                "completion_input_points": len(input_cloud.points),
                "completion_output_points": len(completed_cloud.points),
                **metadata,
            },
        )

    def _copy_cloud_from_points(self, points: np.ndarray):
        cloud = o3d.geometry.PointCloud()
        cloud.points = o3d.utility.Vector3dVector(points)
        return cloud

    def _parse_bbox(self, params: Dict[str, Any]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        raw_bbox = (
            params.get("grnet_repair_bbox")
            or params.get("repair_bbox")
            or params.get("completion_bbox")
            or params.get("mask_bbox")
        )
        if raw_bbox is None:
            return None

        if isinstance(raw_bbox, str):
            raw_bbox = [part.strip() for part in raw_bbox.replace(";", ",").split(",") if part.strip()]

        try:
            values = np.asarray([float(value) for value in raw_bbox], dtype=np.float64)
        except (TypeError, ValueError):
            return None

        if values.size != 6:
            return None

        bbox_min = np.minimum(values[:3], values[3:])
        bbox_max = np.maximum(values[:3], values[3:])
        if np.any((bbox_max - bbox_min) <= 1e-9):
            return None
        return bbox_min, bbox_max

    def _infer_repair_bbox(self, points: np.ndarray, params: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, str]:
        explicit_bbox = self._parse_bbox(params)
        if explicit_bbox is not None:
            return explicit_bbox[0], explicit_bbox[1], "explicit"

        bounds_min = points.min(axis=0)
        bounds_max = points.max(axis=0)
        extent = np.maximum(bounds_max - bounds_min, 1e-6)
        center = np.median(points, axis=0)
        normalized = (points - bounds_min) / extent

        # Pick the sparsest half-space as the likely damaged side, then expand it
        # enough to include nearby structural context for local completion.
        best_axis = 0
        best_side = 1
        best_count = len(points)
        for axis in range(3):
            lower_count = int(np.sum(normalized[:, axis] < 0.5))
            upper_count = int(np.sum(normalized[:, axis] >= 0.5))
            if lower_count < best_count:
                best_axis = axis
                best_side = -1
                best_count = lower_count
            if upper_count < best_count:
                best_axis = axis
                best_side = 1
                best_count = upper_count

        repair_min = bounds_min.copy()
        repair_max = bounds_max.copy()
        if best_side < 0:
            repair_max[best_axis] = bounds_min[best_axis] + extent[best_axis] * 0.62
        else:
            repair_min[best_axis] = bounds_min[best_axis] + extent[best_axis] * 0.38

        padding = float(params.get("grnet_mask_padding", 0.08))
        padding = max(0.0, min(padding, 0.25))
        repair_min = np.maximum(bounds_min, repair_min - extent * padding)
        repair_max = np.minimum(bounds_max, repair_max + extent * padding)
        _ = center
        return repair_min, repair_max, "auto-sparse-halfspace"

    def _crop_to_bbox(self, point_cloud, bbox_min: np.ndarray, bbox_max: np.ndarray):
        bbox = o3d.geometry.AxisAlignedBoundingBox(
            min_bound=bbox_min.astype(np.float64),
            max_bound=bbox_max.astype(np.float64),
        )
        cropped = point_cloud.crop(bbox)
        if len(cropped.points) < 64:
            return point_cloud
        return cropped

    def _normalize_points(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        center = np.mean(points, axis=0)
        centered = points - center
        scale = float(np.max(np.linalg.norm(centered, axis=1)))
        scale = max(scale, 1e-6)
        return centered / scale, center, scale

    def _apply_partial_ratio(self, point_cloud, params: Dict[str, Any]):
        points = np.asarray(point_cloud.points)
        if len(points) == 0:
            return point_cloud, 0.0

        partial_ratio = float(params.get("grnet_partial_ratio", 0.5))
        partial_ratio = max(0.35, min(partial_ratio, 0.65))
        target_points = max(128, int(self._input_points * partial_ratio))
        target_points = min(target_points, len(points))
        if len(points) <= target_points:
            return point_cloud, round(target_points / max(len(points), 1), 4)

        sample_indices = np.linspace(0, len(points) - 1, target_points, dtype=int)
        sampled_cloud = o3d.geometry.PointCloud()
        sampled_cloud.points = o3d.utility.Vector3dVector(points[sample_indices])

        if point_cloud.has_colors() and len(point_cloud.colors) == len(point_cloud.points):
            sampled_cloud.colors = o3d.utility.Vector3dVector(np.asarray(point_cloud.colors)[sample_indices])

        if point_cloud.has_normals() and len(point_cloud.normals) == len(point_cloud.points):
            sampled_cloud.normals = o3d.utility.Vector3dVector(np.asarray(point_cloud.normals)[sample_indices])

        return sampled_cloud, round(target_points / max(len(points), 1), 4)

    def _prepare_model_input(self, point_cloud, params: Dict[str, Any]):
        points = np.asarray(point_cloud.points)
        if len(points) == 0:
            return point_cloud, {
                "grnet_mask_mode": "empty-input",
                "grnet_normalized": False,
                "grnet_partial_ratio": 0.0,
            }

        bbox_min, bbox_max, mask_mode = self._infer_repair_bbox(points, params)
        local_cloud = self._crop_to_bbox(point_cloud, bbox_min, bbox_max)
        partial_cloud, actual_partial_ratio = self._apply_partial_ratio(local_cloud, params)

        local_points = np.asarray(partial_cloud.points)
        normalized_points, center, scale = self._normalize_points(local_points)
        normalized_cloud = self._copy_cloud_from_points(normalized_points)

        # Store transform on the instance for the paired inference call. The
        # adapter is process-local and requests run in the backend worker thread.
        self._last_center = center
        self._last_scale = scale
        self._last_bbox_min = bbox_min
        self._last_bbox_max = bbox_max

        return normalized_cloud, {
            "grnet_mask_mode": mask_mode,
            "grnet_mask_bbox_min": [round(float(value), 6) for value in bbox_min],
            "grnet_mask_bbox_max": [round(float(value), 6) for value in bbox_max],
            "grnet_normalized": True,
            "grnet_normalization_center": [round(float(value), 6) for value in center],
            "grnet_normalization_scale": round(float(scale), 6),
            "grnet_partial_ratio": actual_partial_ratio,
        }

    def _denormalize_and_filter_output(self, completed_points: np.ndarray, params: Dict[str, Any]):
        center = getattr(self, "_last_center", np.zeros(3, dtype=np.float64))
        scale = float(getattr(self, "_last_scale", 1.0))
        bbox_min = getattr(self, "_last_bbox_min", None)
        bbox_max = getattr(self, "_last_bbox_max", None)

        points = (completed_points * scale) + center

        if bbox_min is not None and bbox_max is not None:
            bbox_min = np.asarray(bbox_min, dtype=np.float64)
            bbox_max = np.asarray(bbox_max, dtype=np.float64)
            padding = float(params.get("grnet_output_padding", 0.03))
            extent = np.maximum(bbox_max - bbox_min, 1e-6)
            padded_min = bbox_min - extent * max(0.0, min(padding, 0.2))
            padded_max = bbox_max + extent * max(0.0, min(padding, 0.2))
            inside = np.all((points >= padded_min) & (points <= padded_max), axis=1)
            points = points[inside]

        cloud = self._copy_cloud_from_points(points.astype(np.float64))
        before_sor = len(cloud.points)
        if before_sor >= 32:
            cloud, _ = cloud.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

        return cloud, {
            "grnet_output_points_before_sor": int(before_sor),
            "grnet_sor_nb_neighbors": 20,
            "grnet_sor_std_ratio": 2.0,
            "grnet_output_points_after_sor": int(len(cloud.points)),
        }

    def _run_local_grnet_inference(self, point_cloud, profile: str, params: Dict[str, Any]):
        points = np.asarray(point_cloud.points)
        if len(points) == 0:
            return point_cloud, {"grnet_output_points_before_sor": 0, "grnet_output_points_after_sor": 0}

        with tempfile.TemporaryDirectory(prefix="grnet_infer_") as temp_dir:
            temp_root = Path(temp_dir)
            input_path = temp_root / "input.npy"
            output_root = temp_root / "output"
            np.save(input_path, points.astype(np.float32))

            command = [
                self._python_bin,
                str(self._inference_script),
                str(self._config_path),
                str(self._checkpoint_path),
                "--pc",
                str(input_path),
                "--out_pc_root",
                str(output_root),
                "--device",
                self._device,
                "--profile",
                profile,
            ]

            subprocess.run(
                command,
                cwd=str(self._repo_path),
                check=True,
                capture_output=True,
                text=True,
            )

            # GRNet produces fine.npy in the output directory
            result_file = output_root / input_path.stem / "fine.npy"
            if not result_file.exists():
                raise RuntimeError("GRNet inference did not produce fine.npy output.")

            completed_points = np.load(result_file).astype(np.float64)
            return self._denormalize_and_filter_output(completed_points, params)
