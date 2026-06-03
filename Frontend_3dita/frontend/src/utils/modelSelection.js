/**
 * Model selection utility for frontend
 * Handles communication with available reconstruction models
 */

/**
 * Get list of available completion models from backend
 */
export async function getAvailableModels(apiUrl) {
  try {
    const response = await fetch(`${apiUrl}/api/models`);
    if (!response.ok) {
      throw new Error(`Failed to fetch models: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching available models:", error);
    return {
      models: {},
      default_model: "none",
      available_count: 0,
      error: error.message,
    };
  }
}

/**
 * Get display name for a model
 */
export function getModelDisplayName(modelName) {
  const names = {
    grnet: "GRNet (High Quality) ⭐",
    pointr: "PointR (Balanced)",
    none: "No Models Available",
    auto: "Auto-Select Best Available",
  };
  return names[modelName] || modelName;
}

/**
 * Get description for a model
 */
export function getModelDescription(modelName) {
  const descriptions = {
    grnet:
      "Gated Recurrent Unit Network - Superior quality reconstruction using hierarchical coarse-to-fine generation. Recommended for high-fidelity temple geometry.",
    pointr:
      "Transformer-based point completion network - Balanced speed and quality. Good for quick processing.",
    auto: "Automatically selects the best available model (GRNet preferred, falls back to PointR)",
  };
  return descriptions[modelName] || "Completion model for point cloud reconstruction";
}

/**
 * Format model info for display
 */
export function formatModelInfo(modelName, modelData) {
  const available = modelData?.available ? "✓ Available" : "✗ Not Available";
  const description = getModelDescription(modelName);

  return {
    name: getModelDisplayName(modelName),
    available: modelData?.available,
    status: available,
    description,
    reason: modelData?.reason || "",
  };
}

/**
 * Get recommended model based on profile and availability
 */
export function getRecommendedModel(modelsInfo, profile) {
  if (!modelsInfo || !modelsInfo.models) return "auto";

  // For HQ profile, strongly prefer GRNet
  if (profile === "hq" && modelsInfo.models.grnet?.available) {
    return "grnet";
  }

  // For balanced and fast, use default
  return modelsInfo.default_model || "auto";
}
