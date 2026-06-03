import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence, useSpring } from "framer-motion";

const headingWords = ["3DITA", "Temple", "Reconstruction"];
const lightRays = [
  { angle: -30, height: "40vh" },
  { angle: -16, height: "50vh" },
  { angle: 0, height: "58vh" },
  { angle: 16, height: "50vh" },
  { angle: 30, height: "40vh" },
];

function Niche({ x, y }) {
  return (
    <g>
      <rect x={x} y={y + 6} width="12" height="20" fill="rgba(184,134,11,0.08)" stroke="#B8860B" strokeWidth="0.8" />
      <path
        d={`M ${x} ${y + 6} A 6 6 0 0 1 ${x + 12} ${y + 6}`}
        fill="none"
        stroke="#B8860B"
        strokeWidth="0.8"
      />
    </g>
  );
}

function TempleSilhouette({ width = 620, opacity = 0.8, blur = "0px" }) {
  const mainBands = [
    { y: 132, w: 22 },
    { y: 170, w: 34 },
    { y: 210, w: 46 },
    { y: 252, w: 60 },
    { y: 296, w: 76 },
    { y: 342, w: 92 },
    { y: 390, w: 108 },
    { y: 440, w: 124 },
    { y: 492, w: 140 },
    { y: 546, w: 156 },
  ];
  const miniBandWidths = [14, 20, 28, 34, 40, 46];
  const thickBands = 3;

  return (
    <svg
      viewBox="0 0 420 820"
      width={width}
      height="auto"
      preserveAspectRatio="xMidYMid meet"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      style={{ opacity, overflow: "visible", filter: `blur(${blur}) drop-shadow(0 0 24px rgba(255,215,0,0.22))` }}
    >
      <defs>
        <radialGradient id="templeGlow" gradientUnits="userSpaceOnUse" cx="210" cy="94" r="330">
          <stop offset="0%" stopColor="#FFD700" stopOpacity="0.54" />
          <stop offset="38%" stopColor="#B8860B" stopOpacity="0.16" />
          <stop offset="100%" stopColor="#8B5E00" stopOpacity="0.02" />
        </radialGradient>
      </defs>

      <g stroke="#B8860B" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="210" cy="66" r="56" fill="rgba(255,215,0,0.1)" />
        <circle cx="210" cy="66" r="94" stroke="rgba(255,215,0,0.18)" strokeWidth="2" fill="none" />
        <path
          d="M 212 22 L 218 64 L 230 96 L 236 150 L 210 166 L 184 150 L 190 96 L 202 64 Z"
          fill="rgba(255,215,0,0.08)"
          strokeWidth="2"
        />
        <path
          d="M 170,585 C 147,522 143,458 145,398 C 146,336 152,274 161,232 C 170,188 186,148 198,118 L 210,92 L 222,118 C 234,148 250,188 259,232 C 268,274 274,336 275,398 C 277,458 273,522 250,585 Z"
          fill="url(#templeGlow)"
          strokeWidth="2"
        />
        <path
          d="M 170,585 C 147,522 143,458 145,398 C 146,336 152,274 161,232 C 170,188 186,148 198,118 L 210,92 L 222,118 C 234,148 250,188 259,232 C 268,274 274,336 275,398 C 277,458 273,522 250,585 Z"
          fill="rgba(255,215,0,0.09)"
          opacity="0.96"
        />

        {mainBands.map((band) => (
          <rect
            key={band.y}
            x={210 - band.w / 2}
            y={band.y}
            width={band.w}
            height={thickBands}
            fill="rgba(184,134,11,0.46)"
            strokeWidth="1"
          />
        ))}

        {[{ y: 192, leftX: 145, rightX: 275 }, { y: 272, leftX: 137, rightX: 283 }, { y: 364, leftX: 125, rightX: 295 }, { y: 462, leftX: 112, rightX: 308 }].map((item) => (
          <g key={item.y}>
            <rect x={item.leftX - 5} y={item.y} width="7" height="10" fill="rgba(184,134,11,0.28)" strokeWidth="0.8" />
            <rect x={item.rightX} y={item.y} width="7" height="10" fill="rgba(184,134,11,0.28)" strokeWidth="0.8" />
          </g>
        ))}

        <path
          d="M 108,589 C 98,542 95,500 96,458 C 97,416 103,378 108,348 C 113,318 123,286 136,262 L 145,232 L 154,262 C 167,286 178,318 183,348 C 188,378 194,416 195,458 C 196,500 193,542 183,589 Z"
          fill="rgba(184,134,11,0.18)"
          strokeWidth="1"
        />
        {miniBandWidths.map((width, index) => (
          <rect
            key={`left-mini-${index}`}
            x={145 - width / 2}
            y={276 + index * 30}
            width={width}
            height="2"
            fill="rgba(184,134,11,0.28)"
            strokeWidth="0.7"
          />
        ))}
        <line x1="145" y1="224" x2="145" y2="236" stroke="#B8860B" strokeWidth="1.3" />
        <circle cx="145" cy="221" r="5" fill="rgba(184,134,11,0.34)" strokeWidth="1" />
        <polygon points="145,235 152,243 145,251 138,243" fill="rgba(184,134,11,0.24)" strokeWidth="1" />

        <path
          d="M 222,589 C 212,542 209,500 210,458 C 211,416 217,378 222,348 C 227,318 237,286 250,262 L 259,232 L 268,262 C 281,286 292,318 297,348 C 302,378 308,416 309,458 C 310,500 307,542 297,589 Z"
          fill="rgba(184,134,11,0.18)"
          strokeWidth="1"
        />
        {miniBandWidths.map((width, index) => (
          <rect
            key={`right-mini-${index}`}
            x={255 - width / 2}
            y={276 + index * 30}
            width={width}
            height="2"
            fill="rgba(184,134,11,0.28)"
            strokeWidth="0.7"
          />
        ))}
        <line x1="255" y1="224" x2="255" y2="236" stroke="#B8860B" strokeWidth="1.3" />
        <circle cx="255" cy="221" r="5" fill="rgba(184,134,11,0.34)" strokeWidth="1" />
        <polygon points="255,235 262,243 255,251 248,243" fill="rgba(184,134,11,0.24)" strokeWidth="1" />

        <rect x="114" y="587" width="194" height="22" fill="rgba(184,134,11,0.18)" strokeWidth="1" />
        {Array.from({ length: 9 }, (_, index) => (
          <g key={`arch-${index}`}>
            <rect x={117 + index * 20} y="597" width="16" height="10" fill="rgba(184,134,11,0.1)" stroke="#B8860B" strokeWidth="0.8" />
            <path d={`M ${117 + index * 20} 597 A 8 8 0 0 1 ${133 + index * 20} 597`} fill="none" stroke="#B8860B" strokeWidth="0.75" />
          </g>
        ))}

        <rect x="117" y="605" width="166" height="84" fill="rgba(184,134,11,0.18)" strokeWidth="1.6" />
        {[130, 148, 166, 184, 200, 216, 234, 252].map((x) => (
          <line key={`pilaster-${x}`} x1={x} y1="605" x2={x} y2="689" strokeWidth="0.95" opacity="0.55" />
        ))}
        {[132, 154, 176].map((x) => (
          <Niche key={`left-niche-${x}`} x={x} y={626} />
        ))}
        {[222, 244, 266].map((x) => (
          <Niche key={`right-niche-${x}`} x={x} y={626} />
        ))}
        <rect x="114" y="603" width="176" height="6" fill="rgba(184,134,11,0.34)" strokeWidth="1" />
        <rect x="112" y="683" width="180" height="5" fill="rgba(184,134,11,0.34)" strokeWidth="1" />

        <rect x="158" y="644" width="84" height="48" fill="rgba(184,134,11,0.18)" strokeWidth="1" />
        <line x1="176" y1="644" x2="176" y2="692" strokeWidth="1" opacity="0.55" />
        <line x1="224" y1="644" x2="224" y2="692" strokeWidth="1" opacity="0.55" />

        <rect x="90" y="564" width="240" height="12" fill="rgba(184,134,11,0.22)" strokeWidth="1.6" />
        {[110, 152, 258, 296].map((x) => (
          <g key={`pillar-${x}`}>
            <rect x={x} y="576" width="10" height="64" fill="rgba(184,134,11,0.18)" strokeWidth="1" />
            <rect x={x - 4} y="576" width="18" height="8" fill="rgba(184,134,11,0.34)" />
            <rect x={x - 3} y="636" width="16" height="6" fill="rgba(184,134,11,0.34)" />
          </g>
        ))}

        <rect x="88" y="635" width="236" height="10" fill="rgba(184,134,11,0.18)" strokeWidth="1" />
        <rect x="76" y="646" width="264" height="10" fill="rgba(184,134,11,0.18)" strokeWidth="1" />
        <rect x="64" y="657" width="292" height="10" fill="rgba(184,134,11,0.18)" strokeWidth="1" />

        <rect x="100" y="690" width="198" height="17" fill="rgba(184,134,11,0.22)" strokeWidth="1" />
        <rect x="82" y="709" width="236" height="15" fill="rgba(184,134,11,0.22)" strokeWidth="1" />
        <rect x="64" y="728" width="260" height="13" fill="rgba(184,134,11,0.22)" strokeWidth="1" />
        {Array.from({ length: 26 }, (_, i) => (
          <rect key={`tooth-${i}`} x={72 + i * 10} y="688" width="6" height="4" fill="rgba(184,134,11,0.33)" />
        ))}

        <rect x="40" y="740" width="340" height="10" fill="rgba(184,134,11,0.16)" strokeWidth="0.9" />
        <rect x="18" y="752" width="380" height="10" fill="rgba(184,134,11,0.16)" strokeWidth="0.9" />
        <rect x="0" y="764" width="420" height="10" fill="rgba(184,134,11,0.16)" strokeWidth="0.9" />
      </g>
    </svg>
  );
}

