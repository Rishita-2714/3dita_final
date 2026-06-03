# 🏗️ Architecture Overview - Multi-Model Point Cloud Completion

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Model Selection UI                                       │   │
│  │ - Display available models from /api/models             │   │
│  │ - Allow user to choose: GRNet, PointR, or Auto          │   │
│  │ - Show recommendations based on profile                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ API Endpoints                                              │ │
│  │ - GET  /api/models          (new!)                        │ │
│  │ - POST /api/reconstruct     (modified)                    │ │
│  │ - GET  /api/job/{job_id}    (existing)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Model Selection Logic (runtime.py)                        │ │
│  │                                                            │ │
│  │  _select_completion_model(model_name)                    │ │
│  │    ├─ If model_name=="auto":                             │ │
│  │    │  ├─ Try GRNet (better quality)                      │ │
│  │    │  └─ Fall back to PointR if unavailable             │ │
│  │    ├─ If model_name=="grnet":                            │ │
│  │    │  └─ Use GRNetAdapter                               │ │
│  │    └─ If model_name=="pointr":                           │ │
│  │       └─ Use PoinTrAdapter                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Model Adapters                                             │ │
│  │                                                            │ │
│  │  ┌──────────────────────┐    ┌──────────────────────┐    │ │
│  │  │  GRNetAdapter (new)  │    │  PoinTrAdapter       │    │ │
│  │  │  ─────────────────   │    │  ──────────────────  │    │ │
│  │  │  • GRU architecture  │    │  • Transformer       │    │ │
│  │  │  • Coarse-to-fine    │    │  • Iterative refine  │    │ │
│  │  │  • Higher quality    │    │  • Good balance      │    │ │
│  │  │  • 3-5 sec per scan  │    │  • 1-2 sec per scan  │    │ │
│  │  └──────────────────────┘    └──────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
│              ↓ (subprocess call to external Python env)         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ External Model Environments (Subprocess)                  │ │
│  │                                                            │ │
│  │  ┌──────────────────────┐    ┌──────────────────────┐    │ │
│  │  │ grnet_env/           │    │ pointr_env/          │    │ │
│  │  │ ├─ Python            │    │ ├─ Python            │    │ │
│  │  │ ├─ PyTorch           │    │ ├─ PyTorch           │    │ │
│  │  │ ├─ GRNet repo        │    │ ├─ PoinTr repo       │    │ │
│  │  │ ├─ Model checkpoint  │    │ ├─ Model checkpoint  │    │ │
│  │  │ └─ inference.py      │    │ └─ inference.py      │    │ │
│  │  └──────────────────────┘    └──────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
│              ↓ (Completed point cloud)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Post-Processing (merge.py + Open3D)                       │ │
│  │                                                            │ │
│  │  Input cloud ──┐                                          │ │
│  │                ├─→ Merge → Denoising → Poisson → Export  │ │
│  │  Generated ────┘                                          │ │
│  │  points                                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Output                                                     │ │
│  │ - Reconstructed mesh (PLY/OBJ)                            │ │
│  │ - Metadata:                                               │ │
│  │   ├─ completion_model: "grnet" | "pointr"               │ │
│  │   ├─ completion_device: "cuda:0" | "cpu"                │ │
│  │   ├─ generated_points: number of new points             │ │
│  │   └─ merged_points: total after merge                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP
                    ┌─────────────────────┐
                    │ Frontend displays   │
                    │ 3D viewer with      │
                    │ before/after result │
                    └─────────────────────┘
```

---

## Module Dependency Graph

```
frontend/
  └─ modelSelection.js
      ├─ getAvailableModels()      → calls GET /api/models
      ├─ getModelDisplayName()     → UI labels
      ├─ getRecommendedModel()     → smart selection
      └─ formatModelInfo()         → display formatting

backend/main.py
  ├─ imports: model_info.py
  ├─ GET /api/models endpoint
  │   └─ calls: get_models_info()
  │
  ├─ POST /api/reconstruct endpoint
  │   └─ calls: complete_point_cloud()
  │
  └─ imports: completion/__init__.py

