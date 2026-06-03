# Point Cloud Completion Models Setup Guide

## Overview

This project now supports multiple point cloud completion models to reconstruct temple geometry:

- **GRNet** (Gated Recurrent Unit Network) - **Recommended** for better quality
- **PointR** - Existing implementation, for backward compatibility

## Model Comparison

| Feature | GRNet | PointR |
|---------|-------|--------|
| **Quality** | High (hierarchical coarse-to-fine) | Medium |
| **Speed** | Medium | Fast |
| **Detail Preservation** | Excellent | Good |
| **Memory Usage** | Moderate | Lower |
| **Best For** | High-fidelity reconstruction | Quick processing |

## Quick Start

### 1. Using GRNet (Recommended)

#### Option A: Clone and Setup GRNet Repository

```bash
# Clone GRNet repository
git clone https://github.com/luckyddog/GRNet.git
cd GRNet

# Create isolated environment
python -m venv grnet_env
source grnet_env/bin/activate  # On Windows: grnet_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# You may need to install torch and torchvision separately
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Download pretrained checkpoint (check GRNet repo for links)
mkdir -p checkpoints
# Download model from official source and place in checkpoints/
```

#### Option B: Using Docker

Create a `Dockerfile` for GRNet:

```dockerfile
FROM pytorch/pytorch:2.0-cuda11.8-runtime-ubuntu22.04

WORKDIR /app
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/luckyddog/GRNet.git .
RUN pip install -r requirements.txt
RUN mkdir -p checkpoints
# ADD path/to/grnet_model.pth checkpoints/

ENTRYPOINT ["python", "tools/inference.py"]
```

### 2. Environment Variables

Set these before running the backend:

```bash
# GRNet Configuration
export GRNET_DEVICE=cuda:0              # or cuda:1, cpu, etc.
export GRNET_INPUT_POINTS=2048          # Input point cloud size
export GRNET_PYTHON_BIN=/path/to/grnet_env/bin/python
export GRNET_REPO_PATH=/path/to/GRNet
export GRNET_CONFIG_PATH=/path/to/GRNet/cfgs/config.yaml
export GRNET_CHECKPOINT_PATH=/path/to/GRNet/checkpoints/model.pth

# Model selection (optional)
export COMPLETION_MODEL=grnet  # or "pointr", "auto" (default)
```

### 3. Backend Initialization

```bash
cd backend
python -m pip install -r requirements.txt

# Run with GRNet enabled
export COMPLETION_MODEL=grnet
python main.py
```

### 4. Frontend API Usage

Send model preference in reconstruction request:

```javascript
const formData = new FormData();
formData.append("input_file", fileBlob);
formData.append("reconstruction_mode", "dl_completion");
formData.append("completion_model", "grnet");  // "pointr" or "auto"
formData.append("profile", "hq");

const response = await fetch("http://localhost:8010/api/reconstruct", {
    method: "POST",
    body: formData
});
```

## Model Details

### GRNet Architecture

GRNet uses:
1. **Feature Extraction**: Extracts global and local features from partial point cloud
2. **Gated Recurrent Unit Decoder**: Multi-layer GRU cells for feature decoding
3. **Coarse-to-Fine Generation**: Generates coarse points, then refines to fine details
4. **Better Shape Preservation**: Maintains structural integrity of temple geometry

### PointR Architecture (Existing)

PointR uses:
1. **Transformer Encoder**: Self-attention on input points
2. **Cross-Attention**: Queries interacting with input features
3. **Iterative Refinement**: Multi-step point generation

## Performance Tips

### For HQ (High-Quality) Profile
```bash
export GRNET_DEVICE=cuda:0
export GRNET_INPUT_POINTS=2048
# Takes ~2-5 seconds per reconstruction
```

### For Balanced Profile
```bash
export GRNET_INPUT_POINTS=1024
# Takes ~1-2 seconds per reconstruction
```

### For Fast Profile
```bash
export COMPLETION_MODEL=pointr  # Use faster model
export GRNET_INPUT_POINTS=512
# Takes ~0.5-1 second per reconstruction
```

## Troubleshooting

### GRNet not available
- Check `GRNET_REPO_PATH` points to valid GRNet clone
- Verify checkpoint file exists at `GRNET_CHECKPOINT_PATH`
- Check Python environment has all dependencies

### Falling back to PointR
The system automatically falls back to PointR if GRNet is unavailable:
```bash
export COMPLETION_MODEL=auto  # Tries GRNet first, then PointR
```

### CUDA Out of Memory
- Reduce `GRNET_INPUT_POINTS` (default 2048 → try 1024)
- Use CPU: `export GRNET_DEVICE=cpu`
- Use smaller batch sizes

### No Models Available
- Ensure at least one model (GRNet or PointR) is properly configured
- Check all required paths and checkpoints exist
- Verify Python dependencies installed

## Adding Custom Models

To add a new model (e.g., PCN, VRCNet):

1. Create adapter file: `backend/completion/custommodel_adapter.py`
2. Implement following `GRNetAdapter` pattern
3. Update `runtime.py` to register new model
4. Set environment variables for your model

## API Response

Response includes model information:

```json
{
  "metadata": {
    "completion_mode": "dl_completion",
    "completion_model": "grnet",
    "completion_used": true,
    "completion_status": "local-inference",
    "completion_device": "cuda:0",
    "completion_input_points": 2048,
    "completion_output_points": 16384,
    "generated_points": 4250,
    "merged_points": 20630
  }
}
```

## Resources

- [GRNet GitHub](https://github.com/luckyddog/GRNet)
- [PointR GitHub](https://github.com/yuxumin/PoinTr)
- [Point Cloud Completion Survey](https://arxiv.org/abs/2010.07466)
