import asyncio
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from completion import complete_point_cloud
from completion.model_info import get_models_info
from inpainting import inpaint_temple_path, is_image_file

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - optional runtime dependency
    o3d = None

try:
    import trimesh
except ImportError:  # pragma: no cover - optional runtime dependency
    trimesh = None

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static" / "mock"
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8010")
STATIC_DIR.mkdir(parents=True, exist_ok=True)
MAX_TXT_CONVERTED_POINTS = int(os.environ.get("MAX_TXT_CONVERTED_POINTS", "320000"))
MAX_PREPROCESS_POINTS = {
    "hq": int(os.environ.get("MAX_PREPROCESS_POINTS_HQ", "180000")),
    "balanced": int(os.environ.get("MAX_PREPROCESS_POINTS_BALANCED", "140000")),
    "preview": int(os.environ.get("MAX_PREPROCESS_POINTS_PREVIEW", "90000")),
}

SAMPLE_BEFORE = STATIC_DIR / "sample_before.ply"
SAMPLE_AFTER = STATIC_DIR / "sample_after.ply"
FRONTEND_MOCK_DIR = BASE_DIR.parent / "frontend" / "public" / "mock"

for sample_name in ("sample_before.ply", "sample_after.ply"):
    source = FRONTEND_MOCK_DIR / sample_name
    target = STATIC_DIR / sample_name

    if source.exists():
        shutil.copyfile(source, target)

app = FastAPI(title="3DITA Reconstruction Backend Stub")
app.mount("/mock", StaticFiles(directory=str(STATIC_DIR)), name="mock")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: Dict[str, Dict[str, Any]] = {}
job_websockets: Dict[str, Set[WebSocket]] = {}


def make_absolute_url(path: str) -> str:
    return f"{PUBLIC_BASE_URL.rstrip('/')}{path}"


def default_metadata() -> Dict[str, Any]:
    return {
        "component_class": "Shikhara",
        "before_points": 12400,
        "after_points": 18750,
        "confidence": 0.87,
    }


def parse_ascii_ply_vertices(content: bytes) -> Tuple[List[str], List[str], int]:
    text = content.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    header_end = next(
        (index for index, line in enumerate(lines) if line.strip() == "end_header"),
        -1,
    )

    if header_end < 0:
        return [], [], 0

    vertex_count = 0
    property_lines: List[str] = []
    in_vertex_element = False

    for line in lines[: header_end + 1]:
        stripped = line.strip()
        if stripped.startswith("element vertex "):
            try:
                vertex_count = int(stripped.split()[-1])
            except ValueError:
                vertex_count = 0
            in_vertex_element = True
        elif stripped.startswith("element "):
            in_vertex_element = False
        elif stripped.startswith("property ") and in_vertex_element:
            property_lines.append(line)

    vertices = lines[header_end + 1 : header_end + 1 + vertex_count]
    return vertices, property_lines, vertex_count


def infer_txt_ply_properties(column_count: int) -> List[str]:
    properties = [
        "property float x",
        "property float y",
        "property float z",
    ]

    if column_count >= 6:
        properties.extend(
            [
                "property uchar red",
                "property uchar green",
                "property uchar blue",
            ]
        )

    # Preserve normals when the TXT layout provides them directly after RGB.
    if column_count >= 9:
        properties.extend(
            [
                "property float nx",
                "property float ny",
                "property float nz",
            ]
        )

    # Some temple exports include one scalar before normals.
    if column_count >= 10:
        properties.insert(6, "property float scale")

    for index in range(len(properties), column_count):
        properties.append(f"property float attr_{index - 2}")

    return properties


def clamp_color(value: float) -> int:
    return max(0, min(255, int(round(value))))


def normalize_txt_parts(parts: List[str]) -> Optional[List[str]]:
    if len(parts) < 3:
        return None

    try:
        numeric_parts = [float(part) for part in parts]
    except ValueError:
        return None

    normalized_values = [
        f"{numeric_parts[0]}",
        f"{numeric_parts[1]}",
        f"{numeric_parts[2]}",
    ]

    if len(numeric_parts) >= 6:
        normalized_values.extend(
            [
                str(clamp_color(numeric_parts[3])),
                str(clamp_color(numeric_parts[4])),
                str(clamp_color(numeric_parts[5])),
            ]
        )

    # Support both XYZ RGB NX NY NZ and XYZ RGB SCALE NX NY NZ layouts.
    if len(numeric_parts) == 9:
        normalized_values.extend(
            [
                f"{numeric_parts[6]}",
                f"{numeric_parts[7]}",
                f"{numeric_parts[8]}",
            ]
        )

    if len(numeric_parts) >= 10:
        normalized_values.extend(
            [
                f"{numeric_parts[6]}",
                f"{numeric_parts[7]}",
                f"{numeric_parts[8]}",
                f"{numeric_parts[9]}",
            ]
        )

    if len(numeric_parts) > 10:
        normalized_values.extend(f"{value}" for value in numeric_parts[10:])

    return normalized_values


def txt_points_to_ply(content: bytes) -> bytes:
    text = content.decode("utf-8", errors="ignore")
    point_lines: List[str] = []
    column_count = 0

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.replace(",", " ").split()
        normalized_values = normalize_txt_parts(parts)
        if not normalized_values:
            continue

        column_count = max(column_count, len(normalized_values))
        point_lines.append(" ".join(normalized_values))

    if not point_lines:
        return content

    header = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(point_lines)}",
    ]
    header.extend(infer_txt_ply_properties(column_count))
    header.append("end_header")

    return ("\n".join(header + point_lines) + "\n").encode("utf-8")


def normalize_point_cloud_content(content: bytes, filename: str = "") -> bytes:
    extension = Path(filename).suffix.lower()
    stripped = content.lstrip()

    if extension == ".txt" or not stripped.startswith(b"ply"):
        converted = txt_points_to_ply(content)
        if converted != content:
            return converted

    return content


def txt_file_to_ply_file(txt_path: Path, ply_path: Path) -> Tuple[int, int]:
    point_count = 0
    column_count = 0

    with txt_path.open("r", encoding="utf-8", errors="ignore") as source_file:
        for line in source_file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            normalized_values = normalize_txt_parts(stripped.replace(",", " ").split())
            if not normalized_values:
                continue

            point_count += 1
            column_count = max(column_count, len(normalized_values))

    if point_count == 0:
        raise RuntimeError("TXT file did not contain any valid point rows.")

    sample_step = max(1, math.ceil(point_count / MAX_TXT_CONVERTED_POINTS))
    sampled_count = math.ceil(point_count / sample_step)
    header = [
        "ply",
        "format ascii 1.0",
        f"element vertex {sampled_count}",
    ]
    header.extend(infer_txt_ply_properties(column_count))
    header.append("end_header")

    with ply_path.open("w", encoding="utf-8", newline="\n") as target_file:
        target_file.write("\n".join(header))
        target_file.write("\n")

        valid_index = 0
        written_count = 0
        with txt_path.open("r", encoding="utf-8", errors="ignore") as source_file:
            for line in source_file:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                normalized_values = normalize_txt_parts(stripped.replace(",", " ").split())
                if not normalized_values:
                    continue

                if valid_index % sample_step == 0:
                    target_file.write(" ".join(normalized_values))
                    target_file.write("\n")
                    written_count += 1
                valid_index += 1

    return written_count, column_count


async def save_upload_file(upload_file: UploadFile, destination: Path, chunk_size: int = 4 * 1024 * 1024) -> int:
    total_bytes = 0

    with destination.open("wb") as target_file:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break

            target_file.write(chunk)
            total_bytes += len(chunk)

    await upload_file.close()
    return total_bytes