function CorridorPillar({ x, width, height, side }) {
  const y = 1000 - height;
  const capitalDirection = side === "left" ? 1 : -1;
  const capitalY = y + 12;
  const ringY = capitalY + 28;
  const shaftY = ringY + 34;
  const shaftHeight = height * 0.7;
  const baseY = Math.min(shaftY + shaftHeight, 904);
  const centerX = x + width / 2;
  const capitalX = x - 10;
  const plinthX = x - 15;

  return (
    <g stroke="#B8860B" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="rgba(184,134,11,0.18)">
      <rect x={capitalX} y={capitalY} width={width + 20} height="15" />
      <path
        d={`M ${x + 6} ${capitalY + 17} C ${centerX - capitalDirection * width * 0.2} ${capitalY + 30}, ${centerX + capitalDirection * width * 0.2} ${capitalY + 30}, ${x + width - 6} ${capitalY + 17}`}
        fill="none"
        opacity="0.55"
      />

      {[0, 1, 2].map((index) => (
        <rect key={`${side}-neck-${x}-${index}`} x={x} y={ringY + index * 10} width={width} height="4" />
      ))}

      <rect x={x + width * 0.08} y={shaftY} width={width * 0.84} height={shaftHeight} />
      <line x1={centerX} y1={shaftY + 14} x2={centerX} y2={shaftY + shaftHeight - 14} opacity="0.3" />

      <rect x={x - 4} y={baseY} width={width + 8} height="8" />
      <rect x={x - 8} y={baseY + 10} width={width + 16} height="10" />
      <rect x={x - 12} y={baseY + 24} width={width + 24} height="12" />
      <rect x={plinthX} y={960} width={width + 30} height="34" />
    </g>
  );
}

function FloorPerspectiveLines() {
  return (
    <svg
      className="absolute bottom-0 left-0 z-[3] h-[40vh] w-full pointer-events-none"
      viewBox="0 0 1000 400"
      preserveAspectRatio="none"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <g stroke="rgba(184,134,11,0.06)" strokeWidth="1">
        {[0, 70, 140, 210, 280, 350].map((x) => (
          <line key={`floor-left-${x}`} x1={x} y1="400" x2="500" y2="0" />
        ))}
        {[1000, 930, 860, 790, 720, 650].map((x) => (
          <line key={`floor-right-${x}`} x1={x} y1="400" x2="500" y2="0" />
        ))}
      </g>
    </svg>
  );
}

function CeilingArch() {
  return (
    <svg
      className="absolute left-0 top-0 z-[4] h-[120px] w-full pointer-events-none"
      viewBox="0 0 1000 120"
      preserveAspectRatio="none"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path d="M 0 0 C 250 80, 750 80, 1000 0" stroke="#B8860B" strokeWidth="1.2" opacity="0.35" fill="none" />
      <path d="M 70 0 C 285 56, 715 56, 930 0" stroke="#B8860B" strokeWidth="0.9" opacity="0.2" fill="none" />
      {Array.from({ length: 9 }, (_, index) => {
        const x = 100 + index * 100;
        const y = 24 + Math.sin((index / 8) * Math.PI) * 42;
        return (
          <rect
            key={`ceiling-arch-diamond-${index}`}
            x={x - 5}
            y={y - 5}
            width="10"
            height="10"
            fill="rgba(184,134,11,0.5)"
            transform={`rotate(45 ${x} ${y})`}
          />
        );
      })}
    </svg>
  );
}

