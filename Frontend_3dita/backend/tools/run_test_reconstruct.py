import sys
import traceback
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (
    load_point_cloud,
    preprocess_point_cloud,
    complete_point_cloud,
    reconstruct_surface_mesh,
)

import open3d as o3d


def run_test(source_path: Path, profile: str = "hq"):
    print(f"Loading source: {source_path}")
    pc = load_point_cloud(source_path)
    print(f"Input points: {len(pc.points)}")

    processed, voxel = preprocess_point_cloud(pc, profile)
    print(f"Processed points: {len(processed.points)}, voxel_size={voxel}")

    # Use dl_completion so local fallback runs for geometry-only cases
    completed_cloud, metadata = complete_point_cloud(processed, "dl_completion", profile, {})
    print("Completion metadata:")
    print(json.dumps(metadata, indent=2))
    print(f"Completed points: {len(completed_cloud.points) if completed_cloud else 0}")

    mesh, meshing_cloud, voxel_size, method = reconstruct_surface_mesh(
        completed_cloud, pc, "poisson", profile, {}
    )

    print(f"Mesh vertices: {len(mesh.vertices)}, triangles: {len(mesh.triangles)}, method: {method}")

    out_path = source_path.parent / (source_path.stem + "_test_after.ply")
    o3d.io.write_triangle_mesh(str(out_path), mesh, write_ascii=False)
    print(f"Wrote mesh to: {out_path}")


if __name__ == "__main__":
    try:
        default = Path(__file__).resolve().parents[1] / "static" / "mock" / "e377931a-55d0-4031-a341-38cad59dd229_source.ply"
        source = Path(sys.argv[1]) if len(sys.argv) > 1 else default
        if not source.exists():
            print("Source file not found:", source)
            sys.exit(2)
        run_test(source)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