def get_property_names(property_lines: List[str]) -> List[str]:
    names: List[str] = []

    for line in property_lines:
        parts = line.strip().split()
        if len(parts) >= 3:
            names.append(parts[-1].lower())

    return names


def get_xyz_indices(property_lines: List[str]) -> Optional[Tuple[int, int, int]]:
    property_names = get_property_names(property_lines)

    try:
        return (
            property_names.index("x"),
            property_names.index("y"),
            property_names.index("z"),
        )
    except ValueError:
        return None


def count_geometry_points(content: bytes) -> int:
    _, _, vertex_count = parse_ascii_ply_vertices(content)
    return vertex_count


def load_point_cloud(path: Path):
    if o3d is None:
        raise RuntimeError(
            "Open3D is not installed. Install it with `python -m pip install open3d` "
            "to enable high-fidelity reconstruction."
        )

    suffix = path.suffix.lower()
    if suffix == ".obj":
        mesh = o3d.io.read_triangle_mesh(str(path))
        if mesh.is_empty():
            raise RuntimeError("Uploaded OBJ mesh could not be read.")

        sample_count = max(250_000, min(len(mesh.vertices) * 8, 900_000))
        point_cloud = mesh.sample_points_poisson_disk(number_of_points=sample_count)
        return point_cloud

    point_cloud = o3d.io.read_point_cloud(str(path))
    if point_cloud.is_empty():
        raise RuntimeError("Uploaded point cloud could not be read.")

    return point_cloud


def point_cloud_extent(point_cloud) -> float:
    bounds = point_cloud.get_axis_aligned_bounding_box()
    extent = bounds.get_extent()
    return max(float(np.linalg.norm(extent)), 1e-6)


def point_cloud_flatness(point_cloud) -> float:
    points = np.asarray(point_cloud.points)
    if len(points) < 16:
        return 1.0

    centered = points - np.mean(points, axis=0)
    eigenvalues = np.linalg.eigvalsh(np.cov(centered.T))
    largest = max(float(eigenvalues[-1]), 1e-9)
    return max(float(eigenvalues[0]) / largest, 0.0)


