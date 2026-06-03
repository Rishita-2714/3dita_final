import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { DoubleSide, Vector3 } from "three";
import MandalaSpinner from "./MandalaSpinner";
import { useModelLoader } from "../hooks/useModelLoader";

const MAX_RENDERED_POINTS = 900000;
const POINT_SIZE = 0.0085;

function PointMesh({ geometry, mode, hasVertexColors, colorOverride }) {
  const useVertexColors = mode !== "added_context" && hasVertexColors;
  const color = useVertexColors
    ? "#FFFFFF"
    : colorOverride ||
      (mode === "before"
      ? "#B8860B"
      : mode === "added"
        ? "#00FF40"
        : mode === "added_context"
          ? "#263529"
        : "#FF6B35");
  const opacity = mode === "added_context" ? 0.24 : 0.95;
  const size = mode === "added" ? POINT_SIZE * 1.9 : POINT_SIZE;

  if (!geometry) {
    return null;
  }

  return (
    <points geometry={geometry}>
      <pointsMaterial
        color={color}
        size={size}
        sizeAttenuation={true}
        transparent={true}
        opacity={opacity}
        alphaTest={0.02}
        vertexColors={useVertexColors}
      />
    </points>
  );
}

function SurfaceMesh({ geometry, mode, hasVertexColors, colorOverride }) {
  const isContext = mode === "added_context";
  const useVertexColors = !isContext && hasVertexColors;
  const isAdded = mode === "added";
  const color = useVertexColors
    ? "#FFFFFF"
    : colorOverride ||
      (mode === "before"
      ? "#9E9E9E"
      : mode === "added"
        ? "#00FF40"
        : mode === "added_context"
          ? "#233128"
        : "#B0A898");

  if (!geometry) {
    return null;
  }

  return (
    <mesh geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial
        color={color}
        roughness={isAdded ? 0.82 : 1.0}
        metalness={0}
        flatShading={!isContext && !isAdded}
        vertexColors={useVertexColors}
        side={DoubleSide}
        wireframe={isContext}
        transparent={isContext || isAdded}
        opacity={isContext ? 0.34 : isAdded ? 0.96 : 1}
        emissive={isAdded ? color : "#000000"}
        emissiveIntensity={isAdded ? 0.35 : 0}
      />
    </mesh>
  );
}

function getAnnotationPoints(geometry) {
  const positions = geometry?.getAttribute("position");
  if (!positions || positions.count === 0) {
    return [];
  }

  geometry.computeBoundingSphere();
  const center = geometry.boundingSphere?.center || new Vector3();
  let farthestIndex = 0;
  let farthestDistance = -1;

  for (let index = 0; index < positions.count; index += Math.max(1, Math.floor(positions.count / 8000))) {
    const point = new Vector3().fromBufferAttribute(positions, index);
    const distance = point.distanceToSquared(center);
    if (distance > farthestDistance) {
      farthestDistance = distance;
      farthestIndex = index;
    }
  }

  const farthest = new Vector3().fromBufferAttribute(positions, farthestIndex);
  return [
    { label: "RESTORED EDGE", point: center.clone(), align: "left" },
    { label: "CLOSED VOID", point: farthest, align: "right" },
  ];
}

function SurfaceAnnotations({ geometry }) {
  const anchors = useMemo(() => getAnnotationPoints(geometry), [geometry]);

  return anchors.map((anchor) => (
    <Html
      key={`${anchor.label}-${anchor.point.x}-${anchor.point.y}-${anchor.point.z}`}
      position={anchor.point.toArray()}
      center
      occlude
      style={{ pointerEvents: "none" }}
    >
      <div
        style={{
          position: "relative",
          width: "132px",
          transform: anchor.align === "right" ? "translate(-132px, -54px)" : "translate(0, -54px)",
          color: "#00FF40",
          fontFamily: '"Courier New", monospace',
          fontSize: "11px",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textShadow: "0 0 10px rgba(0,255,64,0.85)",
        }}
      >
        <div>{anchor.label}</div>
        <div
          style={{
            position: "absolute",
            top: "26px",
            [anchor.align === "right" ? "right" : "left"]: "8px",
            width: "88px",
            height: "2px",
            background: "#00FF40",
            boxShadow: "0 0 8px rgba(0,255,64,0.9)",
            transform: anchor.align === "right" ? "rotate(28deg)" : "rotate(-28deg)",
            transformOrigin: anchor.align === "right" ? "right center" : "left center",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "50px",
            [anchor.align === "right" ? "right" : "left"]: "-4px",
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: "#00FF40",
            boxShadow: "0 0 12px rgba(0,255,64,1)",
          }}
        />
      </div>
    </Html>
  ));
}

function SyncControls({ controlsRef, cameraState, onCameraChange }) {
  const applyingUpdate = useRef(false);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls || !cameraState) {
      return;
    }

    const desiredPosition = new Vector3(...cameraState.position);
    const desiredTarget = new Vector3(...cameraState.target);
    if (
      controls.object.position.distanceTo(desiredPosition) < 0.001 &&
      controls.target.distanceTo(desiredTarget) < 0.001
    ) {
      return;
    }

    applyingUpdate.current = true;
    controls.object.position.copy(desiredPosition);
    controls.target.copy(desiredTarget);
    controls.update();
    applyingUpdate.current = false;
  }, [cameraState, controlsRef]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls || !onCameraChange) {
      return undefined;
    }

    const handleChange = () => {
      if (applyingUpdate.current) {
        return;
      }

      onCameraChange({
        position: controls.object.position.toArray(),
        target: controls.target.toArray(),
      });
    };

    controls.addEventListener("change", handleChange);
    return () => controls.removeEventListener("change", handleChange);
  }, [controlsRef, onCameraChange]);

  return null;
}

