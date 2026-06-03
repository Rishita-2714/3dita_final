from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np
from PIL import Image


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class InpaintResult:
    output_path: Path
    metadata: Dict[str, Any]


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def _load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def _load_mask(path: Path, shape: Tuple[int, int]) -> np.ndarray:
    mask_image = Image.open(path).convert("L")
    if mask_image.size != (shape[1], shape[0]):
        mask_image = mask_image.resize((shape[1], shape[0]), Image.Resampling.NEAREST)
    return np.asarray(mask_image, dtype=np.uint8) > 127


def _save_rgb(path: Path, image: np.ndarray) -> None:
    clipped = np.clip(np.rint(image), 0, 255).astype(np.uint8)
    Image.fromarray(clipped, mode="RGB").save(path)


def _shift(mask: np.ndarray, dy: int, dx: int, fill: bool = False) -> np.ndarray:
    h, w = mask.shape
    shifted = np.full_like(mask, fill)

    y_src_start = max(0, -dy)
    y_src_end = min(h, h - dy)
    x_src_start = max(0, -dx)
    x_src_end = min(w, w - dx)

    y_dst_start = max(0, dy)
    y_dst_end = min(h, h + dy)
    x_dst_start = max(0, dx)
    x_dst_end = min(w, w + dx)

    if y_src_start < y_src_end and x_src_start < x_src_end:
        shifted[y_dst_start:y_dst_end, x_dst_start:x_dst_end] = mask[
            y_src_start:y_src_end,
            x_src_start:x_src_end,
        ]
    return shifted


def _dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.copy()
    for _ in range(max(0, iterations)):
        expanded = result.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    expanded |= _shift(result, dy, dx)
        result = expanded
    return result