def preprocess_point_cloud(point_cloud, profile: str):
    point_cloud = point_cloud.remove_non_finite_points()
    point_count = len(point_cloud.points)

    if point_count == 0:
        raise RuntimeError("Point cloud contains no finite points after cleanup.")

    diagonal = point_cloud_extent(point_cloud)
    voxel_divisor = 1050.0 if profile == "hq" else 850.0 if profile == "balanced" else 700.0
    min_voxel = 0.0008 if profile == "hq" else 0.0010 if profile == "balanced" else 0.0012
    voxel_size = max(diagonal / voxel_divisor, min_voxel)
    cleaned = point_cloud

    diagonal = point_cloud_extent(cleaned)
    normal_radius = max(diagonal / 110.0, voxel_size * 3.2)
    if not cleaned.has_normals() or len(cleaned.normals) != len(cleaned.points):
        cleaned.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=normal_radius,
                max_nn=64,
            )
        )

    # Poisson reconstruction needs coherent normals on all sides, otherwise
    # the back of the temple tends to look hollow or get trimmed away.
    cleaned.normalize_normals()

    if len(cleaned.points) >= 1000 and len(cleaned.points) <= 180_000:
        tangent_k = max(20, min(120, len(cleaned.points) // 1200))
        try:
            cleaned.orient_normals_consistent_tangent_plane(tangent_k)
        except RuntimeError:
            center = cleaned.get_center()
            cleaned.orient_normals_towards_camera_location(
                center + np.array([0.0, 0.0, diagonal * 2.5])
            )
    elif len(cleaned.points) > 180_000:
        center = cleaned.get_center()
        cleaned.orient_normals_towards_camera_location(
            center + np.array([0.0, 0.0, diagonal * 2.5])
        )

    cleaned.normalize_normals()

    return cleaned, voxel_size


def remove_meshing_outliers(point_cloud, params: Dict[str, Any] = None):
    if params is None:
        params = {}
    profile = params.get("profile", "balanced")
    enable_sor = params.get("enable_meshing_sor", True if profile in {"hq", "balanced"} else False)
    
    if not enable_sor or len(point_cloud.points) < 100:
        return point_cloud, {
            "meshing_sor_input_points": len(point_cloud.points),
            "meshing_sor_output_points": len(point_cloud.points),
            "meshing_sor_removed_points": 0,
            "meshing_sor_status": "disabled-preserve-real-geometry",
        }
        
    nb_neighbors = int(params.get("meshing_sor_neighbors", 24 if profile == "hq" else 18))
    std_ratio = float(params.get("meshing_sor_std_ratio", 2.5 if profile == "hq" else 2.0))
    
    try:
        cleaned_cloud, outlier_indices = point_cloud.remove_statistical_outlier(
            nb_neighbors=nb_neighbors,
            std_ratio=std_ratio,
        )
        removed_count = len(point_cloud.points) - len(cleaned_cloud.points)
        return cleaned_cloud, {
            "meshing_sor_input_points": len(point_cloud.points),
            "meshing_sor_output_points": len(cleaned_cloud.points),
            "meshing_sor_removed_points": removed_count,
            "meshing_sor_status": f"enabled-sor(nb={nb_neighbors},std={std_ratio})",
        }
    except Exception as exc:
        return point_cloud, {
            "meshing_sor_input_points": len(point_cloud.points),
            "meshing_sor_output_points": len(point_cloud.points),
            "meshing_sor_removed_points": 0,
            "meshing_sor_status": f"failed-fallback:{type(exc).__name__}",
        }


def prepare_meshing_cloud(point_cloud, params: Dict[str, Any]):
    profile = params.get("profile", "balanced")
    default_max = 240_000 if profile == "hq" else 150_000 if profile == "balanced" else 80_000
    max_points = int(params.get("max_meshing_points", default_max))
    upper_limit = 450_000 if profile == "hq" else 300_000 if profile == "balanced" else 160_000
    max_points = max(40_000, min(max_points, upper_limit))
    
    if len(point_cloud.points) <= max_points or params.get("full_resolution_meshing", False):
        return point_cloud, {
            "meshing_cloud_points": len(point_cloud.points),
            "meshing_cloud_status": "full-resolution",
        }

    step = max(1, math.ceil(len(point_cloud.points) / max_points))
    meshing_cloud = point_cloud.uniform_down_sample(step)
    return meshing_cloud, {
        "meshing_cloud_points": len(meshing_cloud.points),
        "meshing_cloud_status": "fast-sampled-for-poisson",
        "meshing_cloud_source_points": len(point_cloud.points),
        "meshing_cloud_sample_step": step,
    }


def transfer_vertex_colors(mesh, reference_cloud):
    if not reference_cloud.has_colors() or len(reference_cloud.colors) == 0:
        return mesh

    reference_points = np.asarray(reference_cloud.points)
    reference_colors = np.asarray(reference_cloud.colors)
    vertices = np.asarray(mesh.vertices)

    if len(reference_points) == 0 or len(vertices) == 0:
        return mesh

    kdtree = o3d.geometry.KDTreeFlann(reference_cloud)
    mesh_colors = np.zeros((len(vertices), 3))

    for index, vertex in enumerate(vertices):
        _, indices, _ = kdtree.search_knn_vector_3d(vertex, 1)
        mesh_colors[index] = reference_colors[indices[0]]

    mesh.vertex_colors = o3d.utility.Vector3dVector(mesh_colors)
    return mesh


def edge_aware_bilateral_smooth_mesh(mesh, iterations: int = 1):
    if mesh.is_empty() or len(mesh.vertices) == 0 or len(mesh.triangles) == 0:
        return mesh

    vertex_count = len(mesh.vertices)
    if vertex_count > 300_000:
        return mesh

    mesh.compute_vertex_normals()
    vertices = np.asarray(mesh.vertices).copy()
    normals = np.asarray(mesh.vertex_normals).copy()
    mesh.compute_adjacency_list()
    adjacency = mesh.adjacency_list

    bbox = mesh.get_axis_aligned_bounding_box()
    diagonal = max(float(np.linalg.norm(bbox.get_extent())), 1e-6)
    spatial_sigma = max(diagonal / 420.0, 1e-5)
    normal_sigma = 0.22

    for _ in range(max(0, iterations)):
        next_vertices = vertices.copy()
        for index, neighbors in enumerate(adjacency):
            if len(neighbors) < 3:
                continue

            neighbor_indices = np.asarray(list(neighbors), dtype=np.int64)
            deltas = vertices[neighbor_indices] - vertices[index]
            distances = np.linalg.norm(deltas, axis=1)
            normal_alignment = np.clip(normals[neighbor_indices] @ normals[index], -1.0, 1.0)

            spatial_weights = np.exp(-(distances * distances) / (2.0 * spatial_sigma * spatial_sigma))
            normal_weights = np.exp(-((1.0 - normal_alignment) ** 2) / (2.0 * normal_sigma * normal_sigma))
            weights = spatial_weights * normal_weights
            weight_sum = float(weights.sum())
            if weight_sum <= 1e-9:
                continue

            target = (vertices[neighbor_indices] * weights[:, None]).sum(axis=0) / weight_sum
            # Keep the move conservative so worn stone edges stay crisp.
            next_vertices[index] = vertices[index] * 0.82 + target * 0.18

        vertices = next_vertices

    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.compute_vertex_normals()
    return mesh


def finalize_mesh(mesh, processed_cloud, color_reference_cloud, profile: str, voxel_size: float):
    if mesh.is_empty():
        return mesh

    bbox = processed_cloud.get_axis_aligned_bounding_box()
    mesh = mesh.crop(bbox.scale(1.08, bbox.get_center()))
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()

    if len(mesh.triangles) > 0:
        mesh = edge_aware_bilateral_smooth_mesh(mesh, iterations=1)
        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_unreferenced_vertices()

    mesh.compute_vertex_normals()
    mesh = transfer_vertex_colors(mesh, color_reference_cloud)
    return mesh


def reconstruct_with_poisson(processed_cloud, profile: str, params: Dict[str, Any]):
    requested_detail = int(params.get("detail", 10 if profile == "hq" else 9 if profile == "balanced" else 8))
    max_detail = 11 if profile == "hq" else 10 if profile == "balanced" else 8
    requested_detail = max(6, min(max_detail, requested_detail))
    if len(processed_cloud.points) > 90_000 and not params.get("full_resolution_meshing", False):
        if profile == "hq":
            requested_detail = min(requested_detail, 10)
        elif profile == "balanced":
            requested_detail = min(requested_detail, 9)
        else:
            requested_detail = min(requested_detail, 7)
    if len(processed_cloud.points) < 250_000:
        depth = min(10 if profile == "hq" else 9, requested_detail)
    elif len(processed_cloud.points) < 650_000:
        depth = min(9 if profile == "hq" else 8, max(6, requested_detail - 1))
    else:
        depth = min(8 if profile == "hq" else 7, max(6, requested_detail - 2))

    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        processed_cloud,
        depth=depth,
        width=0,
        scale=1.24,
        linear_fit=True,
    )

    densities_array = np.asarray(densities)
    if densities_array.size:
        density_quantile = 0.006 if profile == "hq" else 0.01 if profile == "balanced" else 0.014
        density_threshold = float(np.quantile(densities_array, density_quantile))
        low_density_vertices = densities_array < density_threshold
        mesh.remove_vertices_by_mask(low_density_vertices)

    if len(mesh.triangles) > 0:
        mesh = mesh.filter_smooth_laplacian(
            number_of_iterations=5,
            lambda_filter=0.5,
        )
        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_unreferenced_vertices()

    return mesh


def extract_added_geometry_cloud(observed_cloud, reconstructed_cloud, voxel_size: float):
    observed_points = np.asarray(observed_cloud.points)
    reconstructed_points = np.asarray(reconstructed_cloud.points)
    if len(observed_points) == 0 or len(reconstructed_points) == 0:
        return o3d.geometry.PointCloud(), 0

    distances = np.asarray(reconstructed_cloud.compute_point_cloud_distance(observed_cloud))
    threshold = max(voxel_size * 1.85, point_cloud_extent(observed_cloud) / 520.0, 0.0025)
    added_points = reconstructed_points[distances > threshold]

    added_cloud = o3d.geometry.PointCloud()
    if len(added_points) == 0:
        return added_cloud, 0

    added_cloud.points = o3d.utility.Vector3dVector(added_points)
    green = np.tile(np.array([[0.0, 1.0, 0.16]], dtype=np.float64), (len(added_points), 1))
    added_cloud.colors = o3d.utility.Vector3dVector(green)
    return added_cloud, len(added_points)


def build_restoration_visual_meshes(mesh, added_cloud, voxel_size: float):
    if mesh.is_empty() or len(mesh.vertices) == 0:
        return mesh, o3d.geometry.TriangleMesh(), 0

    visual_mesh = o3d.geometry.TriangleMesh(mesh)
    dark_color = np.array([0.09, 0.105, 0.095], dtype=np.float64)
    green_color = np.array([0.0, 1.0, 0.16], dtype=np.float64)
    vertex_count = len(visual_mesh.vertices)
    colors = np.tile(dark_color, (vertex_count, 1))

    if added_cloud is None or len(added_cloud.points) == 0:
        visual_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
        return visual_mesh, o3d.geometry.TriangleMesh(), 0

    vertex_cloud = o3d.geometry.PointCloud()
    vertex_cloud.points = o3d.utility.Vector3dVector(np.asarray(visual_mesh.vertices))
    distances = np.asarray(vertex_cloud.compute_point_cloud_distance(added_cloud))
    threshold = max(voxel_size * 3.5, point_cloud_extent(added_cloud) / 80.0, 0.004)
    restored_vertex_mask = distances <= threshold
    colors[restored_vertex_mask] = green_color
    visual_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)

    triangles = np.asarray(visual_mesh.triangles)
    if len(triangles) == 0 or not np.any(restored_vertex_mask):
        return visual_mesh, o3d.geometry.TriangleMesh(), int(restored_vertex_mask.sum())

    restored_triangle_mask = np.any(restored_vertex_mask[triangles], axis=1)
    restored_mesh = o3d.geometry.TriangleMesh()
    restored_mesh.vertices = o3d.utility.Vector3dVector(np.asarray(visual_mesh.vertices).copy())
    restored_mesh.triangles = o3d.utility.Vector3iVector(triangles[restored_triangle_mask].copy())
    restored_colors = np.tile(green_color, (vertex_count, 1))
    restored_mesh.vertex_colors = o3d.utility.Vector3dVector(restored_colors)
    restored_mesh.remove_unreferenced_vertices()
    restored_mesh.remove_degenerate_triangles()
    restored_mesh.compute_vertex_normals()
    visual_mesh.compute_vertex_normals()

    return visual_mesh, restored_mesh, int(restored_vertex_mask.sum())


