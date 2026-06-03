import { useState } from "react";
import ModelViewer from "./ModelViewer";

const colors = {
  indigo: "#1A0A2E",
  gold: "#B8860B",
  saffron: "#FF6B35",
  cream: "#FFF8F0",
};

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function downloadFile(url, filename) {
  if (!url) {
    return;
  }

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

function StatItem({ label, value }) {
  return (
    <div>
      <div
        style={{
          color: "rgba(184,134,11,0.58)",
          fontFamily: '"Courier New", monospace',
          fontSize: "14px",
          letterSpacing: "0.1em",
          marginBottom: "8px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: colors.gold,
          fontFamily: "Georgia, serif",
          fontSize: "28px",
          fontWeight: 500,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function Panel({ title, accent, children }) {
  return (
    <div
      style={{
        position: "relative",
        minWidth: 0,
        height: "100%",
        border: `1px solid ${accent}`,
        background: colors.indigo,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "12px",
          top: "10px",
          zIndex: 10,
          color: accent,
          fontFamily: '"Courier New", monospace',
          fontSize: "13px",
          fontWeight: "bold",
          letterSpacing: "0.12em",
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

export default function ResultViewer({
  beforeUrl,
  afterUrl,
  addedUrl,
  restorationPanelUrl,
  restoredRegionsUrl,
  metadata = {},
  onNewReconstruction,
}) {
  const [damageMode, setDamageMode] = useState(false);
  const [cameraState, setCameraState] = useState(null);
  const confidence = `${(Number(metadata.confidence || 0) * 100).toFixed(1)}%`;
  const reconstructionMetric = metadata.triangle_count
    ? `${formatNumber(metadata.triangle_count)} tris`
    : confidence;
  const completeness = `${Number(metadata.surface_completeness || 0).toFixed(1)}%`;
  const holesClosed = metadata.holes_closed ?? metadata.added_points ?? metadata.completion?.generated_points ?? 0;

  return (
    <section
      style={{
        minHeight: "100vh",
        background: colors.indigo,
        color: colors.cream,
        padding: "24px 24px 0",
      }}
    >
      <style>
        {`
          @keyframes damagePulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(215,25,32,0.62), 0 0 18px rgba(215,25,32,0.42); }
            50% { box-shadow: 0 0 0 9px rgba(215,25,32,0), 0 0 34px rgba(215,25,32,0.85); }
          }
        `}
      </style>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "24px",
          border: `1px solid rgba(184,134,11,0.35)`,
          background: colors.indigo,
          padding: "20px 24px",
        }}
      >
        <div>
          <div
            style={{
              color: colors.gold,
              fontFamily: '"Courier New", monospace',
              fontSize: "15px",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
            }}
          >
            RECONSTRUCTION COMPLETE
          </div>
          <h1
            style={{
              color: colors.gold,
              fontFamily: "Georgia, serif",
              fontSize: "34px",
              fontWeight: 400,
              margin: "8px 0 0",
            }}
          >
            Before / After 3D Viewer
          </h1>
        </div>

        <button
          type="button"
          onClick={() => setDamageMode((current) => !current)}
          style={{
            border: `1px solid ${colors.saffron}`,
            background: "#D71920",
            color: colors.cream,
            cursor: "pointer",
            fontFamily: "Georgia, serif",
            fontSize: "15px",
            letterSpacing: "0.12em",
            padding: "14px 24px",
            textTransform: "uppercase",
            animation: "damagePulse 1.35s ease-in-out infinite",
            borderRadius: "999px",
          }}
        >
          {damageMode ? "DAMAGE MODE ON" : "DAMAGE MODE"}
        </button>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: "12px",
          height: "max(600px, calc(100vh - 220px))",
          marginTop: "18px",
          width: "100%",
        }}
      >
        <Panel title="DAMAGED" accent={colors.gold}>
          <ModelViewer
            url={beforeUrl}
            mode="before"
            isLoading={false}
            cameraState={cameraState}
            onCameraChange={setCameraState}
          />
        </Panel>

        <Panel title="RECONSTRUCTED" accent={damageMode ? "#D71920" : colors.saffron}>
          <ModelViewer
            url={afterUrl}
            mode="after"
            isLoading={false}
            overlayUrl={damageMode ? (restoredRegionsUrl || addedUrl) : null}
            damageMode={damageMode}
            cameraState={cameraState}
            onCameraChange={setCameraState}
          />
        </Panel>

      </div>

      <div
        style={{
          background: colors.indigo,
          border: `1px solid ${colors.gold}`,
          marginTop: "18px",
          padding: "20px 24px",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
            gap: "20px",
          }}
        >
          <StatItem
            label="POINTS BEFORE"
            value={formatNumber(metadata.before_points)}
          />
          <StatItem
            label="POINTS AFTER"
            value={formatNumber(metadata.after_points)}
          />
          <StatItem
            label="HOLES CLOSED"
            value={formatNumber(holesClosed)}
          />
          <StatItem
            label="SURFACE COMPLETE"
            value={completeness}
          />
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: "14px",
          marginTop: "16px",
        }}
      >
        <button
          type="button"
          onClick={onNewReconstruction}
          style={{
            border: `1px solid ${colors.saffron}`,
            background: "transparent",
            color: colors.saffron,
            cursor: "pointer",
            fontFamily: "Georgia, serif",
            fontSize: "15px",
            letterSpacing: "0.05em",
            padding: "12px 34px",
          }}
        >
          New Reconstruction
        </button>
        <button
          type="button"
          onClick={() => downloadFile(afterUrl, "reconstructed.ply")}
          style={{
            border: `1px solid ${colors.saffron}`,
            background: "transparent",
            color: colors.saffron,
            cursor: "pointer",
            fontFamily: "Georgia, serif",
            fontSize: "15px",
            letterSpacing: "0.05em",
            padding: "12px 34px",
          }}
        >
          Download Reconstructed Surface
        </button>
      </div>
    </section>
  );
}
