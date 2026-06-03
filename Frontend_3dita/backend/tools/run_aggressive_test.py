import sys
import traceback
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as main_mod
from main import (
    load_point_cloud,
    preprocess_point_cloud,
    complete_point_cloud,
    reconstruct_with_poisson,
    reconstruct_with_ball_pivoting,
    reconstruct_with_alpha_shape,
)

import open3d as o3d


def run_aggressive(source_path: Path, profile: str = "hq"):
    print(f"Source: {source_path}")
    pc = load_point_cloud(source_path)
    print(f"Input points: {len(pc.points)}")

    # Increase preprocess target to keep more points for HQ
    main_mod.MAX_PREPROCESS_POINTS["hq"] = max(300000, main_mod.MAX_PREPROCESS_POINTS.get("hq", 180000))
    print(f"MAX_PREPROCESS_POINTS[hq] set to {main_mod.MAX_PREPROCESS_POINTS['hq']}")

    processed, voxel = preprocess_point_cloud(pc, profile)
    print(f"Processed points: {len(processed.points)}, voxel_size={voxel}")

    completed_cloud, metadata = complete_point_cloud(processed, "dl_completion", profile, {"detail":11})
    print("Completion metadata:")
    print(json.dumps(metadata, indent=2))
    print(f"Completed points: {len(completed_cloud.points) if completed_cloud else 0}")

    # Run Poisson
    try:
        mesh_poisson, densities = reconstruct_with_poisson(completed_cloud, profile, {"detail":11}), None
        mesh_poisson = mesh_poisson
    except Exception as e:
        print("Poisson failed:", e)
        mesh_poisson = None

    # Ball Pivoting
    try:
        mesh_bpa = reconstruct_with_ball_pivoting(completed_cloud, voxel)
    except Exception as e:
        print("Ball pivoting failed:", e)
        mesh_bpa = None

    # Alpha shape
    try:
        mesh_alpha = reconstruct_with_alpha_shape(completed_cloud, voxel, profile)
    except Exception as e:
        print("Alpha shape failed:", e)
        mesh_alpha = None

    results = []
    base = source_path.parent
    if mesh_poisson is not None:
        out = base / (source_path.stem + "_aggr_poisson.ply")
        o3d.io.write_triangle_mesh(str(out), mesh_poisson, write_ascii=False)
        results.append(("poisson", len(mesh_poisson.vertices), len(mesh_poisson.triangles), out))
    if mesh_bpa is not None:
        out = base / (source_path.stem + "_aggr_bpa.ply")
        o3d.io.write_triangle_mesh(str(out), mesh_bpa, write_ascii=False)
        results.append(("ball_pivoting", len(mesh_bpa.vertices), len(mesh_bpa.triangles), out))
    if mesh_alpha is not None:
        out = base / (source_path.stem + "_aggr_alpha.ply")
        o3d.io.write_triangle_mesh(str(out), mesh_alpha, write_ascii=False)
        results.append(("alpha_shape", len(mesh_alpha.vertices), len(mesh_alpha.triangles), out))

    for name, v, t, path in results:
        print(f"{name}: vertices={v}, triangles={t}, file={path}")


if __name__ == "__main__":
    try:
        default = Path(__file__).resolve().parents[1] / "static" / "mock" / "e377931a-55d0-4031-a341-38cad59dd229_source.ply"
        source = Path(sys.argv[1]) if len(sys.argv) > 1 else default
        if not source.exists():
            print("Source file not found:", source)
            sys.exit(2)
        run_aggressive(source)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