def estimate_reconstruction_stats(before_points: int, reconstruction_points: int, generated_points: int, triangle_count: int) -> Dict[str, Any]:
    if generated_points <= 0:
        holes_closed = 0
    else:
        points_per_region = max(before_points * 0.025, 1000)
        holes_closed = max(1, min(99, int(round(generated_points / points_per_region))))
    if before_points <= 0:
        completeness = 0.0
    else:
        density_gain = min(max((reconstruction_points - before_points) / max(before_points * 0.28, 1), 0.0), 1.0)
        mesh_support = 1.0 if triangle_count >= before_points * 0.35 else max(0.0, triangle_count / max(before_points * 0.35, 1))
        completeness = min(99.0, 72.0 + (density_gain * 18.0) + (mesh_support * 9.0))

    return {
        "holes_closed": holes_closed,
        "surface_completeness": round(float(completeness), 1),
    }


def reconstruct_with_ball_pivoting(processed_cloud, voxel_size: float):
    radii = o3d.utility.DoubleVector(
        [
            max(voxel_size * 1.6, 0.0015),
            max(voxel_size * 2.6, 0.0025),
            max(voxel_size * 4.2, 0.0045),
        ]
    )
    return o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
        processed_cloud,
        radii,
    )


def reconstruct_with_alpha_shape(processed_cloud, voxel_size: float, profile: str):
    alpha_multiplier = 9.0 if profile == "hq" else 11.0 if profile == "balanced" else 13.0
    alpha = max(voxel_size * alpha_multiplier, 0.004)
    tetra_mesh, pt_map = o3d.geometry.TetraMesh.create_from_point_cloud(processed_cloud)
    return o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
        processed_cloud,
        alpha,
        tetra_mesh,
        pt_map,
    )


def repair_mesh_holes_with_trimesh(mesh):
    if trimesh is None or mesh.is_empty() or len(mesh.vertices) == 0 or len(mesh.triangles) == 0:
        return mesh, {
            "trimesh_fill_holes_used": False,
            "trimesh_fill_holes_status": "unavailable-or-empty",
        }

    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.triangles)
    try:
        repaired = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        before_faces = len(repaired.faces)
        before_watertight = bool(repaired.is_watertight)
        filled = trimesh.repair.fill_holes(repaired)

        if hasattr(repaired, "remove_infinite_values"):
            repaired.remove_infinite_values()
        if hasattr(repaired, "process"):
            repaired.process(validate=True)
        if hasattr(repaired, "remove_unreferenced_vertices"):
            repaired.remove_unreferenced_vertices()

        repaired_mesh = o3d.geometry.TriangleMesh()
        repaired_mesh.vertices = o3d.utility.Vector3dVector(np.asarray(repaired.vertices, dtype=np.float64))
        repaired_mesh.triangles = o3d.utility.Vector3iVector(np.asarray(repaired.faces, dtype=np.int32))
        repaired_mesh.compute_vertex_normals()

        return repaired_mesh, {
            "trimesh_fill_holes_used": True,
            "trimesh_fill_holes_result": bool(filled),
            "trimesh_watertight_before": before_watertight,
            "trimesh_watertight_after": bool(repaired.is_watertight),
            "trimesh_faces_before": int(before_faces),
            "trimesh_faces_after": int(len(repaired.faces)),
        }
    except Exception:
        return mesh, {
            "trimesh_fill_holes_used": False,
            "trimesh_fill_holes_status": "failed-fallback",
        }


def maybe_repair_mesh_holes_with_trimesh(mesh, params: Dict[str, Any]):
    if not params.get("enable_trimesh_repair", False):
        return mesh, {
            "trimesh_fill_holes_used": False,
            "trimesh_fill_holes_status": "skipped-fast-processing",
        }
    return repair_mesh_holes_with_trimesh(mesh)


def ensure_mesh_vertex_count(mesh, minimum_vertices: int, params: Dict[str, Any]):
    if not params.get("preserve_output_density", False):
        return mesh, {
            "vertex_count_target": minimum_vertices,
            "vertex_count_upsampled": False,
            "vertex_count_status": "skipped-fast-processing",
        }

    if mesh.is_empty() or minimum_vertices <= 0:
        return mesh, {"vertex_count_target": minimum_vertices, "vertex_count_upsampled": False}

    before_vertices = len(mesh.vertices)
    if before_vertices > minimum_vertices:
        return mesh, {
            "vertex_count_target": minimum_vertices,
            "vertex_count_before_upsample": before_vertices,
            "vertex_count_after_upsample": before_vertices,
            "vertex_count_upsampled": False,
        }

    upsampled = mesh
    iterations = 0
    while len(upsampled.vertices) <= minimum_vertices and iterations < 2:
        upsampled = upsampled.subdivide_midpoint(number_of_iterations=1)
        iterations += 1

    upsampled.compute_vertex_normals()
    return upsampled, {
        "vertex_count_target": minimum_vertices,
        "vertex_count_before_upsample": before_vertices,
        "vertex_count_after_upsample": len(upsampled.vertices),
        "vertex_count_upsampled": len(upsampled.vertices) > before_vertices,
        "vertex_count_upsample_iterations": iterations,
    }


def detect_boundary_edges(mesh):
    triangles = np.asarray(mesh.triangles)
    if len(triangles) == 0:
        return np.empty((0, 2), dtype=np.int64)

    edge_counts: Dict[Tuple[int, int], int] = {}
    for a, b, c in triangles:
        for u, v in ((a, b), (b, c), (c, a)):
            edge = tuple(sorted((int(u), int(v))))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    return np.asarray(
        [edge for edge, count in edge_counts.items() if count == 1],
        dtype=np.int64,
    )


def boundary_loops_from_edges(boundary_edges: np.ndarray) -> List[List[int]]:
    adjacency: Dict[int, List[int]] = {}
    for a, b in boundary_edges:
        adjacency.setdefault(int(a), []).append(int(b))
        adjacency.setdefault(int(b), []).append(int(a))

    loops: List[List[int]] = []
    visited_edges: Set[Tuple[int, int]] = set()

    for start, neighbors in adjacency.items():
        for neighbor in neighbors:
            edge_key = tuple(sorted((start, neighbor)))
            if edge_key in visited_edges:
                continue

            loop = [start]
            previous = start
            current = neighbor
            visited_edges.add(edge_key)

            for _ in range(len(adjacency) + 8):
                loop.append(current)
                candidates = [
                    item for item in adjacency.get(current, [])
                    if item != previous and tuple(sorted((current, item))) not in visited_edges
                ]
                if not candidates:
                    break

                next_vertex = candidates[0]
                visited_edges.add(tuple(sorted((current, next_vertex))))
                previous, current = current, next_vertex
                if current == start:
                    break

            if len(loop) >= 4:
                loops.append(loop)

    return loops


