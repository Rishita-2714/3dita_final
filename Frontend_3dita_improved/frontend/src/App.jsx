import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import toast, { Toaster } from "react-hot-toast";
import HeroSection from "./components/HeroSection";
import ProcessingOverlay from "./components/ProcessingOverlay";
import ResultViewer from "./components/ResultViewer";
import UploadDialog from "./components/UploadDialog";
import { reconstructTemple } from "./utils/api";

const fadeTransition = {
  duration: 0.4,
  ease: "easeOut",
};

export default function App() {
  const [appState, setAppState] = useState("idle");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [resultData, setResultData] = useState(null);
  const [jobProgress, setJobProgress] = useState({ progress: 0, status: "idle" });

  const handleSubmit = async (file, reconstructionOptions) => {
    setIsDialogOpen(false);
    setAppState("processing");
    setJobProgress({ progress: 0, status: "queued" });

    try {
      const data = await reconstructTemple(file, reconstructionOptions, setJobProgress);
      setResultData(data);
      setAppState("result");
      toast.success("Reconstruction complete.");
    } catch (error) {
      toast.error(
        error?.message ||
          "Reconstruction failed. Please verify the backend and try again.",
      );
      setAppState("idle");
    }
  };

  const handleNewReconstruction = () => {
    setResultData(null);
    setJobProgress({ progress: 0, status: "idle" });
    setAppState("idle");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#1A0A2E",
        overflowX: "hidden",
      }}
    >
      <AnimatePresence mode="wait">
        {appState === "idle" ? (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={fadeTransition}
          >
            <HeroSection onOpen={() => setIsDialogOpen(true)} />
          </motion.div>
        ) : null}

        {appState === "result" && resultData ? (
          <motion.div
            key="result"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={fadeTransition}
          >
            <ResultViewer
              beforeUrl={resultData.before_url}
              afterUrl={resultData.after_url}
              addedUrl={resultData.added_geometry_url}
              restorationPanelUrl={resultData.restoration_panel_url}
              restoredRegionsUrl={resultData.restored_regions_url}
              metadata={resultData.metadata}
              onNewReconstruction={handleNewReconstruction}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>

      {appState === "processing" ? (
        <ProcessingOverlay
          isProcessing
          progress={jobProgress.progress}
          status={jobProgress.status}
        />
      ) : null}

      <UploadDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSubmit={handleSubmit}
      />

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#12071F",
            color: "#FFF8F0",
            border: "1px solid rgba(184, 134, 11, 0.18)",
          },
        }}
      />
    </div>
  );
}
