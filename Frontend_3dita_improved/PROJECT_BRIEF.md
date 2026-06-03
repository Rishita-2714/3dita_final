# 3DITA Temple Reconstruction

## Full Project Brief

## 1. Project Overview

This project is an interactive heritage reconstruction system focused on Indian temple geometry. It accepts temple scan data in `.txt`, `.ply`, or `.obj` form, processes the geometry through a reconstruction backend, and presents the result in a web-based 3D viewer.

The codebase started as a React + Vite frontend connected to a FastAPI backend stub. Over the course of the work completed so far, the project evolved from a demo-grade point-cloud viewer into a practical reconstruction workflow with:

- attribute-preserving point-cloud ingestion
- support for large temple annotation files
- Open3D-based surface reconstruction
- color-preserving mesh output
- quality profiles for fast preview vs higher-fidelity output
- a viewer that can render both point clouds and reconstructed triangle meshes

The current system is best described as a geometry-first reconstruction pipeline for temple scans rather than a generic AI image demo.

## 2. What We Built

### Frontend

The frontend lives in [frontend](./frontend) and is built with:

- `React 18`
- `Vite`
- `Three.js`
- `@react-three/fiber`
- `@react-three/drei`
- `framer-motion`

The frontend is responsible for:

- presenting the landing interface
- collecting upload and reconstruction settings
- sending geometry to the backend
- listening for job progress over WebSocket and polling fallback
- visualizing the original input and reconstructed output in 3D
- displaying metadata such as point counts, triangle counts, and confidence

Key frontend files:

- [frontend/src/main.jsx](./frontend/src/main.jsx)
- [frontend/src/App.jsx](./frontend/src/App.jsx)
- [frontend/src/utils/api.js](./frontend/src/utils/api.js)
- [frontend/src/components/UploadDialog.jsx](./frontend/src/components/UploadDialog.jsx)
- [frontend/src/components/ModelViewer.jsx](./frontend/src/components/ModelViewer.jsx)
- [frontend/src/hooks/useModelLoader.js](./frontend/src/hooks/useModelLoader.js)
- [frontend/src/components/ResultViewer.jsx](./frontend/src/components/ResultViewer.jsx)

### Backend

The backend lives in [backend](./backend) and is built with:

- `FastAPI`
- `Uvicorn`
- `Open3D`
- `NumPy`

The backend is responsible for:

- receiving large geometry uploads
- normalizing raw `.txt` temple annotation files into valid `.ply`
- streaming big uploads safely to disk
- loading point clouds and OBJ meshes
- denoising and downsampling large scans
- estimating and orienting normals
- reconstructing a surface mesh using Poisson reconstruction
- transferring scan colors to reconstructed geometry
- simplifying and exporting the final reconstructed mesh
- exposing job progress and final outputs through REST and WebSocket interfaces

Key backend files:

- [backend/main.py](./backend/main.py)
- [backend/requirements.txt](./backend/requirements.txt)

## 3. Architecture

### High-Level Architecture

The system is split into two services:

1. Frontend service
   - Vite dev server
   - browser-based UI
   - 3D result visualization

2. Backend service
   - FastAPI application
   - file normalization and geometry processing
   - asynchronous reconstruction jobs
   - static file serving for generated outputs

### Entry Points

Frontend:

- [frontend/index.html](./frontend/index.html)
- [frontend/src/main.jsx](./frontend/src/main.jsx)
- [frontend/src/App.jsx](./frontend/src/App.jsx)

Backend:

- [backend/main.py](./backend/main.py)
- `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8010`

### Runtime Flow

1. The user opens the landing page and clicks the reconstruction CTA.
2. [UploadDialog.jsx](./frontend/src/components/UploadDialog.jsx) accepts `.txt`, `.ply`, or `.obj` geometry.
3. The frontend sends the file and selected quality profile to `POST /api/reconstruct`.
4. The backend stores the upload on disk and creates a job record.
5. If the file is `.txt`, the backend converts it to `.ply` while preserving geometry and color attributes.
6. The backend loads the point cloud or sampled OBJ geometry via Open3D.
7. The backend preprocesses the point cloud:
   - remove non-finite points
   - voxel downsample
   - statistical outlier removal
   - normal estimation
   - normal orientation
8. The backend reconstructs a triangle surface using Poisson reconstruction.
9. The backend trims low-density regions, simplifies the mesh, computes normals, and transfers vertex colors.
10. The backend writes output files to `backend/static/mock`.
11. The frontend receives job completion metadata and URLs.
12. [ModelViewer.jsx](./frontend/src/components/ModelViewer.jsx) displays:
   - the original input as a point cloud or source geometry
   - the reconstructed result as a mesh if one exists

## 4. Frontend Structure

### App Orchestration

[frontend/src/App.jsx](./frontend/src/App.jsx) acts as a compact application state machine with three main states:

- `idle`
- `processing`
- `result`

Its responsibilities are:

- open/close the upload dialog
- trigger reconstruction
- switch between landing screen, overlay, and result view
- show toast success/error feedback

### Upload Path

[frontend/src/components/UploadDialog.jsx](./frontend/src/components/UploadDialog.jsx) implements:

