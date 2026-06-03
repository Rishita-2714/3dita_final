import { useEffect, useState } from "react";

const messages = [
  "Reading point cloud geometry…",
  "Mapping temple architecture…",
  "Preparing 3D visualization…",
  "Rendering sacred geometry…",
];

function OrbitCircle({ radius, className }) {
  return (
    <circle
      className={className}
      cx="160"
      cy="160"
      r={radius}
      fill="none"
      stroke="#B8860B"
      strokeWidth="0.5"
      opacity="0.12"
    />
  );
}

function PetalRing({ count, radius, rx, ry, fill, stroke, strokeWidth, className, filter }) {
  return (
    <g className={className} filter={filter} style={{ transformOrigin: "160px 160px" }}>
      {Array.from({ length: count }, (_, index) => {
        const angle = (360 / count) * index;
        return (
          <ellipse
            key={angle}
            cx="160"
            cy={160 - radius}
            rx={rx}
            ry={ry}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            transform={`rotate(${angle} 160 160)`}
          />
        );
      })}
    </g>
  );
}

function DiamondRing({ count, radius, size, fill, stroke, strokeWidth, className, filter }) {
  return (
    <g className={className} filter={filter} style={{ transformOrigin: "160px 160px" }}>
      {Array.from({ length: count }, (_, index) => {
        const angle = (360 / count) * index;
        const radians = (angle * Math.PI) / 180;
        const x = 160 + Math.cos(radians) * radius;
        const y = 160 + Math.sin(radians) * radius;
        return (
          <rect
            key={angle}
            x={x - size / 2}
            y={y - size / 2}
            width={size}
            height={size}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            transform={`rotate(45 ${x} ${y})`}
          />
        );
      })}
    </g>
  );
}

function MandalaSvg({ size = 160 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 320 320"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      style={{ display: "block", overflow: "visible" }}
    >
      <defs>
        <filter id="glow-soft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-strong" x="-70%" y="-70%" width="240%" height="240%">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <circle
        className="mandala-aura"
        cx="160"
        cy="160"
        r="150"
        fill="none"
        stroke="#B8860B"
        opacity="0.15"
        strokeWidth="40"
      />

      <OrbitCircle radius="130" />
      <OrbitCircle radius="95" />
      <OrbitCircle radius="67" />
      <OrbitCircle radius="45" />

      <circle
        className="mandala-outer-orbit"
        cx="160"
        cy="160"
        r="148"
        fill="none"
        stroke="#B8860B"
        strokeWidth="1"
        strokeDasharray="2 18"
        opacity="0.4"
        filter="url(#glow-soft)"
        style={{ transformOrigin: "160px 160px" }}
      />

      <PetalRing
        count={12}
        radius={110}
        rx={7}
        ry={22}
        fill="rgba(184,134,11,0.2)"
        stroke="#FFB300"
        strokeWidth="1.5"
        className="mandala-outer-petals"
        filter="url(#glow-soft)"
      />
      <DiamondRing
        count={8}
        radius={80}
        size={10}
        fill="rgba(255,107,53,0.15)"
        stroke="#FF6B35"
        strokeWidth="1.5"
        className="mandala-middle-diamonds"
        filter="url(#glow-soft)"
      />
      <PetalRing
        count={6}
        radius={55}
        rx={5}
        ry={14}
        fill="rgba(255,179,0,0.25)"
        stroke="#FFB300"
        strokeWidth="2"
        className="mandala-inner-petals"
        filter="url(#glow-strong)"
      />
      <DiamondRing
        count={4}
        radius={35}
        size={6}
        fill="rgba(255,107,53,0.3)"
        stroke="#FF6B35"
        strokeWidth="2"
        className="mandala-inner-diamonds"
        filter="url(#glow-strong)"
      />

      <g className="mandala-center-kalasha" filter="url(#glow-strong)" style={{ transformOrigin: "160px 160px" }}>
        <rect x="152" y="152" width="16" height="16" fill="#FF6B35" />
        <rect x="152" y="152" width="16" height="16" fill="#FF6B35" transform="rotate(45 160 160)" />
        <circle cx="160" cy="160" r="5" fill="#FFB300" />
      </g>

      <text
        x="160"
        y="165"
        textAnchor="middle"
        dominantBaseline="middle"
        fontFamily="Georgia, serif"
        fontSize="14"
        fill="#B8860B"
        opacity="0.5"
        filter="url(#glow-soft)"
      >
        ॐ
      </text>
    </svg>
  );
}

export default function MandalaSpinner({
  size = 160,
  fullscreen = true,
  showMessage = true,
}) {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const intervalId = setInterval(() => {
      setMessageIndex((currentIndex) => (currentIndex + 1) % messages.length);
    }, 2000);

    return () => clearInterval(intervalId);
  }, []);

  const content = (
    <>
      <style>
        {`
          @keyframes mandala-spin-cw {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }

          @keyframes mandala-spin-ccw {
            from { transform: rotate(0deg); }
            to { transform: rotate(-360deg); }
          }

          @keyframes mandala-center-pulse {
            0%, 100% { transform: scale(0.85); }
            50% { transform: scale(1.15); }
          }

          @keyframes mandala-aura-pulse {
            0%, 100% { opacity: 0.05; }
            50% { opacity: 0.2; }
          }

          .mandala-aura { animation: mandala-aura-pulse 4s ease-in-out infinite; }
          .mandala-outer-orbit { animation: mandala-spin-cw 25s linear infinite; }
          .mandala-outer-petals { animation: mandala-spin-cw 12s linear infinite; }
          .mandala-middle-diamonds { animation: mandala-spin-ccw 8s linear infinite; }
          .mandala-inner-petals { animation: mandala-spin-cw 5s linear infinite; }
          .mandala-inner-diamonds { animation: mandala-spin-ccw 3s linear infinite; }
          .mandala-center-kalasha { animation: mandala-center-pulse 2s ease-in-out infinite; }
        `}
      </style>

      <MandalaSvg size={size} />

      {showMessage ? (
        <p
          style={{
            margin: "18px 0 0",
            color: "#B8860B",
            fontFamily: "Georgia, serif",
            fontSize: "12px",
            letterSpacing: "0.1em",
            textAlign: "center",
          }}
        >
          {messages[messageIndex]}
        </p>
      ) : null}
    </>
  );

  if (!fullscreen) {
    return content;
  }

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        minHeight: "320px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#1A0A2E",
      }}
    >
      {content}
    </div>
  );
}
