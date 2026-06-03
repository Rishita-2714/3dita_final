# 📋 Quick Reference - Model Selection & Setup

## File Structure Changes

```
Frontend_3dita/
├── GRNET_SETUP.md ✨                    # Setup guide
├── IMPLEMENTATION_SUMMARY.md ✨         # What was added
│
├── backend/
│   ├── main.py (MODIFIED)               # Added /api/models endpoint
│   ├── requirements.txt
│   ├── .env.grnet.example ✨            # GRNet config template
│   ├── .env.auto.example ✨             # Auto-selection template
│   ├── .env.pointr.example ✨           # PointR config template
│   │
│   └── completion/
│       ├── __init__.py (MODIFIED)       # Exports GRNetAdapter
│       ├── runtime.py (MODIFIED)        # Multi-model support
│       ├── pointr_adapter.py            # Existing PointR adapter
│       ├── grnet_adapter.py ✨          # NEW: GRNet adapter
│       ├── model_info.py ✨             # NEW: Model info utilities
│       ├── merge.py
│       └── MODELS.md ✨                 # Detailed model guide
│
└── frontend/
    └── src/
        └── utils/
            ├── api.js
            └── modelSelection.js ✨     # NEW: Frontend model utilities
```

---

## 🔄 Workflow: From Upload to Result

```
User Uploads File
    ↓
Frontend Calls GET /api/models
    ↓ (optional - to show available models)
Backend Returns: {models: {...}, default: "grnet"}
    ↓
Frontend Calls POST /api/reconstruct
    ├─ file: temple_scan.ply
    ├─ reconstruction_mode: "dl_completion"
    ├─ completion_model: "grnet" ← (or "auto", "pointr")
    └─ profile: "hq"
    ↓
Backend: runtime.py/_select_completion_model()
    ├─ Check if model requested is available
    ├─ If "auto": try GRNet → fall back to PointR
    └─ Select appropriate adapter
    ↓
Backend: Selected Adapter (GRNetAdapter or PoinTrAdapter)
    ├─ Prepare input (downsample to 2048 points)
    ├─ Run inference (via subprocess)
    └─ Return completed point cloud
    ↓
Backend: merge.py
    ├─ Merge original + generated points
    └─ Apply Open3D surface reconstruction
    ↓
Backend Returns to Frontend:
    {
      "before_url": "...",
      "after_url": "...",
      "metadata": {
        "completion_model": "grnet",
        "completion_used": true,
        "generated_points": 4250,
        ...
      }
    }
    ↓
Frontend: Display Results
```

---

## ✅ Setup Checklist

### Phase 1: Preparation (No Changes to Code)
- [ ] Download GRNet: `git clone https://github.com/luckyddog/GRNet.git`
- [ ] Create Python environment: `python -m venv grnet_env`
- [ ] Activate environment: `grnet_env\Scripts\activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Download pretrained checkpoint (from GRNet releases)

### Phase 2: Configuration
- [ ] Copy `.env.grnet.example` → `.env` in backend/
- [ ] Update paths in `.env`:
  - `GRNET_PYTHON_BIN`: Point to `grnet_env/Scripts/python.exe`
  - `GRNET_REPO_PATH`: Point to GRNet directory
  - `GRNET_CHECKPOINT_PATH`: Point to model checkpoint
- [ ] Verify paths exist:
  ```bash
  dir C:\path\to\GRNet
  dir C:\path\to\GRNet\cfgs\config.yaml
  dir C:\path\to\GRNet\checkpoints\grnet_best.pth
  ```

### Phase 3: Testing
- [ ] Start backend: `cd backend && python main.py`
- [ ] Test models endpoint: `curl http://localhost:8010/api/models`
- [ ] Verify response shows both models available
- [ ] Upload a small test file and verify reconstruction

### Phase 4: Deployment
- [ ] Set environment variables in production
- [ ] Test with real temple scan data
- [ ] Monitor GPU/CPU usage and adjust configuration if needed

---

## 🎛️ Configuration Profiles

### For Maximum Quality (Research/Archive)
```bash
COMPLETION_MODEL=grnet
GRNET_DEVICE=cuda:0
GRNET_INPUT_POINTS=2048
profile=hq
```
⏱️ Time: 3-5 seconds | 🎨 Quality: ⭐⭐⭐⭐⭐

