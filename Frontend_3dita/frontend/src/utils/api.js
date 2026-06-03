import axios from "axios";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const REQUEST_TIMEOUT_MS = 30000;
const SOCKET_TIMEOUT_MS = 300000;

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8010")
  .replace(/\/$/, "");
const WS_BASE_URL =
  import.meta.env.VITE_WS_URL ||
  API_BASE_URL.replace(/^http/i, (match) =>
    match.toLowerCase() === "https" ? "wss" : "ws",
  );

function joinUrl(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

function normalizeProgress(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return 0;
  }

  return number > 1 ? Math.round(number) : Math.round(number * 100);
}

function normalizeResultPayload(payload, fallbackBeforeUrl) {
  const data = payload?.result || payload?.data || payload || {};
  const metadata = data.metadata || data.meta || {};
  const afterUrl =
    data.after_url ||
    data.mesh_url ||
    data.reconstructed_url ||
    data.output_url ||
    metadata.mesh_url;
  const beforeUrl =
    data.before_url ||
    data.original_url ||
    data.input_url ||
    fallbackBeforeUrl ||
    null;

  return {
    ...data,
    before_url: beforeUrl,
    after_url: afterUrl,
    added_geometry_url: data.added_geometry_url || data.added_url || metadata.added_geometry_url || null,
    restoration_panel_url: data.restoration_panel_url || metadata.restoration_panel_url || null,
    restored_regions_url: data.restored_regions_url || metadata.restored_regions_url || null,
    metadata,
  };
}

function hasResultModel(payload) {
  const data = payload?.result || payload?.data || payload || {};

  return Boolean(
    data.after_url ||
      data.mesh_url ||
      data.reconstructed_url ||
      data.output_url ||
      data.metadata?.mesh_url,
  );
}

function getErrorMessage(error) {
  if (error.code === "ERR_NETWORK") {
    return "Network error: unable to reach the reconstruction server at the configured API URL.";
  }

  if (error.code === "ECONNABORTED") {
    return "The reconstruction server did not respond in time. Make sure the backend is running.";
  }

  if (error.response?.data?.message) {
    return error.response.data.message;
  }

  if (error.response?.data?.detail) {
    return typeof error.response.data.detail === "string"
      ? error.response.data.detail
      : "The backend rejected the reconstruction request.";
  }

  return error.message || "Reconstruction request failed unexpectedly.";
}

async function pollJob(jobId, onProgress, fallbackBeforeUrl) {
  const maxAttempts = 720;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const { data } = await axios.get(joinUrl(API_BASE_URL, `/api/job/${jobId}`), {
      timeout: REQUEST_TIMEOUT_MS,
    });
    const status = String(data.status || "").toLowerCase();

    if (typeof data.progress !== "undefined") {
      onProgress?.({
        progress: normalizeProgress(data.progress),
        status: data.status || "processing",
      });
    }

    if (
      (status === "done" || status === "complete" || status === "completed") &&
      hasResultModel(data)
    ) {
      return normalizeResultPayload(data, fallbackBeforeUrl);
    }

    if (status === "error" || status === "failed") {
      throw new Error(data.message || data.error || "Backend reconstruction failed.");
    }

    await sleep(500);
  }

  throw new Error("Timed out waiting for the backend reconstruction job.");
}

function waitForJobSocket(jobId, onProgress, fallbackBeforeUrl) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const socket = new WebSocket(joinUrl(WS_BASE_URL, `/ws/job/${jobId}`));
    let timeoutId = 0;

    const resetTimeout = () => {
      window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        finish(reject, new Error("WebSocket progress timed out."));
      }, SOCKET_TIMEOUT_MS);
    };

    const finish = (callback, value) => {
      if (settled) {
        return;
      }

      settled = true;
      window.clearTimeout(timeoutId);
      socket.close();
      callback(value);
    };

    resetTimeout();

    socket.onmessage = (event) => {
      try {
        resetTimeout();
        const message = JSON.parse(event.data);
        const type = String(message.type || message.status || "").toLowerCase();

        if (type === "progress" || typeof message.progress !== "undefined") {
          onProgress?.({
            progress: normalizeProgress(message.value ?? message.progress),
            status: message.status || "processing",
          });
        }

        if (
          (type === "complete" || type === "done" || type === "completed") &&
          hasResultModel(message)
        ) {
          onProgress?.({ progress: 100, status: "complete" });
          finish(resolve, normalizeResultPayload(message, fallbackBeforeUrl));
        }

        if (type === "error" || type === "failed") {
          finish(
            reject,
            new Error(message.message || message.error || "Backend reconstruction failed."),
          );
        }
      } catch (error) {
        finish(reject, new Error("Received an invalid progress message from the backend."));
      }
    };

    socket.onerror = () => {
      finish(reject, new Error("WebSocket progress connection failed."));
    };
  });
}

export async function reconstructTemple(file, options = {}, onProgress) {
  const isMockMode =
    String(import.meta.env.VITE_MOCK_MODE).toLowerCase() === "true";

  if (isMockMode) {
    for (const progress of [12, 34, 58, 79, 100]) {
      await sleep(550);
      onProgress?.({ progress, status: "mock-processing" });
    }

    return {
      before_url: "/mock/sample_before.ply",
      after_url: "/mock/sample_after.ply",
      metadata: {
        component_class: "Shikhara",
        before_points: 12400,
        after_points: 18750,
        confidence: 0.87,
      },
    };
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("model", options.model || "ae");
  formData.append("params", JSON.stringify(options.params || {}));

  const fallbackBeforeUrl = `${URL.createObjectURL(file)}#${encodeURIComponent(
    file.name,
  )}`;

  try {
    onProgress?.({ progress: 0, status: "queued" });
    console.debug("[frontend] reconstructTemple", { apiUrl: API_BASE_URL, fileName: file.name, model: options.model });

    const { data } = await axios.post(joinUrl(API_BASE_URL, "/api/reconstruct"), formData, {
      timeout: REQUEST_TIMEOUT_MS,
    });

    if (!data.job_id && !data.jobId) {
      onProgress?.({ progress: 100, status: "complete" });
      return normalizeResultPayload(data, fallbackBeforeUrl);
    }

    const jobId = data.job_id || data.jobId;
    onProgress?.({ progress: normalizeProgress(data.progress), status: "queued" });

    try {
      return await waitForJobSocket(jobId, onProgress, fallbackBeforeUrl);
    } catch {
      return await pollJob(jobId, onProgress, fallbackBeforeUrl);
    }
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
