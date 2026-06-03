import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { AnimatePresence, motion } from "framer-motion";
import { CloudUpload, X } from "lucide-react";
import toast from "react-hot-toast";

const RECONSTRUCTION_MODES = [
  {
    id: "geometry_only",
    label: "Geometry Only",
    description: "Stable Open3D reconstruction from observed temple scan geometry",
  },
  {
    id: "dl_completion",
    label: "DL Completion",
    description: "Auto-select the best DL completion model (GRNet preferred) before meshing",
  },
  {
    id: "grnet_completion",
    label: "GRNet",
    description: "Use GRNet high-quality completion before meshing",
  },
  {
    id: "pointr_completion",
    label: "PointR",
    description: "Run the configured pretrained PointR checkpoint before meshing",
  },
];

const QUALITY_OPTIONS = [
  {
    id: "hq",
    label: "High Fidelity",
    description: "Best surface quality for temple scans",
    params: [{ key: "detail", label: "Detail", min: 8, max: 11, step: 1, value: 10 }],
  },
  {
    id: "balanced",
    label: "Balanced",
    description: "Strong detail with faster processing",
    params: [{ key: "detail", label: "Detail", min: 7, max: 10, step: 1, value: 9 }],
  },
  {
    id: "preview",
    label: "Preview",
    description: "Faster reconstruction for quick iteration",
    params: [{ key: "detail", label: "Detail", min: 6, max: 9, step: 1, value: 8 }],
  },
];

function getDefaultParams(profileId) {
  const model =
    QUALITY_OPTIONS.find((option) => option.id === profileId) || QUALITY_OPTIONS[0];

  return Object.fromEntries(model.params.map((param) => [param.key, param.value]));
}