- file intake through `react-dropzone`
- model/profile selection
- quality parameter control through a `detail` slider

The current profiles are:

- `hq`: best surface quality
- `balanced`: quality/speed tradeoff
- `preview`: faster iteration

### API Client

[frontend/src/utils/api.js](./frontend/src/utils/api.js) provides the transport layer:

- `POST /api/reconstruct`
- `WS /ws/job/{job_id}`
- fallback `GET /api/job/{job_id}`

Important behavior:

- WebSocket progress timeout is extended to support real reconstruction jobs
- polling fallback exists if the socket path fails
- the frontend can tolerate either immediate-return or queued-job backends

### Model Loading and Rendering

[frontend/src/hooks/useModelLoader.js](./frontend/src/hooks/useModelLoader.js) is responsible for loading:

- `.ply`
- `.obj`
- `.txt`

The loader:

- reads vertex colors from TXT where available
- detects whether loaded geometry is a mesh or point cloud
- avoids subsampling meshes unnecessarily
- subsamples only point clouds when needed

[frontend/src/components/ModelViewer.jsx](./frontend/src/components/ModelViewer.jsx) then renders:

- point clouds via `pointsMaterial`
- reconstructed meshes via `meshStandardMaterial`

This distinction is important because it lets the UI render reconstructed surfaces as proper shaded geometry instead of only colored dots.

## 5. Backend Structure

The backend is currently concentrated in [backend/main.py](./backend/main.py). While this is still a monolithic file, the internal responsibilities are now much clearer than they were at the start.

### Main Backend Responsibilities

1. File normalization
2. Upload streaming
3. Point-cloud loading
4. Point-cloud preprocessing
5. Surface reconstruction
6. Job progress and status reporting
7. Static output serving

### Important Backend Functions

Normalization and parsing:

- `parse_ascii_ply_vertices`
- `infer_txt_ply_properties`
- `normalize_txt_parts`
- `txt_points_to_ply`
- `txt_file_to_ply_file`
- `save_upload_file`

Geometry processing:

- `load_point_cloud`
- `preprocess_point_cloud`
- `transfer_vertex_colors`
- `reconstruct_surface_mesh`

Job handling:

- `broadcast_job_update`
- `run_reconstruction`
- `reconstruct`
- `get_job`
- `job_progress_socket`

## 6. Reconstruction Pipeline

The current reconstruction pipeline is the technical heart of the project.

### Input Normalization

Temple dataset TXT files are not treated as plain XYZ only. The backend now preserves richer point attributes wherever possible, including:

- `x y z`
- `r g b`
- extra scalar attributes
- `nx ny nz` if present

This is a major improvement over common quick demos that immediately discard color and auxiliary attributes.

### Large File Handling

One of the major engineering improvements made during this work is large-file robustness.

Earlier behavior:

- read the full upload into RAM
- convert full TXT to full PLY in memory
- keep full geometry bytes inside job state

Current behavior:

- stream uploads to disk in chunks
- convert large TXT files to PLY on disk
- reconstruct from file paths instead of giant in-memory blobs

This change matters for real temple scans such as:

- `Shikhara_1.txt` at about `292,066,172` bytes

### Geometry Preprocessing

The backend uses Open3D preprocessing before meshing:

- remove non-finite points
- adaptive voxel downsampling
- statistical outlier removal
- normal estimation
- normal orientation

This is important because real temple datasets are large, noisy, and unevenly sampled. Direct surface reconstruction without cleanup generally produces fragile or noisy geometry.

### Surface Reconstruction

The current reconstruction method is:

- Poisson surface reconstruction

This method is practical for cultural heritage point clouds because it:

- creates continuous surfaces from dense point sets
- works well when normals are estimated correctly
- produces significantly more realistic output than raw point-only rendering

### Post-Processing

After reconstruction, the pipeline:

- removes low-density mesh regions
- crops to a padded point-cloud bounding box
- removes duplicated and degenerate elements
- simplifies oversized meshes with quadric decimation
- recomputes vertex normals
- transfers source colors to reconstructed vertices

This creates a more stable, cleaner, and more visually usable output for the frontend.

## 7. What Distinguishes Our Approach

This project is distinct from common reconstruction demos in several ways.

### 1. Geometry-First Instead of Image-First

Many common “AI reconstruction” demos are image-based or presentation-first. This project is grounded in 3D geometry and actual temple point-cloud data.

That means:

- the input is real spatial data
- the output is real 3D geometry
- the viewer is not simulating realism through screenshots or prebuilt assets

### 2. Attribute Preservation

Common quick implementations throw away everything except `x y z`.

Our approach preserves:

- color channels
- normals when available
- extra scalar fields

That directly improves realism and faithfulness to the source dataset.

### 3. Surface Reconstruction Instead of Only Point Display

A common baseline is:

- render a sparse point cloud
- recolor it
- call it reconstruction

Our current system reconstructs a real triangle mesh and displays it as a shaded 3D surface. This is a meaningful jump in output quality.

### 4. Large Heritage Scan Awareness

Many examples are built around tiny test assets.

Our pipeline has been adjusted specifically for large temple datasets by:

- streaming uploads
- using disk-based normalization
- adapting voxel size based on scan scale and point count
- providing `preview`, `balanced`, and `hq` profiles

### 5. Practical Engineering Over Hype

Instead of pretending a generic “AI model” can instantly produce photoreal temple geometry, the project uses a realistic stack:

- sound file normalization
- real point-cloud processing
- well-established geometry algorithms
- meaningful visualization improvements

This makes the system more honest and more useful.

## 8. Effectiveness So Far

### What Works Well

The current approach is effective in several important ways:

- it accepts real temple scan files
- it preserves scan color much better than the initial implementation
- it converts point clouds into actual surfaces
- it handles multiple geometry formats
- it scales better to large inputs than the original memory-heavy pipeline
- it provides visible quality levels to the user

### Observed Practical Result

During local smoke testing on the real `Shikhara_1.txt` dataset in `preview` mode, the pipeline processed:

- input points: about `4,447,111`
- processed points: about `52,895`
- reconstructed mesh vertices: about `69,455`
- reconstructed triangles: about `137,959`

This shows that the system can reduce a massive raw scan into a manageable colored surface representation for interactive visualization.

### Why This Is Effective

The effectiveness comes from using the right level of abstraction:

- keep enough source information to remain faithful
- reduce density enough to become computationally tractable
- reconstruct a surface instead of only plotting points
- preserve color so the result still looks tied to the original scan

This is far more effective than either:

- raw sparse point viewing
- or fake “AI output” without actual geometry processing

## 9. Current Limitations

Even with the improvements, there are still real constraints.

### 1. Not Fully Photoreal

The system reconstructs geometry and preserves point-derived color, but it does not yet do:

- texture baking
- UV generation
- image-based texturing
- neural radiance field rendering

So the result can look like a faithful colored scan surface, but not like a DSLR photograph of a temple.

### 2. Heavy HQ Jobs

For very large temple scans, `hq` is still computationally expensive.

That means:

- high memory pressure is still possible
- processing can take noticeably longer
- running several large jobs simultaneously is not ideal

### 3. Monolithic Backend File

[backend/main.py](./backend/main.py) now contains a much more capable system, but it is still structurally dense. Over time, it should likely be split into:

- ingestion
- preprocessing
- reconstruction
- transport/API
- job orchestration

### 4. No Dedicated Queue Yet

The backend currently starts jobs asynchronously, but there is no explicit concurrency limiter or persistent queue. This can be risky for multiple simultaneous heavy uploads.

## 10. Why The Approach Is Better Than The Common One

Compared to a common reconstruction UI that simply uploads a file and renders a sparse, recolored point cloud, this system is better because it:

- preserves more of the original dataset
- uses actual geometric reconstruction
- supports large-file processing more safely
- adapts quality based on user intent
- outputs a mesh that is structurally more informative than a cloud of points
- remains inspectable and debuggable as an engineering system

In short:

- common approach: quick visualization
- our approach: practical heritage geometry reconstruction pipeline

## 11. Build and Run Process

### Backend

Install:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Run:

```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

Dependencies are declared in [backend/requirements.txt](./backend/requirements.txt):

- `fastapi`
- `uvicorn`
- `python-multipart`
- `numpy`
- `open3d`

### Frontend

Install:

```powershell
cd frontend
npm install
```

Run:

```powershell
npm run dev
```

Build:

```powershell
npm run build
```

Frontend dependencies are declared in [frontend/package.json](./frontend/package.json).

## 12. Recommended Usage Pattern

For best stability and iteration speed:

1. Start with `preview` on a large scan
2. Move to `balanced` if the geometry looks promising
3. Use `hq` only when you want the best surface result and are willing to wait longer
4. Run one large reconstruction job at a time

This workflow gives a better balance between speed and quality than jumping directly to the heaviest mode for every file.

## 13. Future Improvement Opportunities

The next strong upgrades would be:

- add a real backend job queue with concurrency control
- persist job state beyond process memory
- add mesh export in more formats such as `.glb`
- implement texture baking or texture transfer
- support better progress reporting by stage
- introduce adaptive reconstruction strategies per temple component
- split backend modules for maintainability
- add artifact cleanup for stale generated files

If the goal becomes "make it look even closer to the real temple object," the strongest next step is likely:

- textured mesh generation or mesh-to-GLB export with better material handling

## 14. Final Summary

This project is no longer just a temple-themed interface around a stub. It is now a real 3D reconstruction workflow for temple scan data with:

- a React frontend for guided interaction
- a FastAPI backend for asynchronous jobs
- streamed large-file handling
- attribute-aware TXT ingestion
- Open3D-based point-cloud cleaning
- Poisson surface reconstruction
- color-preserving reconstructed meshes
- interactive mesh/point-cloud visualization

Its strongest distinguishing qualities are:

- fidelity to actual temple scan data
- practical handling of large geometry files
- real geometric reconstruction instead of visual imitation
- a workflow shaped around heritage scan constraints rather than generic AI demo patterns

Within the current architecture, the approach is effective, technically grounded, and meaningfully better than the common “upload and show sparse points” pattern.