### For Production (Balanced)
```bash
COMPLETION_MODEL=auto
GRNET_INPUT_POINTS=1024  (or use PointR for speed)
profile=balanced
```
⏱️ Time: 1-2 seconds | 🎨 Quality: ⭐⭐⭐⭐

### For Preview (Fast)
```bash
COMPLETION_MODEL=pointr
POINTR_INPUT_POINTS=512
profile=fast
```
⏱️ Time: 0.5-1 second | 🎨 Quality: ⭐⭐⭐

---

## 🔌 API Quick Reference

### Check Available Models
```bash
GET /api/models
```
**Response:** Models info + default selection

### Request Reconstruction
```bash
POST /api/reconstruct
  - file: <temple_scan>
  - reconstruction_mode: "dl_completion"
  - completion_model: "auto" | "grnet" | "pointr"
  - profile: "hq" | "balanced" | "fast"
```

**Response Metadata Includes:**
- `completion_model`: Which model was used
- `completion_input_points`: Input size
- `completion_output_points`: Output size
- `completion_device`: GPU/CPU used
- `generated_points`: New points added

---

## 🚨 Common Issues & Quick Fixes

| Issue | Solution |
|-------|----------|
| "GRNet not available" | Check env vars point to real paths |
| CUDA out of memory | Reduce `GRNET_INPUT_POINTS` to 1024 |
| Model falling back to PointR | GRNet dependencies missing - check Python env |
| Slow inference | Use `GRNET_INPUT_POINTS=1024` instead of 2048 |
| "No models available" | Verify both models configured correctly |
| Import errors | Reinstall requirements: `pip install -r requirements.txt` |

---

## 📊 Metrics to Monitor

After each reconstruction, check:

```json
{
  "metadata": {
    "completion_model": "grnet",              // ← Which model
    "completion_device": "cuda:0",            // ← GPU used
    "completion_input_points": 2048,          // ← Input
    "completion_output_points": 18750,        // ← Output
    "generated_points": 4250,                 // ← Quality measure
    "merged_points": 20630,                   // ← Final total
    "completion_status": "local-inference"    // ← Status
  }
}
```

**Interpretation:**
- Higher `generated_points` / `merged_points` = More detail added
- `completion_device: cuda:0` = GPU accelerated (good)
- `completion_model: grnet` = Using better model (optimal)

---

## 🔧 Environment Variable Reference

### GRNet Variables
```bash
GRNET_DEVICE                # GPU: "cuda:0", "cuda:1", "cpu"
GRNET_INPUT_POINTS          # Integer: 512, 1024, 2048, 4096
GRNET_PYTHON_BIN            # Path to Python in grnet_env
GRNET_REPO_PATH             # Path to cloned GRNet repo
GRNET_CONFIG_PATH           # Path to config.yaml in GRNet
GRNET_CHECKPOINT_PATH       # Path to model checkpoint file
```

### PointR Variables (Same Pattern)
```bash
POINTR_DEVICE
POINTR_INPUT_POINTS
POINTR_PYTHON_BIN
POINTR_REPO_PATH
POINTR_CONFIG_PATH
POINTR_CHECKPOINT_PATH
```

### Model Selection
```bash
COMPLETION_MODEL            # "auto", "grnet", "pointr"
```

---

## 💡 Pro Tips

1. **Use "auto" mode** - Automatically selects best available
2. **HQ for archival** - Use GRNet with HQ profile for documentation
3. **Balanced for production** - Fast enough and good quality
4. **Monitor GPU** - Use `nvidia-smi` to watch GPU usage
5. **Batch processing** - Both models work in parallel if you have GPUs

---

## 📞 Debugging Commands

```bash
# Check Python environment
python --version
pip list

# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Check GRNet installation
cd GRNet && python -c "import models; print('GRNet OK')"

# Test models endpoint
curl http://localhost:8010/api/models | python -m json.tool

# Check environment variables are set
set GRNET_REPO_PATH  (Windows)
echo $GRNET_REPO_PATH (Linux/Mac)

# Run with verbose output
COMPLETION_MODEL=grnet python main.py
```

---

**Ready to reconstruct! 🏛️**