completion/runtime.py
  ├─ imports: pointr_adapter.py
  ├─ imports: grnet_adapter.py
  ├─ imports: model_info.py
  │
  ├─ _select_completion_model()
  │   ├─ return: GRNetAdapter if available
  │   └─ return: PoinTrAdapter if available
  │
  └─ complete_point_cloud()
      ├─ calls: _select_completion_model()
      ├─ calls: adapter.infer()
      └─ calls: merge_observed_and_completed()

completion/model_info.py
  ├─ get_available_models()
  │   ├─ creates: PoinTrAdapter()
  │   ├─ creates: GRNetAdapter()
  │   └─ returns: {models: {...}}
  │
  ├─ get_default_model()
  │   └─ returns: "grnet" | "pointr" | "none"
  │
  └─ get_models_info()
      └─ aggregates above info

completion/grnet_adapter.py (NEW)
  ├─ class: GRNetAdapter
  ├─ is_available()
  │   └─ checks: repo_path, config, checkpoint
  ├─ infer()
  │   ├─ calls: _prepare_model_input()
  │   └─ calls: _run_local_grnet_inference()
  │       └─ subprocess call to grnet_env/python
  └─ handles: environment variables GRNET_*

completion/pointr_adapter.py (EXISTING)
  ├─ class: PoinTrAdapter
  ├─ is_available()
  │   └─ checks: repo_path, config, checkpoint
  ├─ infer()
  │   ├─ calls: _prepare_model_input()
  │   └─ calls: _run_local_pointr_inference()
  │       └─ subprocess call to pointr_env/python
  └─ handles: environment variables POINTR_*
```

---

## Data Flow for a Single Request

```
1. USER UPLOADS FILE
   ├─ File: temple_scan.ply
   ├─ Mode: dl_completion
   ├─ Model: "auto" (or specific)
   └─ Profile: "hq"

2. FRONTEND REQUEST
   POST /api/reconstruct
   │
   └─ Body:
      ├─ file: <binary PLY data>
      ├─ model: "ae"
      ├─ params: {
      │  "completion_model": "auto",
      │  "profile": "hq",
      │  ...
      │ }

3. BACKEND RECEIVES
   │
   ├─ Validates file
   ├─ Creates job_id
   └─ Queues async job

4. JOB EXECUTION (async)
   │
   ├─ Load input point cloud (Open3D)
   │
   ├─ Call complete_point_cloud()
   │  │
   │  ├─ Select model:
   │  │  └─ runtime._select_completion_model("auto")
   │  │     ├─ GRNetAdapter.is_available() → True
   │  │     └─ Select: GRNetAdapter ✓
   │  │
   │  ├─ Prepare input:
   │  │  └─ adapter._prepare_model_input()
   │  │     └─ Downsample to 2048 points (if needed)
   │  │
   │  ├─ Run inference:
   │  │  └─ adapter._run_local_grnet_inference()
   │  │     ├─ Save points to temp: /tmp/input.npy
   │  │     │
   │  │     ├─ Call subprocess:
   │  │     │  grnet_env/python \
   │  │     │    GRNet/tools/inference.py \
   │  │     │    --pc /tmp/input.npy \
   │  │     │    --device cuda:0 \
   │  │     │    --out_pc_root /tmp/output/
   │  │     │
   │  │     └─ Load result: /tmp/output/fine.npy
   │  │
   │  ├─ Merge results:
   │  │  └─ merge_observed_and_completed()
   │  │     ├─ Combine original + generated points
   │  │     └─ Remove duplicates (radius check)
   │  │
   │  └─ Return metadata:
   │     {
   │       completion_model: "grnet",
   │       completion_device: "cuda:0",
   │       completion_input_points: 2048,
   │       completion_output_points: 18750,
   │       generated_points: 4250,
   │       merged_points: 20630
   │     }
   │
   ├─ Surface reconstruction (Poisson)
   │  └─ Open3D mesh generation
   │
   └─ Export result
      └─ Save to: static/job_id_after.ply

5. BACKEND RETURNS TO FRONTEND
   {
     "job_id": "abc-123",
     "status": "complete",
     "before_url": "/mock/job_id_before.ply",
     "after_url": "/mock/job_id_after.ply",
     "metadata": { ... }
   }