function ModelScene({
  geometry,
  mode,
  hasVertexColors,
  isMesh,
  overlayGeometry,
  overlayIsMesh,
  damageMode,
  showAnnotations,
  cameraState,
  onCameraChange,
}) {
  const controlsRef = useRef(null);
  const { camera } = useThree();
  const [modelCenter, setModelCenter] = useState([0, 0, 0]);

  useEffect(() => {
    const controls = controlsRef.current;

    if (!controls || !geometry) {
      return;
    }

    geometry.computeBoundingSphere();

    const radius = Math.max(geometry.boundingSphere?.radius || 1, 0.001);
    const center = geometry.boundingSphere?.center || new Vector3();
    setModelCenter([center.x, center.y, center.z]);

    camera.position.set(0, 0, radius * 3.5);
    controls.target.set(0, 0, 0);
    controls.update();
  }, [camera, geometry]);

  return (
    <>
      <color attach="background" args={["#1A0A2E"]} />
      <ambientLight color="#FFF8F0" intensity={1.1} />
      <hemisphereLight args={["#fff6dd", "#3b1e12", 0.85]} />
      <directionalLight position={[6, 8, 5]} intensity={1.5} castShadow />
      <directionalLight position={[-6, 4, -7]} intensity={1.05} color="#ffddb0" />
      <directionalLight position={[0, -3, -8]} intensity={0.55} color="#f5c98a" />
      <group position={[-modelCenter[0], -modelCenter[1], -modelCenter[2]]}>
        {isMesh ? (
          <SurfaceMesh geometry={geometry} mode={mode} hasVertexColors={hasVertexColors} />
        ) : (
          <PointMesh geometry={geometry} mode={mode} hasVertexColors={hasVertexColors} />
        )}
        {overlayGeometry ? (
          overlayIsMesh ? (
            <SurfaceMesh
              geometry={overlayGeometry}
              mode="added"
              hasVertexColors={false}
              colorOverride={damageMode ? "#FF1E1E" : "#00FF40"}
            />
          ) : (
            <PointMesh
              geometry={overlayGeometry}
              mode="added"
              hasVertexColors={false}
              colorOverride={damageMode ? "#FF1E1E" : "#00FF40"}
            />
          )
        ) : null}
        {showAnnotations && overlayGeometry ? (
          <SurfaceAnnotations geometry={overlayGeometry} />
        ) : null}
      </group>
      <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.05} />
      <SyncControls
        controlsRef={controlsRef}
        cameraState={cameraState}
        onCameraChange={onCameraChange}
      />
    </>
  );
}

export default function ModelViewer({
  url,
  mode,
  isLoading: externalLoading = false,
  overlayUrl,
  damageMode = false,
  showAnnotations = false,
  cameraState,
  onCameraChange,
}) {
  const {
    geometry,
    isLoading,
    error,
    pointCount,
    renderedPointCount,
    hasVertexColors,
    isMesh,
  } = useModelLoader(
    url,
    MAX_RENDERED_POINTS,
  );
  const {
    geometry: overlayGeometry,
    isMesh: overlayIsMesh,
  } = useModelLoader(
    overlayUrl,
    MAX_RENDERED_POINTS,
  );
  const showLoading = externalLoading || isLoading;

  if (showLoading) {
    return <MandalaSpinner />;
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          minHeight: "320px",
          alignItems: "center",
          justifyContent: "center",
          background: "#1A0A2E",
          color: "#FF6B35",
          fontFamily: "Georgia, serif",
          fontSize: "16px",
          lineHeight: 1.6,
          padding: "24px",
          textAlign: "center",
        }}
      >
        {error.message || "Unable to load this model."}
      </div>
    );
  }

  if (!geometry) {
    return (
      <div
        style={{
          display: "flex",
          minHeight: "320px",
          alignItems: "center",
          justifyContent: "center",
          background: "#1A0A2E",
          color: "#B8860B",
          fontFamily: "Georgia, serif",
          fontSize: "16px",
        }}
      >
        No model loaded.
      </div>
    );
  }

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <Canvas dpr={[1, 2]} camera={{ position: [0, 0, 3], fov: 60 }}>
        <ModelScene
          geometry={geometry}
          mode={mode}
          hasVertexColors={hasVertexColors}
          isMesh={isMesh}
          overlayGeometry={overlayGeometry}
          overlayIsMesh={overlayIsMesh}
          damageMode={damageMode}
          showAnnotations={showAnnotations}
          cameraState={cameraState}
          onCameraChange={onCameraChange}
        />
      </Canvas>
      <div
        style={{
          position: "absolute",
          right: "12px",
          bottom: "12px",
          border: "1px solid #B8860B",
          background: "#1A0A2E",
          opacity: 0.78,
          color: "#B8860B",
          fontFamily: '"Courier New", monospace',
          fontSize: "14px",
          padding: "6px 12px",
          pointerEvents: "none",
        }}
      >
        {isMesh ? "mesh" : "points"} · {renderedPointCount.toLocaleString()} / {pointCount.toLocaleString()}
      </div>
    </div>
  );
}