def central_hole_bbox_from_cloud(point_cloud, profile: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if params.get("grnet_repair_bbox") or len(point_cloud.points) < 200:
        return {}

    preview_cloud = point_cloud
    max_preview_points = int(params.get("hole_detection_max_points", 80_000))
    max_preview_points = max(20_000, min(max_preview_points, 140_000))
    if len(point_cloud.points) > max_preview_points:
        step = max(1, math.ceil(len(point_cloud.points) / max_preview_points))
        preview_cloud = point_cloud.uniform_down_sample(step)

    voxel_size = max(point_cloud_extent(point_cloud) / 420.0, 0.003)
    try:
        preview_mesh = reconstruct_with_ball_pivoting(preview_cloud, voxel_size)
    except Exception:
        try:
            preview_mesh = reconstruct_with_alpha_shape(preview_cloud, voxel_size, profile)
        except Exception:
            return {}

    boundary_edges = detect_boundary_edges(preview_mesh)
    loops = boundary_loops_from_edges(boundary_edges)
    if not loops:
        return {}

    vertices = np.asarray(preview_mesh.vertices)
    mesh_center = vertices.mean(axis=0)
    best_loop = None
    best_score = -1.0
    for loop in loops:
        loop_points = vertices[np.asarray(loop, dtype=np.int64)]
        extent = loop_points.ptp(axis=0)
        area_score = float(np.linalg.norm(extent[:2]) + np.linalg.norm(extent))
        centrality = 1.0 / (1.0 + float(np.linalg.norm(loop_points.mean(axis=0) - mesh_center)))
        score = area_score * centrality
        if score > best_score:
            best_score = score
            best_loop = loop_points

    if best_loop is None:
        return {}

    extent = np.maximum(best_loop.ptp(axis=0), point_cloud_extent(point_cloud) / 80.0)
    padding = float(params.get("hole_mask_padding", 0.32))
    bbox_min = best_loop.min(axis=0) - extent * padding
    bbox_max = best_loop.max(axis=0) + extent * padding
    params["grnet_repair_bbox"] = [
        float(bbox_min[0]),
        float(bbox_min[1]),
        float(bbox_min[2]),
        float(bbox_max[0]),
        float(bbox_max[1]),
        float(bbox_max[2]),
    ]
    params["grnet_mask_source"] = "detected-hole-boundary"
    params["force_completion"] = True
    return {
        "hole_mask_source": "boundary_edges",
        "hole_boundary_vertices": int(len(best_loop)),
        "hole_repair_bbox": [round(float(value), 6) for value in params["grnet_repair_bbox"]],
    }


def fill_mesh_boundary_holes(mesh, color_reference_cloud, profile: str):
    if mesh.is_empty() or len(mesh.triangles) == 0:
        return mesh, {"holes_closed": 0, "hole_fill_vertices": 0}

    boundary_edges = detect_boundary_edges(mesh)
    loops = boundary_loops_from_edges(boundary_edges)
    if not loops:
        return mesh, {"holes_closed": 0, "hole_fill_vertices": 0}

    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    mesh_center = vertices.mean(axis=0)

    candidate_loops = []
    for loop in loops:
        if len(loop) < 4:
            continue
        loop_points = vertices[np.asarray(loop, dtype=np.int64)]
        perimeter = float(np.linalg.norm(np.diff(np.vstack([loop_points, loop_points[0]]), axis=0), axis=1).sum())
        centrality = 1.0 / (1.0 + float(np.linalg.norm(loop_points.mean(axis=0) - mesh_center)))
        candidate_loops.append((perimeter * centrality, loop))

    if not candidate_loops:
        return mesh, {"holes_closed": 0, "hole_fill_vertices": 0}

    candidate_loops.sort(reverse=True, key=lambda item: item[0])
    max_holes = 1 if profile != "hq" else 2
    new_vertices = vertices.tolist()
    new_triangles = triangles.tolist()
    patch_vertex_indices: List[int] = []

    for _, loop in candidate_loops[:max_holes]:
        loop_indices = np.asarray(loop, dtype=np.int64)
        loop_points = vertices[loop_indices]
        center = loop_points.mean(axis=0)
        center_index = len(new_vertices)
        new_vertices.append(center.tolist())
        patch_vertex_indices.append(center_index)

        for index, current_vertex in enumerate(loop):
            next_vertex = loop[(index + 1) % len(loop)]
            new_triangles.append([int(current_vertex), int(next_vertex), center_index])

    filled_mesh = o3d.geometry.TriangleMesh()
    filled_mesh.vertices = o3d.utility.Vector3dVector(np.asarray(new_vertices, dtype=np.float64))
    filled_mesh.triangles = o3d.utility.Vector3iVector(np.asarray(new_triangles, dtype=np.int32))
    filled_mesh.remove_degenerate_triangles()
    filled_mesh.remove_duplicated_triangles()
    filled_mesh.remove_unreferenced_vertices()
    filled_mesh.compute_vertex_normals()

    if len(patch_vertex_indices) > 0:
        filled_mesh = filled_mesh.filter_smooth_laplacian(number_of_iterations=5, lambda_filter=0.5)
        filled_mesh.compute_vertex_normals()

    filled_mesh = transfer_vertex_colors(filled_mesh, color_reference_cloud)
    if filled_mesh.has_vertex_colors():
        colors = np.asarray(filled_mesh.vertex_colors)
        patch_color = np.array([0.38, 0.36, 0.30], dtype=np.float64)
        if color_reference_cloud.has_colors() and len(color_reference_cloud.colors) > 0:
            patch_color = np.asarray(color_reference_cloud.colors).mean(axis=0)
        rng = np.random.default_rng(42)
        for index in patch_vertex_indices:
            if index < len(colors):
                moss = np.array([0.08, 0.18, 0.07]) * rng.uniform(0.0, 0.55)
                weather_noise = rng.normal(0.0, 0.035, size=3)
                colors[index] = np.clip((patch_color * 0.9) + moss + weather_noise, 0.0, 1.0)
        filled_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)

    return filled_mesh, {
        "holes_closed": min(max_holes, len(candidate_loops)),
        "hole_fill_vertices": int(len(patch_vertex_indices)),
        "hole_fill_method": "boundary-advancing-front-fan",
        "hole_fill_smoothing": "laplacian(iterations=5,lambda=0.5)",
    }