// ===== NEW FEATURE: SRI YANTRA BACKGROUND =====
function SriYantraBackground() {
  const outerPetals = Array.from({ length: 16 }, (_, index) => {
    const angle = index * 22.5;
    const radians = (angle * Math.PI) / 180;
    return {
      id: `outer-${index}`,
      x: 200 + Math.cos(radians) * 115,
      y: 200 + Math.sin(radians) * 115,
      angle,
    };
  });

  const innerPetals = Array.from({ length: 8 }, (_, index) => {
    const angle = index * 45;
    const radians = (angle * Math.PI) / 180;
    return {
      id: `inner-${index}`,
      x: 200 + Math.cos(radians) * 82,
      y: 200 + Math.sin(radians) * 82,
      angle,
    };
  });

  const trianglePath = (r, up = true, rotation = 0) => {
    const points = Array.from({ length: 3 }, (_, index) => {
      const angle = ((up ? -90 : 90) + rotation + index * 120) * (Math.PI / 180);
      return `${200 + Math.cos(angle) * r},${200 + Math.sin(angle) * r}`;
    });
    return `M ${points.join(" L ")} Z`;
  };

  return (
    <motion.div
      className="absolute left-1/2 top-1/2 z-[4] h-[55vh] w-[55vh] -translate-x-1/2 -translate-y-1/2 pointer-events-none"
      animate={{
        rotate: [0, 360],
        opacity: [0.06, 0.12, 0.06],
      }}
      transition={{
        rotate: { duration: 120, repeat: Infinity, ease: 'linear' },
        opacity: { duration: 8, repeat: Infinity, ease: 'easeInOut' },
      }}
      style={{ opacity: 0.08 }}
    >
      <svg viewBox="0 0 400 400" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <g stroke="#B8860B" strokeLinecap="round" strokeLinejoin="round">
          <path d="M 40 40 H 168 M 232 40 H 360 V 168 M 360 232 V 360 H 232 M 168 360 H 40 V 232 M 40 168 V 40" strokeWidth="1" />
          <path d="M 50 50 H 176 M 224 50 H 350 V 176 M 350 224 V 350 H 224 M 176 350 H 50 V 224 M 50 176 V 50" strokeWidth="0.5" />
          <circle cx="200" cy="200" r="140" strokeWidth="0.8" />
          <circle cx="200" cy="200" r="120" strokeWidth="0.6" />
          <circle cx="200" cy="200" r="105" strokeWidth="0.5" />
          {outerPetals.map((petal) => (
            <ellipse
              key={petal.id}
              cx={petal.x}
              cy={petal.y}
              rx="10"
              ry="22"
              fill="rgba(184,134,11,0.15)"
              strokeWidth="0.5"
              transform={`rotate(${petal.angle + 90} ${petal.x} ${petal.y})`}
            />
          ))}
          {innerPetals.map((petal) => (
            <ellipse
              key={petal.id}
              cx={petal.x}
              cy={petal.y}
              rx="10"
              ry="20"
              fill="rgba(184,134,11,0.12)"
              strokeWidth="0.5"
              transform={`rotate(${petal.angle + 90} ${petal.x} ${petal.y})`}
            />
          ))}
          {[90, 70, 50, 30].map((r, index) => (
            <path key={`up-triangle-${r}`} d={trianglePath(r, true, index * 9)} fill="rgba(184,134,11,0.06)" strokeWidth="0.7" />
          ))}
          {[85, 65, 48, 32, 18].map((r, index) => (
            <path key={`down-triangle-${r}`} d={trianglePath(r, false, index * -7)} fill="rgba(184,134,11,0.06)" strokeWidth="0.7" />
          ))}
          <circle cx="200" cy="200" r="4" fill="#FFD700" opacity="0.6" stroke="none" />
        </g>
      </svg>
    </motion.div>
  );
}

// ===== NEW FEATURE: SOUNDWAVE BESIDE HEADING =====
function SoundwaveBars({ bars, side }) {
  return (
    <div
      className="pointer-events-none absolute top-1/2 hidden -translate-y-1/2 items-center min-[900px]:flex"
      style={side === "left" ? { left: -80 } : { right: -80 }}
      aria-hidden="true"
    >
      <span className="block h-px w-16 bg-gradient-to-r from-transparent via-[#B8860B] to-transparent opacity-70" />
      <span className="mx-3 h-2 w-2 rotate-45 border border-[#B8860B] bg-[rgba(184,134,11,0.18)]" />
      <span className="block h-px w-16 bg-gradient-to-r from-transparent via-[#B8860B] to-transparent opacity-70" />
    </div>
  );
}

// ===== NEW FEATURE: CARVED FRIEZE BORDER =====
function CarvedFriezeBorder() {
  const units = Array.from({ length: 40 }, (_, index) => index * 72);
  const mantra = "ॐ नमः शिवाय | ॐ नमः शिवाय | ॐ नमः शिवाय | ॐ नमः शिवाय | ॐ नमः शिवाय |";

  return (
    <div
      className="absolute left-0 z-[10] flex h-[50px] w-full justify-center pointer-events-none"
      style={{ bottom: 65 }}
      aria-label="ॐ नमः शिवाय"
    >
      <div
        className="relative h-full w-[min(760px,calc(100vw-48px))] overflow-hidden"
        style={{
          borderTop: '1px solid rgba(184,134,11,0.42)',
          borderBottom: '1px solid rgba(184,134,11,0.28)',
          background: 'linear-gradient(90deg, transparent, rgba(26,10,0,0.36) 16%, rgba(26,10,0,0.36) 84%, transparent)',
        }}
      >
        <motion.svg
          className="absolute inset-0"
          viewBox="0 0 2880 50"
          width="200%"
          height="50"
          preserveAspectRatio="xMidYMid slice"
          xmlns="http://www.w3.org/2000/svg"
          animate={{ x: ['0%', '-50%'] }}
          transition={{ duration: 60, repeat: Infinity, ease: 'linear' }}
          style={{ opacity: 0.28 }}
          aria-hidden="true"
        >
          <g stroke="#B8860B" strokeWidth="0.7" fill="rgba(184,134,11,0.08)" strokeLinecap="round" strokeLinejoin="round">
            {units.map((x) => (
              <g key={`frieze-separator-${x}`} transform={`translate(${x} 0)`}>
                <rect x="70" y="5" width="2" height="40" />
                <rect x="66" y="4" width="10" height="4" />
                <rect x="66" y="42" width="10" height="4" />
              </g>
            ))}
          </g>
        </motion.svg>

        <div
          className="absolute inset-y-0 left-0 z-[1] w-12"
          style={{ background: 'linear-gradient(90deg, rgba(18,6,31,0.95), transparent)' }}
          aria-hidden="true"
        />
        <div
          className="absolute inset-y-0 right-0 z-[1] w-12"
          style={{ background: 'linear-gradient(270deg, rgba(18,6,31,0.95), transparent)' }}
          aria-hidden="true"
        />
        <motion.div
          className="relative z-[2] flex h-full w-max items-center"
          initial={{ x: '0%' }}
          animate={{ x: ['0%', '-50%'] }}
          transition={{ duration: 22, repeat: Infinity, ease: 'linear' }}
          style={{
            willChange: 'transform',
            fontFamily: 'serif',
            fontSize: '14px',
            color: 'rgba(184,134,11,0.68)',
            letterSpacing: '0.3em',
            whiteSpace: 'nowrap',
          }}
        >
          <span className="pr-12">{mantra}</span>
          <span className="pr-12">{mantra}</span>
        </motion.div>
      </div>
    </div>
  );
}