6. FRONTEND DISPLAYS
   ├─ Load before mesh in 3D viewer
   ├─ Load after mesh in 3D viewer
   ├─ Show comparison
   ├─ Display metadata:
   │  "Used: GRNet | Points: 2048→18750 | Generated: 4250"
   └─ Allow rotation/zoom/export
```

---

## Configuration & Environment Setup

```
┌─ Local Machine ─────────────────────────────────┐
│                                                  │
│  ┌─ GRNet Environment ─────────────────────┐   │
│  │ grnet_env/                              │   │
│  │ ├─ Scripts/python.exe                  │   │
│  │ ├─ Lib/site-packages/                  │   │
│  │ │  ├─ torch/                           │   │
│  │ │  ├─ open3d/                          │   │
│  │ │  └─ ...                              │   │
│  │ └─ tools/inference.py (from repo)      │   │
│  │                                         │   │
│  │ Environment Variables:                 │   │
│  │ GRNET_PYTHON_BIN=.../python.exe        │   │
│  │ GRNET_REPO_PATH=C:/path/to/GRNet       │   │
│  │ GRNET_CONFIG_PATH=.../config.yaml      │   │
│  │ GRNET_CHECKPOINT_PATH=.../model.pth    │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌─ PointR Environment ───────────────────┐   │
│  │ pointr_env/                            │   │
│  │ ├─ Scripts/python.exe                  │   │
│  │ ├─ Lib/site-packages/                  │   │
│  │ │  ├─ torch/                           │   │
│  │ │  ├─ open3d/                          │   │
│  │ │  └─ ...                              │   │
│  │ └─ tools/inference.py (from repo)      │   │
│  │                                         │   │
│  │ Environment Variables:                 │   │
│  │ POINTR_PYTHON_BIN=.../python.exe       │   │
│  │ POINTR_REPO_PATH=C:/path/to/PoinTr     │   │
│  │ POINTR_CONFIG_PATH=.../config.yaml     │   │
│  │ POINTR_CHECKPOINT_PATH=.../model.pth   │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌─ Backend Application ──────────────────┐   │
│  │ Backend/.env                           │   │
│  │ ├─ COMPLETION_MODEL=auto               │   │
│  │ ├─ GRNET_DEVICE=cuda:0                 │   │
│  │ ├─ POINTR_DEVICE=cuda:0                │   │
│  │ └─ ... (all above vars)                │   │
│  │                                         │   │
│  │ python main.py                         │   │
│  │ ├─ FastAPI server on :8010             │   │
│  │ ├─ Loads both adapters on startup      │   │
│  │ └─ Checks model availability           │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌─ Frontend Application ─────────────────┐   │
│  │ npm run dev                            │   │
│  │ ├─ Vite dev server on :5173           │   │
│  │ ├─ Connects to backend at :8010       │   │
│  │ ├─ Queries /api/models on init        │   │
│  │ └─ Shows available model options       │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Model Selection Decision Tree

```
User submits reconstruction request
│
├─ completion_model parameter provided?
│  ├─ YES: "grnet"
│  │  └─ Use: GRNetAdapter (must be available)
│  │
│  ├─ YES: "pointr"
│  │  └─ Use: PoinTrAdapter (must be available)
│  │
│  └─ YES: "auto" (or not specified)
│     │
│     └─ Try GRNet first
│        ├─ GRNetAdapter.is_available() → YES
│        │  └─ Use: GRNetAdapter ✓ (better quality)
│        │
│        └─ GRNetAdapter.is_available() → NO
│           │
│           └─ Try PointR next
│              ├─ PoinTrAdapter.is_available() → YES
│              │  └─ Use: PoinTrAdapter ✓ (fallback)
│              │
│              └─ PoinTrAdapter.is_available() → NO
│                 └─ Skip completion, return original points ✗
│
Response includes: which model was actually used
```

---

**Architecture Status: ✅ Complete and Modular**

The system is designed to easily support additional models in the future by following the same adapter pattern!