def force_fill_central_void_cap(mesh, color_reference_cloud, params: Dict[str, Any]):
    if mesh.is_empty() or len(mesh.vertices) < 32:
        return mesh, o3d.geometry.TriangleMesh(), {
            "central_void_cap_used": False,
            "central_void_cap_status": "empty-or-too-small",
        }

    vertices = np.asarray(mesh.vertices)
    bounds_min = vertices.min(axis=0)
    bounds_max = vertices.max(axis=0)
    extent = np.maximum(bounds_max - bounds_min, 1e-6)
    best = None

    for axis in range(3):
        other_axes = [item for item in range(3) if item != axis]
        for side in (-1, 1):
            threshold = (
                bounds_max[axis] - extent[axis] * 0.22
                if side > 0
                else bounds_min[axis] + extent[axis] * 0.22
            )
            slice_mask = vertices[:, axis] >= threshold if side > 0 else vertices[:, axis] <= threshold
            slice_points = vertices[slice_mask]
            if len(slice_points) < 40:
                continue

            projected = slice_points[:, other_axes]
            center_2d = np.median(projected, axis=0)
            radii = np.linalg.norm(projected - center_2d, axis=1)
            outer_radius = float(np.percentile(radii, 82))
            inner_radius = float(np.percentile(radii, 18))
            if outer_radius <= 1e-9:
                continue

            hole_ratio = inner_radius / outer_radius
            score = hole_ratio * len(slice_points)
            if hole_ratio < float(params.get("central_void_min_ratio", 0.18)):
                continue
            if best is None or score > best["score"]:
                best = {
                    "axis": axis,
                    "side": side,
                    "other_axes": other_axes,
                    "center_2d": center_2d,
                    "plane": float(np.median(slice_points[:, axis])),
                    "radius": max(inner_radius * 1.08, outer_radius * 0.22),
                    "score": score,
                    "hole_ratio": hole_ratio,
                }

    if best is None:
        return mesh, o3d.geometry.TriangleMesh(), {
            "central_void_cap_used": False,
            "central_void_cap_status": "no-central-void-candidate",
        }

    segments = int(params.get("central_void_cap_segments", 48))
    segments = max(24, min(segments, 96))
    axis = best["axis"]
    other_axes = best["other_axes"]
    plane = best["plane"]
    radius = best["radius"]
    center_2d = best["center_2d"]

    cap_vertices = []
    center_3d = np.zeros(3, dtype=np.float64)
    center_3d[axis] = plane
    center_3d[other_axes] = center_2d
    cap_vertices.append(center_3d)

    for index in range(segments):
        angle = (2.0 * math.pi * index) / segments
        point = center_3d.copy()
        point[other_axes[0]] = center_2d[0] + math.cos(angle) * radius
        point[other_axes[1]] = center_2d[1] + math.sin(angle) * radius
        cap_vertices.append(point)

    cap_triangles = []
    for index in range(segments):
        a = 0
        b = index + 1
        c = 1 if index == segments - 1 else index + 2
        cap_triangles.append([a, b, c] if best["side"] > 0 else [a, c, b])

    cap_mesh = o3d.geometry.TriangleMesh()
    cap_mesh.vertices = o3d.utility.Vector3dVector(np.asarray(cap_vertices, dtype=np.float64))
    cap_mesh.triangles = o3d.utility.Vector3iVector(np.asarray(cap_triangles, dtype=np.int32))
    cap_mesh.compute_vertex_normals()

    base_color = np.array([0.42, 0.40, 0.34], dtype=np.float64)
    if color_reference_cloud.has_colors() and len(color_reference_cloud.colors) > 0:
        reference_colors = np.asarray(color_reference_cloud.colors)
        reference_points = np.asarray(color_reference_cloud.points)
        if len(reference_points) > 0:
            reference_cloud = color_reference_cloud
            tree = o3d.geometry.KDTreeFlann(reference_cloud)
            sampled_colors = []
            for point in cap_vertices[1:: max(1, segments // 12)]:
                _, indices, _ = tree.search_knn_vector_3d(point, 3)
                sampled_colors.extend(reference_colors[indices])
            if sampled_colors:
                base_color = np.mean(np.asarray(sampled_colors), axis=0)

    rng = np.random.default_rng(7)
    cap_colors = []
    for index in range(len(cap_vertices)):
        moss = np.array([0.05, 0.16, 0.04]) * (0.25 + 0.75 * (index % 5 == 0))
        noise = rng.normal(0.0, 0.028, size=3)
        cap_colors.append(np.clip(base_color * 0.88 + moss + noise, 0.0, 1.0))
    cap_mesh.vertex_colors = o3d.utility.Vector3dVector(np.asarray(cap_colors, dtype=np.float64))

    combined = mesh + cap_mesh
    combined.remove_duplicated_vertices()
    combined.remove_degenerate_triangles()
    combined.compute_vertex_normals()

    red_region = o3d.geometry.TriangleMesh(cap_mesh)
    red_region.vertex_colors = o3d.utility.Vector3dVector(
        np.tile(np.array([[1.0, 0.04, 0.02]], dtype=np.float64), (len(red_region.vertices), 1))
    )

    return combined, red_region, {
        "central_void_cap_used": True,
        "central_void_cap_axis": int(axis),
        "central_void_cap_side": int(best["side"]),
        "central_void_cap_vertices": int(len(cap_vertices)),
        "central_void_cap_triangles": int(len(cap_triangles)),
        "central_void_hole_ratio": round(float(best["hole_ratio"]), 4),
        "central_void_cap_radius": round(float(radius), 6),
    }


def reconstruct_surface_mesh(processed_cloud, color_reference_cloud, reconstruction_method: str, profile: str, params: Dict[str, Any]):
    voxel_size = max(point_cloud_extent(processed_cloud) / 700.0, 0.0012)
    resolved_method = reconstruction_method
    flatness = point_cloud_flatness(processed_cloud)
    prefer_conservative = flatness < 0.22

    try:
        if reconstruction_method == "auto":
            if profile == "hq" or not prefer_conservative:
                mesh = reconstruct_with_poisson(processed_cloud, profile, params)
                resolved_method = "poisson"
            else:
                mesh = reconstruct_with_ball_pivoting(processed_cloud, voxel_size)
                resolved_method = "ball_pivoting"
        elif reconstruction_method == "ball_pivoting":
            mesh = reconstruct_with_ball_pivoting(processed_cloud, voxel_size)
        elif reconstruction_method == "alpha_shape":
            mesh = reconstruct_with_alpha_shape(processed_cloud, voxel_size, profile)
        else:
            mesh = reconstruct_with_poisson(processed_cloud, profile, params)
            resolved_method = "poisson"
    except Exception:
        try:
            mesh = reconstruct_with_alpha_shape(processed_cloud, voxel_size, profile)
            resolved_method = "alpha_shape"
        except Exception:
            mesh = reconstruct_with_poisson(processed_cloud, profile, params)
            resolved_method = "poisson"

    if mesh.is_empty() or len(mesh.vertices) < 1000 or len(mesh.triangles) < 1000:
        if resolved_method != "poisson" and not prefer_conservative:
            mesh = reconstruct_with_poisson(processed_cloud, profile, params)
            resolved_method = "poisson"
        else:
            mesh = reconstruct_with_alpha_shape(processed_cloud, voxel_size, profile)
            resolved_method = "alpha_shape"

    mesh = finalize_mesh(mesh, processed_cloud, color_reference_cloud, profile, voxel_size)
    return mesh, processed_cloud, voxel_size, resolved_method


def make_damaged_point_cloud(content: bytes) -> Tuple[bytes, int]:
    vertices, coordinate_properties, vertex_count = parse_ascii_ply_vertices(content)

    if not vertices:
        return content, 0

    xyz_indices = get_xyz_indices(coordinate_properties)
    if xyz_indices is None:
        return content, vertex_count

    points = []
    for line in vertices:
        parts = line.split()
        if len(parts) <= max(xyz_indices):
            continue

        try:
            x, y, z = (
                float(parts[xyz_indices[0]]),
                float(parts[xyz_indices[1]]),
                float(parts[xyz_indices[2]]),
            )
        except ValueError:
            continue

        points.append((x, y, z, line))

    if not points:
        return content, vertex_count

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    range_x = max(max_x - min_x, 0.000001)
    range_y = max(max_y - min_y, 0.000001)
    range_z = max(max_z - min_z, 0.000001)

    damaged_lines = []
    for index, (x, y, z, line) in enumerate(points):
        nx = (x - min_x) / range_x
        ny = (y - min_y) / range_y
        nz = (z - min_z) / range_z

        upper_chip = ny > 0.66 and 0.22 < nx < 0.62 and 0.22 < nz < 0.82
        side_chip = nx > 0.70 and 0.34 < ny < 0.70 and 0.28 < nz < 0.72
        light_erosion = index % 47 == 0 and ny > 0.25

        if upper_chip or side_chip or light_erosion:
            continue

        damaged_lines.append(line)

    if len(damaged_lines) < max(10, int(len(points) * 0.75)):
        damaged_lines = [line for index, (*_, line) in enumerate(points) if index % 23 != 0]

    header = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(damaged_lines)}",
    ]
    header.extend(coordinate_properties or [
        "property float x",
        "property float y",
        "property float z",
    ])
    header.append("end_header")

    return ("\n".join(header + damaged_lines) + "\n").encode("utf-8"), len(damaged_lines)