// ===== NEW FEATURE: INTRO SEQUENCE =====
function CinematicIntroOverlay({ introComplete, introPhase }) {
  return (
    <AnimatePresence>
      {!introComplete && (
        <motion.div
          style={{
            position: 'fixed',
            inset: 0,
            background: '#000000',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
        >
          {introPhase >= 1 && (
            <motion.div
              style={{
                position: 'absolute',
                width: '4px',
                height: '4px',
                borderRadius: '50%',
                background: '#FFD700',
                boxShadow: '0 0 20px #FFD700',
              }}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
            />
          )}

          {introPhase >= 2 && (
            <motion.div
              style={{
                position: 'absolute',
                width: '300px',
                height: '300px',
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(184,134,11,0.4) 0%, transparent 70%)',
                filter: 'blur(40px)',
              }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 3, opacity: 1 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            />
          )}

          {introPhase >= 2 && (
            <motion.div
              style={{
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 0.35, scale: 1 }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
            >
              <svg viewBox="0 0 200 350" width="180" height="auto" aria-hidden="true">
                <path
                  d="M 85,340 C 75,280 72,220 75,170 C 78,120 88,80 100,45 C 112,80 122,120 125,170 C 128,220 125,280 115,340 Z"
                  fill="rgba(184,134,11,0.15)"
                  stroke="#B8860B"
                  strokeWidth="1"
                />
                <circle cx="100" cy="35" r="8" fill="rgba(184,134,11,0.3)" stroke="#B8860B" strokeWidth="1" />
                <line x1="100" y1="43" x2="100" y2="60" stroke="#B8860B" strokeWidth="1.5" />
              </svg>
            </motion.div>
          )}

          {introPhase >= 3 && (
            <motion.div
              style={{
                position: 'absolute',
                textAlign: 'center',
                bottom: '35%',
              }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              <div
                style={{
                  fontFamily: 'serif',
                  fontSize: '22px',
                  color: 'rgba(184,134,11,0.8)',
                  letterSpacing: '0.3em',
                  marginBottom: '12px',
                }}
              >
                ॐ
              </div>
              <div
                style={{
                  fontFamily: 'Inter',
                  fontSize: '9px',
                  color: 'rgba(184,134,11,0.5)',
                  letterSpacing: '0.4em',
                }}
              >
                INITIALIZING 3DITA SYSTEM
              </div>
            </motion.div>
          )}

          {introPhase >= 4 && (
            <motion.div
              style={{
                position: 'absolute',
                textAlign: 'center',
              }}
              initial={{ opacity: 0, scale: 1.1 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8 }}
            >
              <div
                style={{
                  fontFamily: 'Georgia, serif',
                  fontSize: 'clamp(2rem, 5vw, 4rem)',
                  background: 'linear-gradient(180deg, #FFD700, #B8860B)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '0.05em',
                  filter: 'drop-shadow(0 0 30px rgba(184,134,11,0.8))',
                }}
              >
                3DITA
              </div>
              <div
                style={{
                  fontFamily: 'Inter',
                  fontSize: '10px',
                  color: 'rgba(184,134,11,0.6)',
                  letterSpacing: '0.35em',
                  marginTop: '8px',
                }}
              >
                TEMPLE RECONSTRUCTION ENGINE
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ===== NEW FEATURE: CURSOR TRAIL =====
function GoldCursorTrail({ cursorPos, cursorTrail, isHoveringButton, clickParticles }) {
  return (
    <>
      <div
        style={{
          position: 'fixed',
          left: cursorPos.x - (isHoveringButton ? 12 : 7),
          top: cursorPos.y - (isHoveringButton ? 12 : 7),
          width: isHoveringButton ? '24px' : '14px',
          height: isHoveringButton ? '24px' : '14px',
          borderRadius: '50%',
          border: `1.5px solid ${isHoveringButton ? '#FF6B35' : '#B8860B'}`,
          background: isHoveringButton ? 'rgba(255,107,53,0.2)' : 'rgba(184,134,11,0.15)',
          pointerEvents: 'none',
          zIndex: 9999,
          transition: 'width 0.2s, height 0.2s, border-color 0.2s',
          mixBlendMode: 'screen',
        }}
      />
      <div
        style={{
          position: 'fixed',
          left: cursorPos.x - 2,
          top: cursorPos.y - 2,
          width: '4px',
          height: '4px',
          borderRadius: '50%',
          background: isHoveringButton ? '#FF6B35' : '#FFD700',
          pointerEvents: 'none',
          zIndex: 9999,
        }}
      />
      {cursorTrail.map((pos, i) => (
        <div
          key={`cursor-trail-${i}`}
          style={{
            position: 'fixed',
            left: pos.x - (5 - i * 0.4),
            top: pos.y - (5 - i * 0.4),
            width: `${Math.max(10 - i * 1.2, 2)}px`,
            height: `${Math.max(10 - i * 1.2, 2)}px`,
            borderRadius: '50%',
            background: '#B8860B',
            opacity: Math.max(0.5 - i * 0.06, 0.05),
            pointerEvents: 'none',
            zIndex: 9998,
            transition: 'left 0.05s, top 0.05s',
          }}
        />
      ))}
      {clickParticles.map((p) => (
        <motion.div
          key={p.id}
          style={{
            position: 'fixed',
            left: p.x,
            top: p.y,
            width: '5px',
            height: '5px',
            borderRadius: '50%',
            background: '#FFD700',
            pointerEvents: 'none',
            zIndex: 9999,
          }}
          animate={{
            x: Math.cos(p.angle) * p.distance,
            y: Math.sin(p.angle) * p.distance,
            opacity: [1, 0],
            scale: [1, 0],
          }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      ))}
    </>
  );
}

function CentralNagaraTemple() {
  const shikharaBands = [
    { y: 130, w: 32 },
    { y: 158, w: 44 },
    { y: 188, w: 58 },
    { y: 220, w: 72 },
    { y: 254, w: 88 },
    { y: 290, w: 104 },
    { y: 328, w: 120 },
    { y: 368, w: 136 },
    { y: 410, w: 152 },
    { y: 454, w: 168 },
  ];

  return (
    <motion.div
      style={{
        position: 'absolute',
        left: '50%',
        top: '52%',
        transform: 'translate(-50%, -50%)',
        height: '85vh',
        width: 'auto',
        zIndex: 5,
        pointerEvents: 'none',
        opacity: 0.38,
      }}
      animate={{
        filter: [
          'drop-shadow(0 0 30px rgba(184,134,11,0.4))',
          'drop-shadow(0 0 120px rgba(184,134,11,1.0))',
          'drop-shadow(0 0 30px rgba(184,134,11,0.4))',
        ],
      }}
      transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
    >
      <svg
        viewBox="0 0 400 720"
        height="100%"
        width="auto"
        preserveAspectRatio="xMidYMid meet"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        style={{ overflow: 'visible' }}
      >
        <g stroke="#B8860B" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="rgba(184,134,11,0.18)">
          <path d="M 200 18 L 208 50 L 200 72 L 192 50 Z" />
          <ellipse cx="200" cy="82" rx="38" ry="10" />
          <path d="M 176 92 C 188 104, 212 104, 224 92 L 218 122 L 182 122 Z" />
          <path d="M 112 494 C 96 404, 104 300, 128 220 C 146 160, 174 116, 200 88 C 226 116, 254 160, 272 220 C 296 300, 304 404, 288 494 Z" />
          <path d="M 145 486 C 132 398, 140 302, 158 230 C 170 176, 186 132, 200 102 C 214 132, 230 176, 242 230 C 260 302, 268 398, 255 486 Z" fill="rgba(184,134,11,0.18)" />
          {shikharaBands.map((band) => (
            <path key={`central-band-${band.y}`} d={`M ${200 - band.w / 2} ${band.y} C ${176} ${band.y + 6}, ${224} ${band.y + 6}, ${200 + band.w / 2} ${band.y}`} fill="none" strokeWidth="0.9" />
          ))}

          <path d="M 72 500 C 58 428, 64 354, 84 300 C 98 264, 116 238, 132 218 C 148 238, 166 264, 180 300 C 200 354, 206 428, 192 500 Z" />
          <path d="M 208 500 C 194 428, 200 354, 220 300 C 234 264, 252 238, 268 218 C 284 238, 302 264, 316 300 C 336 354, 342 428, 328 500 Z" />
          {[270, 312, 356, 402].map((y) => (
            <g key={`uru-band-${y}`}>
              <path d={`M 94 ${y} C 114 ${y + 5}, 150 ${y + 5}, 170 ${y}`} fill="none" opacity="0.8" strokeWidth="0.9" />
              <path d={`M 230 ${y} C 250 ${y + 5}, 286 ${y + 5}, 306 ${y}`} fill="none" opacity="0.8" strokeWidth="0.9" />
            </g>
          ))}

          <path d="M 58 498 L 342 498 L 330 528 L 70 528 Z" />
          <path d="M 82 528 L 318 528 L 318 594 L 82 594 Z" />
          <path d="M 122 548 C 144 526, 176 526, 198 548 L 198 594 L 122 594 Z" fill="rgba(184,134,11,0.18)" />
          <path d="M 202 548 C 224 526, 256 526, 278 548 L 278 594 L 202 594 Z" fill="rgba(184,134,11,0.18)" />
          <rect x="106" y="594" width="188" height="48" />
          {[124, 164, 236, 276].map((x) => (
            <g key={`central-pillar-${x}`}>
              <rect x={x - 6} y="542" width="12" height="88" />
              <rect x={x - 12} y="534" width="24" height="8" />
              <rect x={x - 14} y="630" width="28" height="8" />
            </g>
          ))}
          <rect x="72" y="642" width="256" height="18" />
          <rect x="50" y="660" width="300" height="18" />
          <rect x="28" y="678" width="344" height="16" />
          <rect x="124" y="694" width="152" height="10" />
          <rect x="104" y="704" width="192" height="10" />
        </g>
      </svg>
    </motion.div>
  );
}

function ForegroundDiya({ side }) {
  const placement = side === "left" ? { left: 120 } : { right: 120 };

  return (
    <div className="absolute bottom-[60px] z-[7] pointer-events-none" style={placement}>
      <svg viewBox="-45 -70 90 95" width="90" height="95" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <linearGradient id={`diyaBowlGradient-${side}`} x1="0" y1="-10" x2="0" y2="10" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#8B4513" />
            <stop offset="100%" stopColor="#5C2E00" />
          </linearGradient>
          <linearGradient id={`diyaFlameGradient-${side}`} x1="0" y1="-30" x2="0" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFD700" />
            <stop offset="60%" stopColor="#FF6B35" />
            <stop offset="100%" stopColor="#FF4500" />
          </linearGradient>
          <radialGradient id={`diyaGoldGlow-${side}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FFD700" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#FFD700" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="0" cy="-30" r="30" fill={`url(#diyaGoldGlow-${side})`} style={{ filter: 'blur(15px)' }} opacity="0.5" />
        <ellipse cx="0" cy="8" rx="28" ry="10" fill={`url(#diyaBowlGradient-${side})`} stroke="#B8860B" strokeWidth="1" />
        <ellipse cx="0" cy="4" rx="20" ry="6" fill="rgba(255,165,0,0.4)" />
        <rect x="-1" y="-4" width="2" height="8" fill="#8B4513" />
        <motion.g
          animate={{
            scaleY: [1, 1.15, 0.9, 1.1, 1],
            scaleX: [1, 0.9, 1.05, 0.95, 1],
            x: [0, 2, -1, 2, 0],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          style={{ transformOrigin: 'center bottom' }}
        >
          <path d="M 0,0 C 8,-10 8,-25 0,-30 C -8,-25 -8,-10 0,0" fill={`url(#diyaFlameGradient-${side})`} />
          <path d="M 0,0 C 4.8,-6 4.8,-15 0,-18 C -4.8,-15 -4.8,-6 0,0" fill="#FFD700" opacity="0.9" />
        </motion.g>
      </svg>
    </div>
  );
}

function TempleCorridorScene({ springX, springY }) {
  const emberParticles = [
    { x: -58, y: 34, s: 3, dx: -22, dy: -28, d: 0 },
    { x: -38, y: 28, s: 2.5, dx: -15, dy: -38, d: 0.35 },
    { x: -18, y: 42, s: 2.8, dx: -6, dy: -34, d: 0.7 },
    { x: 12, y: 36, s: 3.2, dx: 7, dy: -42, d: 0.2 },
    { x: 34, y: 30, s: 2.4, dx: 16, dy: -32, d: 0.55 },
    { x: 56, y: 38, s: 3, dx: 24, dy: -36, d: 0.9 },
    { x: -70, y: 54, s: 2, dx: -30, dy: -18, d: 1.1 },
    { x: 72, y: 52, s: 2, dx: 32, dy: -20, d: 1.3 },
  ];

  return (
    <motion.div
      className="absolute inset-0 z-[5] pointer-events-none"
      style={{ transformStyle: 'preserve-3d', x: springX, y: springY }}
    >
      <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" className="h-full w-full" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <radialGradient id="corridorSacredGlow" cx="50%" cy="45%" r="36%">
            <stop offset="0%" stopColor="#FFD700" stopOpacity="0.4" />
            <stop offset="45%" stopColor="#B8860B" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#B8860B" stopOpacity="0" />
          </radialGradient>
        </defs>

        <motion.circle
          cx="500"
          cy="450"
          r="270"
          fill="url(#corridorSacredGlow)"
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        />

        <g stroke="#B8860B" strokeWidth="1" opacity="0.15" strokeLinecap="round" strokeLinejoin="round">
          <path d="M 20 0 C 160 110, 280 170, 500 170 C 720 170, 840 110, 980 0" />
          <path d="M 72 0 C 196 82, 304 128, 500 128 C 696 128, 804 82, 928 0" />
          <path d="M 140 0 C 248 58, 340 88, 500 88 C 660 88, 752 58, 860 0" />
          {Array.from({ length: 18 }, (_, index) => {
            const x = 80 + index * 50;
            return (
              <g key={`arch-ornament-${index}`}>
                <path d={`M ${x} 22 L ${x + 13} 38 L ${x} 54 L ${x - 13} 38 Z`} fill="rgba(184,134,11,0.14)" />
                <circle cx={x} cy="38" r="3" fill="#B8860B" opacity="0.65" />
              </g>
            );
          })}
        </g>

        <CorridorPillar x={0} width={60} height={1000} side="left" />
        <CorridorPillar x={80} width={40} height={800} side="left" />
        <CorridorPillar x={130} width={25} height={650} side="left" />
        <CorridorPillar x={940} width={60} height={1000} side="right" />
        <CorridorPillar x={880} width={40} height={800} side="right" />
        <CorridorPillar x={845} width={25} height={650} side="right" />

      </svg>

      <motion.div
        className="absolute left-1/2 top-[45%] -translate-x-1/2 -translate-y-1/2"
        style={{ width: 520, x: springX, y: springY, zIndex: 5 }}
        animate={{ opacity: [0.16, 0.22, 0.16], scale: [0.98, 1.02, 0.98] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        <TempleSilhouette width={520} opacity={0.22} blur="0px" />
      </motion.div>

      <div className="absolute left-1/2 top-[45%] h-[120px] w-[220px] -translate-x-1/2 translate-y-[66px]">
        {emberParticles.map((ember, index) => (
          <motion.span
            key={`distant-ember-${index}`}
            className="absolute rounded-full"
            style={{
              left: `calc(50% + ${ember.x}px)`,
              top: `calc(50% + ${ember.y}px)`,
              width: ember.s,
              height: ember.s,
              background: '#FF6B35',
              boxShadow: '0 0 8px #FF6B35',
            }}
            animate={{
              x: [0, ember.dx, ember.dx * 1.2],
              y: [0, ember.dy, ember.dy - 10],
              opacity: [0, 0.95, 0],
              scale: [0.7, 1.25, 0.45],
            }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeOut', delay: ember.d }}
          />
        ))}
      </div>
    </motion.div>
  );
}

function CornerMandala({ placement }) {
  const positions = {
    "top-left": { top: 0, left: 0, transform: "none" },
    "top-right": { top: 0, right: 0, transform: "scaleX(-1)" },
    "bottom-left": { bottom: 0, left: 0, transform: "scaleY(-1)" },
    "bottom-right": { bottom: 0, right: 0, transform: "scale(-1, -1)" },
  };

  return (
    <motion.div
      className="absolute z-[6] opacity-14 pointer-events-none"
      style={{ width: 90, height: 90, ...positions[placement], willChange: 'transform, opacity' }}
      animate={{ rotate: [0, 360] }}
      transition={{ duration: 26, repeat: Infinity, ease: 'linear' }}
    >
      <svg viewBox="0 0 90 90" width="90" height="90" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <g stroke="#B8860B" strokeWidth="1" fill="none">
          <path d="M10 45C10 26 26 10 45 10" />
          <path d="M10 60C10 28 28 10 60 10" />
          <path d="M10 75C10 40 40 10 75 10" />
          <path d="M22 45C22 26 45 10 68 10" />
        </g>
      </svg>
    </motion.div>
  );
}

function ConstellationOverlay() {
  const stars = [
    { x: 12, y: 18 },
    { x: 23, y: 32 },
    { x: 36, y: 24 },
    { x: 48, y: 40 },
    { x: 62, y: 22 },
    { x: 75, y: 30 },
    { x: 84, y: 18 },
    { x: 68, y: 12 },
  ];

  const connections = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 4],
    [4, 5],
    [5, 7],
    [2, 6],
  ];

  return (
    <motion.div className="absolute inset-0 z-[3] pointer-events-none">
      <motion.svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full" aria-hidden="true"
        animate={{ opacity: [0.04, 0.14, 0.04] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
      >
        {connections.map(([start, end], index) => (
          <line
            key={`const-line-${index}`}
            x1={`${stars[start].x}`}
            y1={`${stars[start].y}`}
            x2={`${stars[end].x}`}
            y2={`${stars[end].y}`}
            stroke="rgba(184,134,11,0.08)"
            strokeWidth="0.6"
            strokeDasharray="4 8"
          />
        ))}
        {stars.map((star, index) => (
          <circle
            key={`const-star-${index}`}
            cx={star.x}
            cy={star.y}
            r="1.5"
            fill="#B8860B"
            opacity="0.6"
          />
        ))}
      </motion.svg>
    </motion.div>
  );
}

export default function HeroSection({ onOpen }) {
  const [isMounted, setIsMounted] = useState(false);
  const [viewportHeight, setViewportHeight] = useState(() =>
    typeof window !== 'undefined' ? window.innerHeight + 120 : 980
  );
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  // ===== NEW FEATURE: INTRO SEQUENCE =====
  const [introComplete, setIntroComplete] = useState(false);
  const [introPhase, setIntroPhase] = useState(0);
  // ===== NEW FEATURE: CURSOR TRAIL =====
  const [cursorPos, setCursorPos] = useState({ x: -100, y: -100 });
  const [cursorTrail, setCursorTrail] = useState(
    Array(8).fill({ x: -100, y: -100 })
  );
  const [isHoveringButton, setIsHoveringButton] = useState(false);
  const [clickParticles, setClickParticles] = useState([]);

  useEffect(() => {
    setIsMounted(true);
    const handleResize = () => setViewportHeight(window.innerHeight + 120);
    window.addEventListener('resize', handleResize);

    const handleMouse = (e) => {
      setMousePos({
        x: (e.clientX / window.innerWidth - 0.5) * 20,
        y: (e.clientY / window.innerHeight - 0.5) * 10,
      });
    };

    window.addEventListener('mousemove', handleMouse);
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouse);
    };
  }, []);

  // ===== NEW FEATURE: INTRO SEQUENCE =====
  useEffect(() => {
    if (sessionStorage.getItem('3dita_intro_seen')) {
      setIntroComplete(true);
      return;
    }

    const timers = [
      setTimeout(() => setIntroPhase(1), 100),
      setTimeout(() => setIntroPhase(2), 900),
      setTimeout(() => setIntroPhase(3), 1800),
      setTimeout(() => setIntroPhase(4), 2600),
      setTimeout(() => {
        setIntroComplete(true);
        sessionStorage.setItem('3dita_intro_seen', 'true');
      }, 3800),
    ];

    return () => timers.forEach((timer) => clearTimeout(timer));
  }, []);

  // ===== NEW FEATURE: CURSOR TRAIL =====
  useEffect(() => {
    const handleMouseMove = (e) => {
      setCursorPos({ x: e.clientX, y: e.clientY });
      setCursorTrail((prev) => {
        const newTrail = [{ x: e.clientX, y: e.clientY }, ...prev.slice(0, 7)];
        return newTrail;
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // ===== NEW FEATURE: CURSOR TRAIL =====
  useEffect(() => {
    const handleClick = (e) => {
      const burst = Array.from({ length: 6 }, (_, i) => ({
        id: Date.now() + i,
        x: e.clientX,
        y: e.clientY,
        angle: (i / 6) * Math.PI * 2,
        distance: Math.random() * 40 + 20,
      }));
      setClickParticles(burst);
      setTimeout(() => setClickParticles([]), 600);
    };

    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, []);

  const springX = useSpring(mousePos.x * 0.4, { stiffness: 50, damping: 20 });
  const springY = useSpring(mousePos.y * 0.3, { stiffness: 50, damping: 20 });
  const blobAX = useSpring(mousePos.x * 0.6, { stiffness: 50, damping: 20 });
  const blobAY = useSpring(mousePos.y * 0.4, { stiffness: 50, damping: 20 });
  const blobBX = useSpring(mousePos.x * -0.5, { stiffness: 50, damping: 20 });
  const blobBY = useSpring(mousePos.y * 0.3, { stiffness: 50, damping: 20 });
  const blobCX = useSpring(mousePos.x * 0.3, { stiffness: 50, damping: 20 });
  const blobCY = useSpring(mousePos.y * -0.2, { stiffness: 50, damping: 20 });
  const stars = useMemo(
    () =>
      Array.from({ length: 100 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        top: Math.random() * 100,
        size: Math.random() * 1.8 + 0.4,
        baseOpacity: Math.random() * 0.35 + 0.08,
        twinkleDuration: Math.random() * 4 + 2,
        delay: Math.random() * 5,
      })),
    []
  );

  const particles = useMemo(
    () =>
      Array.from({ length: 45 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        size:
          i < 30
            ? Math.random() * 2 + 1
            : i < 42
            ? Math.random() * 3 + 2
            : Math.random() * 5 + 4,
        duration: Math.random() * 10 + 6,
        delay: Math.random() * 12,
        drift: (Math.random() - 0.5) * 80,
        type: i < 34 ? "dust" : "ember",
      })),
    []
  );

  // ===== NEW FEATURE: SOUNDWAVE BESIDE HEADING =====
  const barHeights = useMemo(
    () =>
      Array.from({ length: 10 }, () => ({
        id: Math.random(),
        baseHeight: Math.random() * 20 + 10,
        peakScale: Math.random() * 2 + 0.5,
        duration: Math.random() * 1.2 + 0.6,
        delay: Math.random() * 0.8,
      })),
    []
  );

  return (
    <section className="relative min-h-screen overflow-hidden bg-[#12061F] text-white" style={{ perspective: 1400, perspectiveOrigin: '50% 30%', cursor: 'none' }}>
      {/* ===== NEW FEATURE: INTRO SEQUENCE ===== */}
      <CinematicIntroOverlay introComplete={introComplete} introPhase={introPhase} />

      <div
        className="absolute inset-0 z-[1]"
        style={{
          background: 'radial-gradient(circle at 20% 18%, rgba(255, 186, 70, 0.14), transparent 24%), radial-gradient(circle at 72% 25%, rgba(255, 107, 53, 0.08), transparent 28%), radial-gradient(circle at 50% 52%, rgba(118, 26, 117, 0.25), transparent 40%)',
          opacity: 1,
          willChange: 'opacity',
        }}
      />

      <ConstellationOverlay />
      <FloorPerspectiveLines />
      <CeilingArch />

      <motion.div className="absolute inset-0 z-[3] pointer-events-none overflow-hidden" style={{ willChange: 'transform, opacity' }}>
        <motion.div
          className="absolute h-[44vh] w-[50vw] rounded-full"
          style={{
            top: '-18%',
            left: '-12%',
            background: 'radial-gradient(circle, rgba(255,200,80,0.16) 0%, transparent 68%)',
            filter: 'blur(90px)',
            x: blobAX,
            y: blobAY,
          }}
          animate={{ x: [-30, 42, -30], y: [0, 30, 0], opacity: [0.2, 0.7, 0.2] }}
          transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute h-[38vh] w-[44vw] rounded-full"
          style={{
            top: '6%',
            right: '-16%',
            background: 'radial-gradient(circle, rgba(255,107,53,0.1) 0%, transparent 70%)',
            filter: 'blur(112px)',
            x: blobBX,
            y: blobBY,
          }}
          animate={{ x: [22, -32, 22], y: [10, -18, 10], opacity: [0.22, 0.66, 0.22] }}
          transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute h-[34vh] w-[64vw] rounded-full"
          style={{
            bottom: '-16%',
            left: '18%',
            background: 'radial-gradient(circle, rgba(120, 38, 89, 0.12) 0%, transparent 70%)',
            filter: 'blur(98px)',
            x: blobCX,
            y: blobCY,
          }}
          animate={{ scale: [1, 1.22, 1], opacity: [0.18, 0.48, 0.18] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        />
      </motion.div>

      <div className="absolute inset-0 z-[4] pointer-events-none">
        {stars.map((star) => (
          <div
            key={star.id}
            style={{
              position: 'absolute',
              left: `${star.left}%`,
              top: `${star.top}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              borderRadius: '50%',
              background: 'white',
              opacity: star.baseOpacity,
              pointerEvents: 'none',
            }}
          />
        ))}
      </div>

      <div className="absolute inset-0 z-[4] pointer-events-none">
        {particles.map((p) => (
          <motion.div
            key={p.id}
            style={{
              position: 'absolute',
              left: `${p.left}%`,
              bottom: '-8px',
              width: `${p.size}px`,
              height: `${p.size}px`,
              borderRadius: '50%',
              background: p.type === 'ember' ? '#FF6B35' : '#B8860B',
              boxShadow: p.type === 'ember' ? '0 0 5px rgba(255,107,53,0.6)' : 'none',
              pointerEvents: 'none',
            }}
            animate={{
              y: [0, -(window.innerHeight + 100)],
              x: [0, p.drift],
              opacity: [0, 0.85, 0.85, 0],
            }}
            transition={{
              duration: p.duration,
              delay: p.delay,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ))}
      </div>

      <motion.div
        className="absolute top-0 left-1/2 z-[4] -translate-x-1/2 pointer-events-none"
        style={{ width: 300, height: 300, opacity: 0.5 }}
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 40, repeat: Infinity, ease: 'linear' }}
      >
        <svg viewBox="0 0 300 300" width="300" height="300" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="150" cy="150" r="140" stroke="#B8860B" strokeWidth="0.5" opacity="0.2" fill="none" />
          <circle cx="150" cy="150" r="110" stroke="#B8860B" strokeWidth="0.8" opacity="0.15" fill="none" />
          <circle cx="150" cy="150" r="80" stroke="#B8860B" strokeWidth="0.5" opacity="0.1" fill="none" />
          {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => {
            const radians = (angle * Math.PI) / 180;
            const x = 150 + Math.cos(radians) * 140;
            const y = 150 + Math.sin(radians) * 140;
            return (
              <line
                key={angle}
                x1="150"
                y1="150"
                x2={x}
                y2={y}
                stroke="#B8860B"
                strokeWidth="0.5"
                opacity="0.12"
              />
            );
          })}
          {[...Array(16)].map((_, index) => {
            const angle = (index * 22.5) * (Math.PI / 180);
            const cx = 150 + Math.cos(angle) * 110;
            const cy = 150 + Math.sin(angle) * 110;
            return (
              <rect
                key={`diamond-${index}`}
                x={cx - 3}
                y={cy - 3}
                width="6"
                height="6"
                fill="rgba(184,134,11,0.15)"
                stroke="#B8860B"
                strokeWidth="0.5"
                transform={`rotate(45 ${cx} ${cy})`}
              />
            );
          })}
        </svg>
      </motion.div>

      <div className="absolute left-1/2 top-[6%] z-[5] -translate-x-1/2 pointer-events-none">
        {lightRays.map((ray, index) => (
          <motion.div
            key={ray.angle}
            className="absolute"
            style={{
              left: '50%',
              top: 0,
              width: '1.8px',
              height: ray.height,
              background: 'linear-gradient(180deg, rgba(255,215,0,0.55) 0%, rgba(255,215,0,0.12) 55%, transparent 100%)',
              transformOrigin: 'top center',
              transform: `translateX(-50%) rotate(${ray.angle}deg)`,
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{ opacity: [0.15, 0.76, 0.15], scaleY: [0.82, 1.18, 0.82] }}
            transition={{ duration: 3.4 + index * 0.6, repeat: Infinity, ease: 'easeInOut', delay: index * 0.4 }}
          />
        ))}
      </div>

      <TempleCorridorScene springX={springX} springY={springY} />
      {/* ===== NEW FEATURE: SRI YANTRA BACKGROUND ===== */}
      <SriYantraBackground />
      <CentralNagaraTemple />
      <ForegroundDiya side="left" />
      <ForegroundDiya side="right" />

      <CornerMandala placement="top-left" />
      <CornerMandala placement="top-right" />

      <div
        className="absolute inset-0 z-[8] pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 120% 110% at 50% 50%, transparent 40%, rgba(8,3,18,0.32) 72%, rgba(8,3,18,0.92) 100%)',
          willChange: 'opacity',
        }}
      />

      <AnimatePresence>
        {isMounted && (
          <div
            style={{
              position: 'relative',
              zIndex: 30,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100vh',
              textAlign: 'center',
              padding: '0 32px',
              pointerEvents: 'none',
            }}
          >
            <motion.div
              className="relative flex flex-col items-center justify-center w-full max-w-6xl"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.75, ease: 'easeOut' }}
              style={{
                background: 'radial-gradient(ellipse 52% 64% at 50% 48%, rgba(18,7,31,0.78) 0%, rgba(18,7,31,0.48) 42%, transparent 72%)',
              }}
            >
              <motion.div
                className="relative inline-flex items-center gap-3 rounded-full uppercase text-[#F5D67D] shadow-[0_0_36px_rgba(255,196,93,0.16)]"
                initial={{ opacity: 0, y: -28, scale: 0.92 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.72, ease: 'easeOut' }}
                style={{
                  willChange: 'transform, opacity',
                  fontSize: '12px',
                  padding: '9px 24px',
                  letterSpacing: '0.18em',
                  border: '1px solid rgba(184,134,11,0.9)',
                  background: 'rgba(184,134,11,0.15)',
                }}
              >
                <span className="inline-flex h-2.5 w-2.5 rounded-full bg-[#FF7B35] shadow-[0_0_14px_rgba(255,107,53,0.7)]" />
                DIGITAL HERITAGE INTERFACE
              </motion.div>

              {/* ===== NEW FEATURE: SOUNDWAVE BESIDE HEADING ===== */}
              <div className="relative mt-8">
                <SoundwaveBars bars={barHeights} side="left" />
                <SoundwaveBars bars={barHeights} side="right" />
                <motion.h1
                  className="max-w-[860px] text-transparent"
                  style={{
                    fontFamily: 'Georgia, Cambria, serif',
                    fontSize: 'clamp(3.2rem, 6.5vw, 5.8rem)',
                    background: 'linear-gradient(180deg, #FFD700 0%, #D4A017 40%, #B8860B 70%, #7A5200 100%)',
                    WebkitBackgroundClip: 'text',
                    backgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    filter: 'drop-shadow(0 6px 14px rgba(0,0,0,0.95))',
                    maxWidth: '860px',
                    marginBottom: '22px',
                  }}
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.55, delay: 0.24 }}
                >
                  3DITA Temple Reconstruction
                </motion.h1>
              </div>

              <motion.p
                className="mt-8 max-w-[680px]"
                style={{
                  color: 'rgba(255,248,240,0.88)',
                  fontSize: 'clamp(1rem, 2vw, 1.125rem)',
                  fontWeight: 400,
                  letterSpacing: '0.07em',
                  fontFamily: 'Inter, Arial, sans-serif',
                  lineHeight: '1.9',
                  textShadow: '0 2px 12px rgba(0,0,0,0.75)',
                }}
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.9, delay: 0.78 }}
              >
                AI-Powered Reconstruction of Ancient Indian Temple Architecture
              </motion.p>

              <motion.div
                className="my-8"
                initial={{ opacity: 0, scale: 0.94, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.9, delay: 1.05, ease: 'easeOut' }}
              >
                <motion.button
                  type="button"
                  onClick={onOpen}
                  onMouseEnter={() => setIsHoveringButton(true)}
                  onMouseLeave={() => setIsHoveringButton(false)}
                  whileHover={{ scale: 1.06 }}
                  whileTap={{ scale: 0.96 }}
                  className="relative overflow-hidden rounded-full border border-[rgba(255,255,255,0.18)] bg-gradient-to-r from-[#FF8B52] via-[#FF5E29] to-[#D73E0F] px-[58px] py-[18px] text-white font-semibold tracking-[0.09em] shadow-[0_20px_46px_rgba(255,111,53,0.24)]"
                  style={{ fontSize: '1.05rem', fontFamily: 'Inter, Arial, sans-serif', fontWeight: 600, padding: '16px 40px', willChange: 'transform', pointerEvents: 'auto' }}
                >
                  <motion.div
                    className="absolute inset-0"
                    style={{
                      background: 'linear-gradient(110deg, transparent 28%, rgba(255,255,255,0.36) 52%, transparent 74%)',
                      backgroundSize: '240% 100%',
                      pointerEvents: 'none',
                    }}
                    initial={{ backgroundPosition: '-120% 0%' }}
                    whileHover={{ backgroundPosition: '220% 0%' }}
                    transition={{ duration: 0.55, ease: 'easeOut' }}
                  />
                  <span className="relative inline-flex items-center gap-3">
                    <span>Begin Reconstruction</span>
                    <motion.span
                      className="inline-block"
                      whileHover={{ x: 6 }}
                      transition={{ duration: 0.26, ease: 'easeOut' }}
                      style={{ willChange: 'transform' }}
                    >
                      →
                    </motion.span>
                  </span>
                </motion.button>
              </motion.div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ===== NEW FEATURE: CARVED FRIEZE BORDER ===== */}
      <CarvedFriezeBorder />

      <motion.div
        className="absolute bottom-[48px] left-1/2 z-[15] flex -translate-x-1/2 flex-col items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.6, duration: 1.1 }}
        style={{ willChange: 'transform, opacity' }}
      >
        <motion.span
          className="block h-[40px] w-[1px] bg-gradient-to-b from-transparent to-[#F8D473]"
          animate={{ scaleY: [0, 1, 0], opacity: [0, 0.72, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          style={{ transformOrigin: 'top', willChange: 'transform, opacity' }}
        />
        <motion.svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="stroke-[#F8D473]"
          animate={{ y: [0, 10, 0], opacity: [0.45, 1, 0.45] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
          style={{ willChange: 'transform, opacity' }}
        >
          <path d="M6 9L12 15L18 9" stroke="#F8D473" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
        <span className="text-[11px] tracking-[0.25em] text-[rgba(184,134,11,0.8)] font-sans">SCROLL TO EXPLORE</span>
      </motion.div>

      {/* ===== NEW FEATURE: CURSOR TRAIL ===== */}
      <GoldCursorTrail
        cursorPos={cursorPos}
        cursorTrail={cursorTrail}
        isHoveringButton={isHoveringButton}
        clickParticles={clickParticles}
      />
    </section>
  );
}