def _erode(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.copy()
    for _ in range(max(0, iterations)):
        contracted = result.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    contracted &= _shift(result, dy, dx, fill=True)
        result = contracted
    return result


def _boundary_band(mask: np.ndarray, radius: int) -> np.ndarray:
    return _dilate(mask, radius) & ~_erode(mask, radius)


def _mean_known_color(image: np.ndarray, known: np.ndarray) -> np.ndarray:
    if not np.any(known):
        return np.array([127.0, 127.0, 127.0], dtype=np.float32)
    return image[known].mean(axis=0)


def _iter_ring_fill(image: np.ndarray, mask: np.ndarray, passes: int) -> np.ndarray:
    result = image.copy()
    known = ~mask
    result[mask] = _mean_known_color(image, known)

    offsets = [
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (-1, -1, 0.707),
        (-1, 1, 0.707),
        (1, -1, 0.707),
        (1, 1, 0.707),
    ]

    for _ in range(max(1, passes)):
        fillable = mask & _dilate(known, 1)
        if not np.any(fillable):
            break

        weighted_sum = np.zeros_like(result)
        weight_sum = np.zeros(mask.shape, dtype=np.float32)
        for dy, dx, weight in offsets:
            neighbor_known = _shift(known, dy, dx)
            neighbor_values = np.roll(result, shift=(dy, dx), axis=(0, 1))
            valid = fillable & neighbor_known
            weighted_sum[valid] += neighbor_values[valid] * weight
            weight_sum[valid] += weight

        update = fillable & (weight_sum > 0)
        result[update] = weighted_sum[update] / weight_sum[update, None]
        known[update] = True

    return result


def _patch_slices(y: int, x: int, radius: int, height: int, width: int):
    return (
        slice(max(0, y - radius), min(height, y + radius + 1)),
        slice(max(0, x - radius), min(width, x + radius + 1)),
    )


def _candidate_centers(known: np.ndarray, mask: np.ndarray, step: int) -> Iterable[Tuple[int, int]]:
    h, w = known.shape
    source = known & ~_dilate(mask, 2)
    ys, xs = np.where(source)
    if len(xs) == 0:
        ys, xs = np.where(known)
    if len(xs) == 0:
        return []

    stride = max(1, step)
    return zip(ys[::stride], xs[::stride])


def _patch_refine(
    original: np.ndarray,
    initialized: np.ndarray,
    mask: np.ndarray,
    patch_radius: int,
    target_step: int,
    candidate_step: int,
    passes: int,
) -> np.ndarray:
    h, w = mask.shape
    result = initialized.copy()
    known_original = ~mask
    candidates = list(_candidate_centers(known_original, mask, candidate_step))
    if not candidates:
        return result

    target_band = mask
    for pass_index in range(max(1, passes)):
        ys, xs = np.where(target_band)
        if len(xs) == 0:
            break

        order = np.argsort((ys / max(h, 1)) + (pass_index * 0.031))
        for index in order[:: max(1, target_step)]:
            ty = int(ys[index])
            tx = int(xs[index])
            target_y, target_x = _patch_slices(ty, tx, patch_radius, h, w)
            target_patch = result[target_y, target_x]
            compare_mask = known_original[target_y, target_x]
            copy_mask = mask[target_y, target_x]
            if not np.any(copy_mask):
                continue

            best_score = None
            best_patch = None
            for cy, cx in candidates:
                source_y, source_x = _patch_slices(int(cy), int(cx), patch_radius, h, w)
                source_patch = original[source_y, source_x]
                if source_patch.shape != target_patch.shape:
                    continue

                source_known = known_original[source_y, source_x]
                usable = compare_mask & source_known
                if usable.sum() < max(4, compare_mask.size // 9):
                    continue

                color_delta = target_patch[usable] - source_patch[usable]
                score = float(np.mean(color_delta * color_delta))
                row_bias = abs(float(cy - ty)) / max(h, 1)
                score *= 1.0 + row_bias * 0.45
                if best_score is None or score < best_score:
                    best_score = score
                    best_patch = source_patch

            if best_patch is None:
                continue

            current = result[target_y, target_x]
            current[copy_mask] = (current[copy_mask] * 0.38) + (best_patch[copy_mask] * 0.62)
            result[target_y, target_x] = current

        target_band = mask & _dilate(~target_band, 1)
        if not np.any(target_band):
            target_band = mask

    return result


def _resize_work_inputs(image: np.ndarray, mask: np.ndarray, max_side: int) -> Tuple[np.ndarray, np.ndarray, float]:
    h, w = mask.shape
    longest = max(h, w)
    if longest <= max_side:
        return image, mask, 1.0

    scale = max_side / float(longest)
    work_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    work_image = np.asarray(
        Image.fromarray(np.clip(image, 0, 255).astype(np.uint8), mode="RGB").resize(
            work_size,
            Image.Resampling.LANCZOS,
        ),
        dtype=np.float32,
    )
    work_mask = np.asarray(
        Image.fromarray(mask.astype(np.uint8) * 255, mode="L").resize(
            work_size,
            Image.Resampling.NEAREST,
        ),
        dtype=np.uint8,
    ) > 127
    return work_image, work_mask, scale


def _restore_work_result(work_result: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    return np.asarray(
        Image.fromarray(np.clip(work_result, 0, 255).astype(np.uint8), mode="RGB").resize(
            size,
            Image.Resampling.LANCZOS,
        ),
        dtype=np.float32,
    )


def _feather_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    alpha = mask.astype(np.float32)
    for _ in range(max(1, radius)):
        total = alpha.copy()
        count = np.ones_like(alpha)
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            total += np.roll(alpha, shift=(dy, dx), axis=(0, 1))
            count += 1.0
        alpha = total / count
        alpha[mask] = np.maximum(alpha[mask], 0.82)
        alpha[~_dilate(mask, radius)] = 0.0
    return np.clip(alpha, 0.0, 1.0)


def _boundary_consistency(image: np.ndarray, result: np.ndarray, mask: np.ndarray) -> float:
    ring = _boundary_band(mask, 1) & ~mask
    if not np.any(ring):
        return 1.0
    diff = np.mean(np.abs(image[ring] - result[ring])) / 255.0
    return round(float(max(0.0, 1.0 - diff)), 4)


def _local_guided_refinement(image: np.ndarray, mask: np.ndarray, params: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
    h, w = mask.shape
    masked_ratio = float(mask.mean())
    profile = str(params.get("profile", "hq")).lower()
    max_side = int(params.get("work_max_side", 960 if profile == "hq" else 768))
    max_side = max(384, min(max_side, 1600))
    work_image, work_mask, work_scale = _resize_work_inputs(image, mask, max_side)
    wh, ww = work_mask.shape

    patch_radius = int(params.get("patch_radius", 6 if profile == "hq" else 5))
    patch_radius = max(3, min(patch_radius, 14))

    ring_passes = int(params.get("ring_passes", max(wh, ww) // 30))
    ring_passes = max(8, min(ring_passes, 72))
    patch_passes = int(params.get("refinement_passes", 1 if profile == "hq" else 0))
    patch_passes = max(0, min(patch_passes, 2))

    initialized = _iter_ring_fill(work_image, work_mask, passes=ring_passes)
    if patch_passes > 0 and int(work_mask.sum()) < 120_000:
        target_step = 5 if profile == "hq" else 7
        candidate_step = max(1, int(params.get("candidate_step", 31 if profile == "hq" else 43)))
        refined = _patch_refine(
            work_image,
            initialized,
            work_mask,
            patch_radius=patch_radius,
            target_step=target_step,
            candidate_step=candidate_step,
            passes=patch_passes,
        )
    else:
        refined = initialized

    if work_scale < 1.0:
        refined = _restore_work_result(refined, (w, h))

    alpha = _feather_mask(mask, radius=3 if profile == "hq" else 2)
    blended = (refined * alpha[..., None]) + (image * (1.0 - alpha[..., None]))
    blended[~mask] = image[~mask]

    return blended, {
        "inpaint_model": "local_guided_refinement",
        "inpaint_status": "local-structural-texture-fallback",
        "mask_ratio": round(masked_ratio, 6),
        "patch_radius": patch_radius,
        "ring_passes": ring_passes,
        "refinement_passes": patch_passes,
        "work_scale": round(float(work_scale), 4),
        "work_resolution": [int(ww), int(wh)],
        "preserved_resolution": [int(w), int(h)],
    }


def _run_external_grnet(image_path: Path, mask_path: Path, output_path: Path, params: Dict[str, Any]) -> Dict[str, Any] | None:
    command_template = os.environ.get("GRNET_INPAINT_COMMAND", "").strip()
    if not command_template:
        return None

    command = command_template.format(
        image=str(image_path),
        mask=str(mask_path),
        output=str(output_path),
        profile=shlex.quote(str(params.get("profile", "hq"))),
    )
    subprocess.run(command, check=True, capture_output=True, text=True, shell=True)
    if not output_path.exists():
        raise RuntimeError("Configured gRNet inpainting command did not create the output image.")

    return {
        "inpaint_model": "external_grnet",
        "inpaint_status": "external-guided-refinement-network",
        "command_configured": True,
    }


def inpaint_temple_path(image_path: Path, mask_path: Path, output_path: Path, params: Dict[str, Any] | None = None) -> InpaintResult:
    params = params or {}
    image = _load_rgb(image_path)
    mask = _load_mask(mask_path, image.shape[:2])
    if not np.any(mask):
        _save_rgb(output_path, image)
        return InpaintResult(
            output_path=output_path,
            metadata={
                "inpaint_model": "none",
                "inpaint_status": "empty-mask",
                "completion_used": False,
                "preserved_resolution": [int(image.shape[1]), int(image.shape[0])],
            },
        )

    external_metadata = _run_external_grnet(image_path, mask_path, output_path, params)
    if external_metadata is not None:
        output = _load_rgb(output_path)
        if output.shape[:2] != image.shape[:2]:
            raise RuntimeError("gRNet output resolution does not match the input image.")
        output[~mask] = image[~mask]
        _save_rgb(output_path, output)
        external_metadata.update(
            {
                "completion_used": True,
                "preserved_resolution": [int(image.shape[1]), int(image.shape[0])],
                "boundary_consistency": _boundary_consistency(image, output, mask),
            }
        )
        return InpaintResult(output_path=output_path, metadata=external_metadata)

    output, metadata = _local_guided_refinement(image, mask, params)
    _save_rgb(output_path, output)
    metadata.update(
        {
            "completion_used": True,
            "boundary_consistency": _boundary_consistency(image, output, mask),
            "quality_objectives": [
                "structural-continuity",
                "photorealistic-local-texture",
                "lighting-consistency",
                "perspective-preservation",
                "weathered-material-match",
                "seamless-boundary",
                "full-resolution-output",
            ],
        }
    )
    return InpaintResult(output_path=output_path, metadata=metadata)
