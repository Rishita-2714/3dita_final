"""Model availability checker utility."""

from typing import Dict, Any
from .pointr_adapter import PoinTrAdapter
from .grnet_adapter import GRNetAdapter


def get_available_models() -> Dict[str, Any]:
    """Check which completion models are available and configured.
    
    Returns:
        Dict with model availability status and metadata
    """
    models = {}
    
    # Check PointR
    pointr = PoinTrAdapter()
    models["pointr"] = {
        "available": pointr.is_available(),
        "reason": pointr.availability_reason() if not pointr.is_available() else "available",
        "description": "PointR - Transformer-based point completion network"
    }
    
    # Check GRNet
    grnet = GRNetAdapter()
    models["grnet"] = {
        "available": grnet.is_available(),
        "reason": grnet.availability_reason() if not grnet.is_available() else "available",
        "description": "GRNet - Gated Recurrent Unit point cloud completion (recommended)"
    }
    
    return models


def get_default_model() -> str:
    """Get the default model selection based on availability.
    
    Returns:
        Model name ("grnet", "pointr", or "none")
    """
    models = get_available_models()
    
    # Prefer GRNet for quality
    if models["grnet"]["available"]:
        return "grnet"
    # Fall back to PointR
    if models["pointr"]["available"]:
        return "pointr"
    # No models available
    return "none"


def get_models_info() -> Dict[str, Any]:
    """Get comprehensive information about available models.
    
    Returns:
        Dict with availability and default selection
    """
    available_models = get_available_models()
    default = get_default_model()
    
    return {
        "models": available_models,
        "default_model": default,
        "available_count": sum(1 for m in available_models.values() if m["available"])
    }