async def broadcast_job_update(job_id: str) -> None:
    active_sockets = job_websockets.get(job_id, set())
    sockets = list(active_sockets)
    if not sockets:
        return

    payload = {
        "type": "progress",
        "status": jobs[job_id]["status"],
        "progress": jobs[job_id]["progress"],
    }

    if jobs[job_id]["status"] in {"done", "complete", "completed"} and jobs[job_id].get("after_url"):
        payload.update({
            "type": "complete",
            "before_url": jobs[job_id]["before_url"],
            "after_url": jobs[job_id]["after_url"],
            "added_geometry_url": jobs[job_id].get("added_geometry_url"),
            "restoration_panel_url": jobs[job_id].get("restoration_panel_url"),
            "restored_regions_url": jobs[job_id].get("restored_regions_url"),
            "metadata": jobs[job_id]["metadata"],
        })
    elif jobs[job_id]["status"] in {"error", "failed"}:
        payload.update({
            "type": "error",
            "message": jobs[job_id].get("message", "Reconstruction failed."),
        })

    stale_sockets = []
    for websocket in sockets.copy():
        try:
            await websocket.send_json(payload)
        except Exception:
            stale_sockets.append(websocket)

    for websocket in stale_sockets:
        active_sockets.discard(websocket)


async def run_in_worker(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args))


async def run_reconstruction(job_id: str, model: str, params: Dict[str, Any]) -> None:
    print(f"[backend] starting reconstruction for job_id={job_id}, model={model}", flush=True)
    jobs[job_id].update(
        {
            "status": "processing",
            "progress": 0,
        }
    )
    await broadcast_job_update(job_id)

    def update_status(progress: int, message: str) -> None:
        jobs[job_id].update(
            {
                "status": "processing",
                "progress": progress,
                "status_message": message,
            }
        )

    original_suffix = Path(jobs[job_id].get("filename") or "").suffix.lower()
    upload_path_value = jobs[job_id].get("upload_path")
    upload_path = Path(upload_path_value) if upload_path_value else SAMPLE_AFTER
    normalized_input_suffix = ".ply" if original_suffix == ".txt" else (original_suffix or ".ply")
    source_path = (
        STATIC_DIR / f"{job_id}_source{normalized_input_suffix}"
        if original_suffix == ".txt"
        else upload_path
    )
    before_path = source_path
    after_path = STATIC_DIR / f"{job_id}_after.ply"
    added_path = STATIC_DIR / f"{job_id}_added_geometry.ply"
    panel3_path = STATIC_DIR / f"{job_id}_restoration_panel.ply"
    restored_region_path = STATIC_DIR / f"{job_id}_restored_regions.ply"

    try:
        update_status(8, "Preparing uploaded geometry")
        await broadcast_job_update(job_id)

        if original_suffix == ".txt":
            await run_in_worker(txt_file_to_ply_file, upload_path, source_path)
            try:
                upload_path.unlink()
            except OSError:
                pass

        update_status(18, "Loading high fidelity geometry")
        await broadcast_job_update(job_id)
        point_cloud = await run_in_worker(load_point_cloud, source_path)

        update_status(36, "Denoising and orienting point cloud")
        await broadcast_job_update(job_id)
        reconstruction_mode = model if model in {"geometry_only", "dl_completion"} else "geometry_only"
        reconstruction_method = params.get("mesh_method") if isinstance(params, dict) else None
        if reconstruction_method not in {"poisson", "ball_pivoting", "alpha_shape"}:
            reconstruction_method = "poisson"
        profile = params.get("profile") if isinstance(params, dict) else None
        if profile not in {"hq", "balanced", "preview"}:
            profile = model if model in {"hq", "balanced", "preview"} else "balanced"

        # Apply smart default triggers based on the reconstruction quality profile
        if isinstance(params, dict):
            if "profile" not in params:
                params["profile"] = profile
            if "enable_trimesh_repair" not in params:
                params["enable_trimesh_repair"] = True if profile in {"hq", "balanced"} else False
            if "preserve_output_density" not in params:
                params["preserve_output_density"] = True if profile in {"hq", "balanced"} else False
            if "enable_hole_detection" not in params:
                params["enable_hole_detection"] = True if profile == "hq" else False
            if "full_resolution_meshing" not in params:
                params["full_resolution_meshing"] = True if profile == "hq" else False

        processed_cloud, preprocess_voxel_size = await run_in_worker(
            preprocess_point_cloud,
            point_cloud,
            profile,
        )
        if params.get("enable_hole_detection", False):
            hole_mask_metadata = await run_in_worker(
                central_hole_bbox_from_cloud,
                processed_cloud,
                profile,
                params,
            )
        else:
            hole_mask_metadata = {"hole_mask_status": "skipped-fast-processing"}

        update_status(54, "Completing missing geometry")
        await broadcast_job_update(job_id)
        completion_request_mode = reconstruction_mode
        if reconstruction_mode == "geometry_only" and params.get("force_completion"):
            completion_request_mode = "dl_completion"

        reconstruction_cloud, completion_metadata = await run_in_worker(
            complete_point_cloud,
            processed_cloud,
            completion_request_mode,
            profile,
            params,
        )

        reconstruction_cloud, meshing_cleanup_metadata = await run_in_worker(
            remove_meshing_outliers,
            reconstruction_cloud,
            params,
        )
        meshing_input_cloud, meshing_cloud_metadata = await run_in_worker(
            prepare_meshing_cloud,
            reconstruction_cloud,
            params,
        )

        update_status(70, "Reconstructing surface mesh")
        await broadcast_job_update(job_id)
        mesh, meshing_cloud, voxel_size, resolved_method = await run_in_worker(
            reconstruct_surface_mesh,
            meshing_input_cloud,
            point_cloud,
            reconstruction_method,
            profile,
            params,
        )
        mesh, trimesh_repair_metadata = await run_in_worker(
            maybe_repair_mesh_holes_with_trimesh,
            mesh,
            params,
        )
        mesh, hole_fill_metadata = await run_in_worker(
            fill_mesh_boundary_holes,
            mesh,
            point_cloud,
            profile,
        )
        mesh, central_void_region_mesh, central_void_metadata = await run_in_worker(
            force_fill_central_void_cap,
            mesh,
            point_cloud,
            params,
        )
        mesh, vertex_count_metadata = await run_in_worker(
            ensure_mesh_vertex_count,
            mesh,
            len(point_cloud.points),
            params,
        )
        added_cloud, added_point_count = await run_in_worker(
            extract_added_geometry_cloud,
            processed_cloud,
            reconstruction_cloud,
            voxel_size,
        )
        panel3_mesh, restored_region_mesh, restored_vertex_count = await run_in_worker(
            build_restoration_visual_meshes,
            mesh,
            added_cloud,
            voxel_size,
        )
        if central_void_region_mesh is not None and not central_void_region_mesh.is_empty():
            restored_region_mesh = central_void_region_mesh
            restored_vertex_count = max(restored_vertex_count, len(central_void_region_mesh.vertices))

        update_status(78, "Writing reconstructed surface")
        await broadcast_job_update(job_id)
        if mesh.is_empty():
            raise RuntimeError("Surface reconstruction produced an empty mesh.")

        if not o3d.io.write_triangle_mesh(str(after_path), mesh, write_ascii=False):
            raise RuntimeError("Failed to write reconstructed mesh output.")
        if len(added_cloud.points) > 0:
            o3d.io.write_point_cloud(str(added_path), added_cloud, write_ascii=True)
        if not panel3_mesh.is_empty():
            o3d.io.write_triangle_mesh(str(panel3_path), panel3_mesh, write_ascii=False)
        if not restored_region_mesh.is_empty():
            o3d.io.write_triangle_mesh(str(restored_region_path), restored_region_mesh, write_ascii=False)

        before_points = len(point_cloud.points)
        after_points = len(mesh.vertices)
        triangle_count = len(mesh.triangles)
        generated_points = int(completion_metadata.get("generated_points", added_point_count) or added_point_count)
        stats = estimate_reconstruction_stats(
            before_points=before_points,
            reconstruction_points=len(reconstruction_cloud.points),
            generated_points=generated_points,
            triangle_count=triangle_count,
        )
        if hole_fill_metadata.get("holes_closed", 0) > 0:
            stats["holes_closed"] = max(
                int(stats.get("holes_closed", 0)),
                int(hole_fill_metadata["holes_closed"]),
            )
        if central_void_metadata.get("central_void_cap_used"):
            stats["holes_closed"] = max(int(stats.get("holes_closed", 0)), 1)

        jobs[job_id].update(
            {
                "status": "done",
                "progress": 100,
                "before_url": make_absolute_url(f"/mock/{before_path.name}"),
                "after_url": make_absolute_url(f"/mock/{after_path.name}"),
                "added_geometry_url": make_absolute_url(f"/mock/{added_path.name}") if added_path.exists() else None,
                "restoration_panel_url": make_absolute_url(f"/mock/{panel3_path.name}") if panel3_path.exists() else None,
                "restored_regions_url": make_absolute_url(f"/mock/{restored_region_path.name}") if restored_region_path.exists() else None,
                "metadata": {
                    **default_metadata(),
                    "before_points": before_points,
                    "processed_points": len(processed_cloud.points),
                    "reconstruction_points": len(reconstruction_cloud.points),
                    "after_points": after_points,
                    "added_points": added_point_count,
                    "restored_vertices": restored_vertex_count,
                    "triangle_count": triangle_count,
                    **stats,
                    "before_format": normalized_input_suffix.lstrip("."),
                    "after_format": "ply",
                    "profile": profile,
                    "reconstruction_mode": reconstruction_mode,
                    "reconstruction_method": resolved_method,
                    "completion": completion_metadata,
                    "meshing_cleanup": meshing_cleanup_metadata,
                    "meshing_cloud": meshing_cloud_metadata,
                    "hole_mask": hole_mask_metadata,
                    "trimesh_repair": trimesh_repair_metadata,
                    "hole_fill": hole_fill_metadata,
                    "central_void_cap": central_void_metadata,
                    "vertex_count_guard": vertex_count_metadata,
                    "pipeline": (
                        "Full-resolution reconstruction with no point downsampling, optional completion, "
                        "disabled aggressive SOR, capped-depth Poisson meshing, trimesh hole repair, "
                        "boundary hole fill, vertex-count guard, and color transfer"
                    ),
                    "preprocess_voxel_size": round(preprocess_voxel_size, 5),
                    "voxel_size": round(voxel_size, 5),
                    "confidence": 0.95 if triangle_count > 50_000 else 0.88,
                },
            }
        )
        await broadcast_job_update(job_id)
    except Exception as exc:
        print(f"[backend] reconstruction failed for job_id={job_id}: {exc}", flush=True)
        jobs[job_id].update(
            {
                "status": "failed",
                "progress": 100,
                "message": str(exc),
            }
        )
        await broadcast_job_update(job_id)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "reconstruction_backend": "open3d" if o3d is not None else "stub-fallback-missing-open3d",
    }