function formatFileSize(size) {
  if (!size) {
    return "0 KB";
  }

  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(
    Math.floor(Math.log(size) / Math.log(1024)),
    units.length - 1,
  );
  const value = size / 1024 ** exponent;
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function getFormatLabel(fileName = "") {
  const extension = fileName.split(".").pop()?.toUpperCase();
  if (extension === "PLY" || extension === "OBJ" || extension === "TXT") {
    return `.${extension}`;
  }

  return "UNKNOWN";
}

function MandalaWatermark() {
  return (
    <svg
      viewBox="0 0 300 300"
      className="h-full w-full"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <g stroke="#B8860B" strokeWidth="1.2">
        <circle cx="150" cy="150" r="28" />
        <circle cx="150" cy="150" r="52" />
        <circle cx="150" cy="150" r="78" />
        <circle cx="150" cy="150" r="106" />
        {Array.from({ length: 12 }, (_, index) => {
          const angle = (index * Math.PI) / 6;
          const x = 150 + Math.cos(angle) * 78;
          const y = 150 + Math.sin(angle) * 78;

          return (
            <ellipse
              key={index}
              cx={x}
              cy={y}
              rx="12"
              ry="28"
              transform={`rotate(${index * 30} ${x} ${y})`}
            />
          );
        })}
      </g>
    </svg>
  );
}

export default function UploadDialog({ isOpen, onClose, onSubmit }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedMode, setSelectedMode] = useState("dl_completion");
  const [selectedProfile, setSelectedProfile] = useState("balanced");
  const [params, setParams] = useState(getDefaultParams("balanced"));

  const onDrop = useCallback(
    (acceptedFiles) => {
      const [file] = acceptedFiles;
      if (file) {
        setSelectedFile(file);
        toast.success("Scan file accepted.");
      }
    },
    [],
  );

  const onDropRejected = useCallback((fileRejections) => {
    const message =
      fileRejections[0]?.errors[0]?.message ||
      "Please upload a valid .ply, .obj, or .txt file.";
    toast.error(message);
  }, []);

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      onDropRejected,
      multiple: false,
      accept: {
        "model/ply": [".ply"],
        "model/obj": [".obj"],
        "text/plain": [".obj", ".txt"],
        "application/octet-stream": [".ply", ".obj", ".txt"],
      },
    });

  const rejectionMessage = fileRejections[0]?.errors[0]?.message;
  const formatLabel = selectedFile ? getFormatLabel(selectedFile.name) : "";
  const activeProfile =
    QUALITY_OPTIONS.find((option) => option.id === selectedProfile) || QUALITY_OPTIONS[0];

  const handleProfileChange = (profileId) => {
    setSelectedProfile(profileId);
    setParams(getDefaultParams(profileId));
  };

  const handleParamChange = (key, value) => {
    setParams((currentParams) => ({
      ...currentParams,
      [key]: Number(value),
    }));
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      return;
    }

    try {
      setIsSubmitting(true);
      const usePoinTr = selectedMode === "pointr_completion";
      const useGrNet = selectedMode === "grnet_completion";
      await onSubmit(selectedFile, {
        model: usePoinTr || useGrNet || selectedMode === "dl_completion" ? "dl_completion" : selectedMode,
        params: {
          ...params,
          profile: selectedProfile,
          ...(usePoinTr
            ? { completion_model: "pointr", force_completion: true }
            : useGrNet
            ? { completion_model: "grnet", force_completion: true }
            : {}),
          mesh_method: selectedProfile === "hq" ? "poisson" : "auto",
        },
      });
      setSelectedFile(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen ? (
        <motion.div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4 py-8 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            initial={{ opacity: 0, y: 48 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 36 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="relative w-full max-w-lg overflow-hidden rounded-xl border border-[#B8860B] bg-[#1A0A2E] p-6 shadow-[0_20px_80px_rgba(0,0,0,0.45)]"
          >
            <div className="pointer-events-none absolute inset-0 opacity-[0.05]">
              <MandalaWatermark />
            </div>
            <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-[radial-gradient(circle_at_top,rgba(184,134,11,0.16),transparent_70%)]" />

            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 z-10 rounded-full p-2 text-[#B8860B] transition hover:bg-[#B8860B]/10"
              aria-label="Close upload dialog"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="relative space-y-6">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.32em] text-[#B8860B]/80">
                  Temple Scan Intake
                </p>
                <h2 className="font-serif text-3xl text-[#B8860B]">
                  Upload Temple Scan
                </h2>
                <p className="text-sm leading-7 text-[#FFF8F0]/72">
                  Add a `.ply`, `.obj`, or `.txt` reconstruction source file to
                  begin geometry restoration and synchronized visualization.
                </p>
              </div>

              <div
                {...getRootProps()}
                className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
                  isDragActive
                    ? "border-[#B8860B] bg-[#B8860B]/10 shadow-[0_0_30px_rgba(184,134,11,0.32)]"
                    : "border-[#B8860B]/60 bg-white/5 hover:border-[#B8860B] hover:shadow-[0_0_24px_rgba(184,134,11,0.22)]"
                }`}
              >
                <input {...getInputProps()} />
                <div className="mx-auto flex max-w-md flex-col items-center gap-4">
                  <div className="rounded-full border border-[#B8860B]/40 bg-[#B8860B]/10 p-4 text-[#B8860B]">
                    <CloudUpload className="h-8 w-8" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium text-[#FFF8F0]">
                      {isDragActive
                        ? "Release to place the scan"
                        : "Drop .ply, .obj, or .txt file here"}
                    </p>
                    <p className="text-sm text-[#FFF8F0]/58">
                      or click to browse from your device
                    </p>
                  </div>
                </div>
              </div>

              {rejectionMessage ? (
                <p className="rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">
                  {rejectionMessage}
                </p>
              ) : null}

              {selectedFile ? (
                <div className="rounded-xl border border-[#B8860B]/30 bg-white/5 px-5 py-4">
                  <p className="text-xs uppercase tracking-[0.25em] text-[#B8860B]/78">
                    Selected File
                  </p>
                  <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="space-y-1">
                      <p
                        className="text-sm text-[#FFF8F0]"
                        style={{ fontFamily: '"Courier New", monospace' }}
                      >
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-[#FFF8F0]/62">
                        {formatFileSize(selectedFile.size)}
                      </p>
                    </div>
                    <span className="inline-flex w-fit rounded-full bg-[#FF6B35]/18 px-3 py-1 text-xs font-semibold tracking-[0.2em] text-[#FF6B35]">
                      {formatLabel}
                    </span>
                  </div>
                </div>
              ) : null}

              <div className="space-y-4 rounded-xl border border-[#B8860B]/25 bg-white/5 p-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-[#B8860B]/78">
                    Reconstruction Mode
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {RECONSTRUCTION_MODES.map((mode) => (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => setSelectedMode(mode.id)}
                        className={`border px-3 py-3 text-left transition ${
                          selectedMode === mode.id
                            ? "border-[#FF6B35] bg-[#FF6B35]/14 text-[#FFF8F0]"
                            : "border-[#B8860B]/25 bg-[#1A0A2E]/60 text-[#FFF8F0]/72 hover:border-[#B8860B]"
                        }`}
                      >
                        <span className="block text-sm font-semibold">
                          {mode.label}
                        </span>
                        <span className="mt-1 block text-xs text-[#FFF8F0]/55">
                          {mode.description}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-[#B8860B]/78">
                    Quality Profile
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    {QUALITY_OPTIONS.map((profile) => (
                      <button
                        key={profile.id}
                        type="button"
                        onClick={() => handleProfileChange(profile.id)}
                        className={`border px-3 py-3 text-left transition ${
                          selectedProfile === profile.id
                            ? "border-[#B8860B] bg-[#B8860B]/14 text-[#FFF8F0]"
                            : "border-[#B8860B]/25 bg-[#1A0A2E]/60 text-[#FFF8F0]/72 hover:border-[#B8860B]"
                        }`}
                      >
                        <span className="block text-sm font-semibold">
                          {profile.label}
                        </span>
                        <span className="mt-1 block text-xs text-[#FFF8F0]/55">
                          {profile.description}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {activeProfile.params.map((param) => (
                    <label key={param.key} className="block">
                      <span className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-[#B8860B]/80">
                        {param.label}
                        <span className="text-[#FFF8F0]/72">
                          {params[param.key]}
                        </span>
                      </span>
                      <input
                        type="range"
                        min={param.min}
                        max={param.max}
                        step={param.step}
                        value={params[param.key]}
                        onChange={(event) =>
                          handleParamChange(param.key, event.target.value)
                        }
                        className="mt-3 w-full accent-[#FF6B35]"
                      />
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={!selectedFile || isSubmitting}
                  onClick={handleSubmit}
                  className="rounded-full bg-[#FF6B35] px-6 py-3 text-sm font-semibold text-[#FFF8F0] transition disabled:cursor-not-allowed disabled:opacity-40 enabled:hover:shadow-[0_0_28px_rgba(255,107,53,0.35)]"
                >
                  {isSubmitting
                    ? "Reconstructing..."
                    : "Reconstruct Temple Part"}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
