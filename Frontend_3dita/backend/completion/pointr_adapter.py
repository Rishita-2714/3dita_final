from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - runtime dependency
    o3d = None


@dataclass
class CompletionResult:
    point_cloud: Optional[object]
    metadata: Dict[str, Any]


class PoinTrAdapter:
    """Adapter around an optional external PoinTr runtime.

    The stable reconstruction backend should not need to import the research
    stack directly. Instead, this adapter can invoke a separately prepared
    PoinTr environment through a configurable Python executable.
    """

    def __init__(self) -> None:
        self._availability_reason = ""
        default_repo_path = Path(__file__).resolve().parents[3] / "external" / "PoinTr"
        default_config_path = default_repo_path / "cfgs" / "PCN_models" / "PoinTr.yaml"
        default_checkpoint_path = default_repo_path / "pretrained" / "PoinTr_PCN.pth"

        self._device = os.environ.get("POINTR_DEVICE", "cpu")
        self._input_points = int(os.environ.get("POINTR_INPUT_POINTS", "2048"))
        self._python_bin = os.environ.get("POINTR_PYTHON_BIN", "").strip() or sys.executable
        self._repo_path = Path(os.environ.get("POINTR_REPO_PATH", "").strip()) if os.environ.get("POINTR_REPO_PATH", "").strip() else default_repo_path
        self._config_path = Path(os.environ.get("POINTR_CONFIG_PATH", "").strip()) if os.environ.get("POINTR_CONFIG_PATH", "").strip() else default_config_path
        self._checkpoint_path = Path(os.environ.get("POINTR_CHECKPOINT_PATH", "").strip()) if os.environ.get("POINTR_CHECKPOINT_PATH", "").strip() else default_checkpoint_path
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
            raise RuntimeError("Open3D is required for PoinTr integration.")

        if not self.is_available():
            return CompletionResult(
                point_cloud=None,
                metadata={
                    "completion_model": "pointr",
                    "completion_used": False,
                    "completion_status": self.availability_reason(),
                },
            )

        input_cloud, prep_metadata = self._prepare_model_input(point_cloud, params)
        completed_cloud, output_metadata = self._run_local_pointr_inference(input_cloud, params)
        return CompletionResult(
            point_cloud=completed_cloud,
            metadata={
                "completion_model": "pointr",
                "completion_used": True,
                "completion_status": "local-inference",
                "completion_device": self._device,
                "completion_input_points": len(input_cloud.points),
                "completion_output_points": len(completed_cloud.points),
                **prep_metadata,
                **output_metadata,
            },
        )

    def _normalize_points(self, points: np.ndarray):
        center = np.mean(points, axis=0)
        centered = points - center
        scale = float(np.max(np.linalg.norm(centered, axis=1)))
        scale = max(scale, 1e-6)
        return centered / scale, center, scale

    def _prepare_model_input(self, point_cloud, params: Dict[str, Any]):
        points = np.asarray(point_cloud.points)
        if len(points) == 0:
            return point_cloud, {
                "pointr_normalized": False,
                "pointr_input_points_before_sample": 0,
            }

        if len(points) > self._input_points:
            sample_indices = np.linspace(0, len(points) - 1, self._input_points, dtype=int)
        else:
            sample_indices = np.arange(len(points))

        sampled_points = points[sample_indices]
        normalized_points, center, scale = self._normalize_points(sampled_points)
        sampled_cloud = o3d.geometry.PointCloud()
        sampled_cloud.points = o3d.utility.Vector3dVector(normalized_points)

        if point_cloud.has_colors() and len(point_cloud.colors) == len(point_cloud.points):
            sampled_cloud.colors = o3d.utility.Vector3dVector(np.asarray(point_cloud.colors)[sample_indices])

        if point_cloud.has_normals() and len(point_cloud.normals) == len(point_cloud.points):
            sampled_cloud.normals = o3d.utility.Vector3dVector(np.asarray(point_cloud.normals)[sample_indices])

        bbox = point_cloud.get_axis_aligned_bounding_box()
        self._last_center = center
        self._last_scale = scale
        self._last_bbox_min = np.asarray(bbox.min_bound, dtype=np.float64)
        self._last_bbox_max = np.asarray(bbox.max_bound, dtype=np.float64)

        return sampled_cloud, {
            "pointr_normalized": True,
            "pointr_input_points_before_sample": int(len(points)),
            "pointr_normalization_center": [round(float(value), 6) for value in center],
            "pointr_normalization_scale": round(float(scale), 6),
        }

    def _denormalize_and_filter_output(self, completed_points: np.ndarray, params: Dict[str, Any]):
        center = getattr(self, "_last_center", np.zeros(3, dtype=np.float64))
        scale = float(getattr(self, "_last_scale", 1.0))
        bbox_min = np.asarray(getattr(self, "_last_bbox_min", center - scale), dtype=np.float64)
        bbox_max = np.asarray(getattr(self, "_last_bbox_max", center + scale), dtype=np.float64)

        points = (completed_points * scale) + center
        extent = np.maximum(bbox_max - bbox_min, 1e-6)
        padding = max(0.0, min(float(params.get("pointr_output_padding", 0.04)), 0.18))
        padded_min = bbox_min - extent * padding
        padded_max = bbox_max + extent * padding
        inside = np.all((points >= padded_min) & (points <= padded_max), axis=1)
        points = points[inside]

        completed_cloud = o3d.geometry.PointCloud()
        completed_cloud.points = o3d.utility.Vector3dVector(points.astype(np.float64))
        before_sor = len(completed_cloud.points)
        if before_sor >= 32:
            completed_cloud, _ = completed_cloud.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

        return completed_cloud, {
            "pointr_output_points_before_filter": int(len(completed_points)),
            "pointr_output_points_inside_bbox": int(before_sor),
            "pointr_output_points_after_sor": int(len(completed_cloud.points)),
        }

    def _run_local_pointr_inference(self, point_cloud, params: Dict[str, Any]):
        import sys
        points = np.asarray(point_cloud.points)
        if len(points) == 0:
            return point_cloud, {
                "pointr_output_points_before_filter": 0,
                "pointr_output_points_after_sor": 0,
            }

        with tempfile.TemporaryDirectory(prefix="pointr_infer_") as temp_dir:
            temp_root = Path(temp_dir)
            input_path = temp_root / "input.npy"
            output_root = temp_root / "output"
            output_root.mkdir(parents=True, exist_ok=True)
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
            ]

            print(f"[PoinTr] Running command: {' '.join(command)}", file=sys.stderr, flush=True)
            print(f"[PoinTr] CWD: {self._repo_path}", file=sys.stderr, flush=True)
            print(f"[PoinTr] Input points: {len(points)}", file=sys.stderr, flush=True)
            print(f"[PoinTr] Temp dir: {temp_root}", file=sys.stderr, flush=True)
            print(f"[PoinTr] Output root: {output_root}", file=sys.stderr, flush=True)

            result = subprocess.run(
                command,
                cwd=str(self._repo_path),
                check=False,
                capture_output=True,
                text=True,
            )

            print(f"[PoinTr] Return code: {result.returncode}", file=sys.stderr, flush=True)
            print(f"[PoinTr] STDOUT:\n{result.stdout}", file=sys.stderr, flush=True)
            print(f"[PoinTr] STDERR:\n{result.stderr}", file=sys.stderr, flush=True)

            if result.returncode != 0:
                raise RuntimeError(
                    "PoinTr inference failed with code "
                    + str(result.returncode)
                    + ": "
                    + (result.stderr or result.stdout or "unknown error")
                )

            # List output directory to debug
            try:
                output_contents = list(output_root.rglob("*"))
                print(f"[PoinTr] Output dir contents: {output_contents}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[PoinTr] Could not list output: {e}", file=sys.stderr, flush=True)

            result_file = output_root / input_path.stem / "fine.npy"
            alternate_result_file = input_path.with_suffix("") / "fine.npy"
            if not result_file.exists() and alternate_result_file.exists():
                result_file = alternate_result_file

            if not result_file.exists():
                raise RuntimeError(
                    "PoinTr inference did not produce fine.npy output at "
                    + str(result_file)
                    + f". stdout={result.stdout!r} stderr={result.stderr!r}"
                )

            completed_points = np.load(result_file).astype(np.float64)
            return self._denormalize_and_filter_output(completed_points, params)