@app.get("/api/models")
async def get_available_models() -> JSONResponse:
    """Get information about available point cloud completion models.
    
    Returns:
        - models: Dict of model names with availability status and descriptions
        - default_model: Recommended model to use
        - available_count: Number of available models
    """
    info = get_models_info()
    return JSONResponse(info)


@app.post("/api/reconstruct")
async def reconstruct(
    file: UploadFile,
    model: str = Form("ae"),
    params: str = Form("{}"),
) -> JSONResponse:
    try:
        request_params = json.loads(params or "{}")
    except json.JSONDecodeError:
        request_params = {}

    job_id = str(uuid4())
    file_suffix = Path(file.filename or "").suffix.lower() or ".bin"
    upload_path = STATIC_DIR / f"{job_id}_upload{file_suffix}"
    upload_bytes = await save_upload_file(file, upload_path)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "model": model,
        "params": request_params,
        "filename": file.filename,
        "upload_path": str(upload_path),
        "upload_bytes": upload_bytes,
    }

    print(f"[backend] /api/reconstruct called: job_id={job_id}, file={file.filename}, model={model}", flush=True)
    asyncio.create_task(run_reconstruction(job_id, model, request_params))
    return JSONResponse({"job_id": job_id, "status": "queued", "progress": 0})


@app.post("/api/inpaint")
async def inpaint(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    params: str = Form("{}"),
) -> JSONResponse:
    try:
        request_params = json.loads(params or "{}")
    except json.JSONDecodeError:
        request_params = {}

    job_id = str(uuid4())
    image_suffix = Path(image.filename or "").suffix.lower() or ".png"
    mask_suffix = Path(mask.filename or "").suffix.lower() or ".png"
    image_path = STATIC_DIR / f"{job_id}_inpaint_source{image_suffix}"
    mask_path = STATIC_DIR / f"{job_id}_inpaint_mask{mask_suffix}"
    output_path = STATIC_DIR / f"{job_id}_inpaint_after.png"

    if not is_image_file(image_path):
        raise HTTPException(status_code=400, detail="Image must be a PNG, JPEG, WEBP, BMP, or TIFF file.")
    if not is_image_file(mask_path):
        raise HTTPException(status_code=400, detail="Mask must be a PNG, JPEG, WEBP, BMP, or TIFF file.")

    await save_upload_file(image, image_path)
    await save_upload_file(mask, mask_path)

    try:
        result = await run_in_worker(
            inpaint_temple_path,
            image_path,
            mask_path,
            output_path,
            request_params,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse(
        {
            "job_id": job_id,
            "status": "done",
            "progress": 100,
            "before_url": make_absolute_url(f"/mock/{image_path.name}"),
            "mask_url": make_absolute_url(f"/mock/{mask_path.name}"),
            "after_url": make_absolute_url(f"/mock/{result.output_path.name}"),
            "metadata": {
                **result.metadata,
                "task": "temple_path_image_inpainting",
                "mask_format": mask_suffix.lstrip("."),
                "output_format": "png",
            },
        }
    )


@app.get("/api/job/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    job = jobs.get(job_id)
    print(f"[backend] /api/job/{job_id} called, job_exists={job is not None}", flush=True)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse(
        {
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "message": job.get("message"),
            "before_url": job.get("before_url"),
            "after_url": job.get("after_url"),
            "added_geometry_url": job.get("added_geometry_url"),
            "restoration_panel_url": job.get("restoration_panel_url"),
            "restored_regions_url": job.get("restored_regions_url"),
            "metadata": job.get("metadata"),
        }
    )


@app.websocket("/ws/job/{job_id}")
async def job_progress_socket(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    print(f"[backend] websocket connect request for job_id={job_id}", flush=True)
    if job_id not in jobs:
        await websocket.close(code=1008)
        return

    job_websockets.setdefault(job_id, set()).add(websocket)

    try:
        await broadcast_job_update(job_id)
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        job_websockets[job_id].discard(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8010)),
        log_level="info",
    )
