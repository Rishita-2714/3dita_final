import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import MandalaSpinner from "./MandalaSpinner";

const messages = [
  "Analyzing point cloud…",
  "Running reconstruction model…",
  "Streaming backend progress…",
  "Preparing visualization…",
];

const particleColors = ["#B8860B", "#FFB300", "#FF6B35"];

function ParticleCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    let animationFrame = 0;
    let particles = [];

    if (!canvas || !context) {
      return undefined;
    }

    const resize = () => {
      canvas.width = window.innerWidth * window.devicePixelRatio;
      canvas.height = window.innerHeight * window.devicePixelRatio;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      context.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    };

    const createParticle = (resetToBottom = false) => ({
      x: Math.random() * window.innerWidth,
      y: resetToBottom
        ? window.innerHeight + Math.random() * 80
        : Math.random() * window.innerHeight,
      speed: 0.3 + Math.random() * 0.9,
      size: 1 + Math.random() * 2,
      color: particleColors[Math.floor(Math.random() * particleColors.length)],
      opacity: 0.2 + Math.random() * 0.5,
    });

    const resetParticles = () => {
      particles = Array.from({ length: 60 }, () => createParticle());
    };

    const draw = () => {
      context.clearRect(0, 0, window.innerWidth, window.innerHeight);

      particles.forEach((particle) => {
        particle.y -= particle.speed;

        if (particle.y < -12) {
          Object.assign(particle, createParticle(true));
        }

        context.save();
        context.globalAlpha = particle.opacity;
        context.shadowBlur = 6;
        context.shadowColor = particle.color;
        context.fillStyle = particle.color;
        context.beginPath();
        context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        context.fill();
        context.restore();
      });

      animationFrame = requestAnimationFrame(draw);
    };

    resize();
    resetParticles();
    draw();
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
      }}
      aria-hidden="true"
    />
  );
}

function CornerOrnament({ top, right, bottom, left, reverse = false }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{
        position: "absolute",
        top,
        right,
        bottom,
        left,
        zIndex: 2,
        opacity: 0.35,
        animation: `${reverse ? "ornament-spin-ccw" : "ornament-spin-cw"} 12s linear infinite`,
      }}
      aria-hidden="true"
    >
      <path d="M3 3 L17 17 M17 3 L3 17" stroke="#B8860B" strokeWidth="1" />
      <rect x="7" y="7" width="6" height="6" fill="#0D0618" stroke="#B8860B" strokeWidth="1" transform="rotate(45 10 10)" />
    </svg>
  );
}

function getStatusMessage(status, progress) {
  if (!status || status === "idle") {
    return messages[0];
  }

  if (status === "queued") {
    return "Queued on reconstruction backend…";
  }

  if (status === "complete" || progress >= 100) {
    return "Reconstruction complete…";
  }

  return `${status.replace(/[-_]/g, " ")}…`;
}

export default function ProcessingOverlay({
  isProcessing,
  progress = 0,
  status = "processing",
}) {
  const [messageIndex, setMessageIndex] = useState(0);
  const normalizedProgress = Math.max(0, Math.min(100, Math.round(progress || 0)));
  const statusMessage =
    normalizedProgress > 0 ? getStatusMessage(status, normalizedProgress) : messages[messageIndex];

  useEffect(() => {
    if (!isProcessing) {
      return undefined;
    }

    const intervalId = setInterval(() => {
      setMessageIndex((currentIndex) => (currentIndex + 1) % messages.length);
    }, 2500);

    return () => clearInterval(intervalId);
  }, [isProcessing]);

  return (
    <AnimatePresence>
      {isProcessing ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{
            opacity: 1,
            scale: 1,
            transition: { duration: 0.6, ease: "easeOut" },
          }}
          exit={{
            opacity: 0,
            scale: 1.04,
            transition: { duration: 0.4 },
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9998,
            overflow: "hidden",
            background:
              "radial-gradient(ellipse 600px 400px at 50% 55%, rgba(184,134,11,0.18) 0%, transparent 70%), radial-gradient(ellipse at 50% 100%, rgba(255,107,53,0.08) 0%, transparent 50%), #0D0618",
          }}
        >
          <style>
            {`
              @keyframes progress-fill {
                0% { width: 0%; }
                82% { width: 82%; }
                100% { width: 82%; }
              }

              @keyframes status-fade {
                from { opacity: 0; }
                to { opacity: 1; }
              }

              @keyframes ornament-spin-cw {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
              }

              @keyframes ornament-spin-ccw {
                from { transform: rotate(0deg); }
                to { transform: rotate(-360deg); }
              }
            `}
          </style>

          <ParticleCanvas />
          <CornerOrnament top="20px" left="20px" />
          <CornerOrnament top="20px" right="20px" reverse />
          <CornerOrnament bottom="20px" left="20px" reverse />
          <CornerOrnament bottom="20px" right="20px" />

          <div
            style={{
              position: "relative",
              zIndex: 1,
              minHeight: "100vh",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
            }}
          >
            <motion.div
              initial={{ rotate: -30, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              style={{ width: "320px", height: "320px" }}
            >
              <MandalaSpinner size={320} fullscreen={false} showMessage={false} />
            </motion.div>

            <div style={{ marginTop: "40px" }}>
              <div
                key={statusMessage}
                style={{
                  color: "#FFB300",
                  fontFamily: "Georgia, serif",
                  fontSize: "18px",
                  letterSpacing: "0.12em",
                  textShadow:
                    "0 0 30px rgba(255,179,0,0.6), 0 0 60px rgba(255,179,0,0.2)",
                  animation: "status-fade 0.4s ease-out",
                }}
              >
                {statusMessage}
              </div>

              <div
                style={{
                  marginTop: "14px",
                  color: "#FFF8F0",
                  fontFamily: "Inter, sans-serif",
                  fontSize: "12px",
                  letterSpacing: "0.08em",
                  opacity: 0.45,
                }}
              >
                Please wait — reconstruction in progress
              </div>

              <div
                style={{
                  width: "200px",
                  height: "1px",
                  margin: "16px auto 0",
                  background:
                    "linear-gradient(to right, transparent, #B8860B, transparent)",
                }}
              />

              <div
                style={{
                  position: "relative",
                  width: "280px",
                  height: "2px",
                  margin: "12px auto 0",
                  background: "rgba(184,134,11,0.15)",
                  borderRadius: "2px",
                  overflow: "visible",
                }}
              >
                <div
                  style={{
                    position: "relative",
                    height: "100%",
                    width: `${normalizedProgress || 8}%`,
                    background: "#FFB300",
                    borderRadius: "2px",
                    transition: "width 0.35s ease",
                  }}
                >
                  <span
                    style={{
                      position: "absolute",
                      right: "-2px",
                      top: "-1px",
                      width: "4px",
                      height: "4px",
                      borderRadius: "50%",
                      background: "#FFB300",
                      boxShadow: "0 0 10px 3px rgba(255,179,0,0.8)",
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  marginTop: "10px",
                  color: "#B8860B",
                  fontFamily: '"Courier New", monospace',
                  fontSize: "12px",
                  letterSpacing: "0.14em",
                }}
              >
                {normalizedProgress}%
              </div>
            </div>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
