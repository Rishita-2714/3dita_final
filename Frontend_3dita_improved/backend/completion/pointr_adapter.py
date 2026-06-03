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

        input_cloud = self._prepare_model_input(point_cloud)
        completed_cloud = self._run_local_pointr_inference(input_cloud)
        return CompletionResult(
            point_cloud=completed_cloud,
            metadata={
                "completion_model": "pointr",
                "completion_used": True,
                "completion_status": "local-inference",
                "completion_device": self._device,
                "completion_input_points": len(input_cloud.points),
                "completion_output_points": len(completed_cloud.points),
            },
        )

    def _prepare_model_input(self, point_cloud):
        points = np.asarray(point_cloud.points)
        if len(points) <= self._input_points:
            return point_cloud

        sample_indices = np.linspace(0, len(points) - 1, self._input_points, dtype=int)
        sampled_cloud = o3d.geometry.PointCloud()
        sampled_cloud.points = o3d.utility.Vector3dVector(points[sample_indices])

        if point_cloud.has_colors() and len(point_cloud.colors) == len(point_cloud.points):
            sampled_cloud.colors = o3d.utility.Vector3dVector(np.asarray(point_cloud.colors)[sample_indices])

        if point_cloud.has_normals() and len(point_cloud.normals) == len(point_cloud.points):
            sampled_cloud.normals = o3d.utility.Vector3dVector(np.asarray(point_cloud.normals)[sample_indices])

        return sampled_cloud

    def _run_local_pointr_inference(self, point_cloud):
        points = np.asarray(point_cloud.points)
        if len(points) == 0:
            return point_cloud

        with tempfile.TemporaryDirectory(prefix="pointr_infer_") as temp_dir:
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
            ]

            subprocess.run(
                command,
                cwd=str(self._repo_path),
                check=True,
                capture_output=True,
                text=True,
            )

            result_file = output_root / input_path.stem / "fine.npy"
            if not result_file.exists():
                raise RuntimeError("PoinTr inference did not produce fine.npy output.")

            completed_points = np.load(result_file).astype(np.float64)
            completed_cloud = o3d.geometry.PointCloud()
            completed_cloud.points = o3d.utility.Vector3dVector(completed_points)
            return completed_cloud
