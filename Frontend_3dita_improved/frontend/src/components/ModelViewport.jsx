import { useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bounds, Environment, Html, OrbitControls } from "@react-three/drei";
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  MeshStandardMaterial,
  PointsMaterial,
  Vector3,
} from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";

const MAX_POINTS = 200000;

function subsampleGeometry(geometry, maxPoints = MAX_POINTS) {
  const positions = geometry.getAttribute("position");

  if (!positions || positions.count <= maxPoints) {
    return geometry;
  }

  const step = Math.ceil(positions.count / maxPoints);
  const sampledCount = Math.ceil(positions.count / step);
  const nextGeometry = new BufferGeometry();

  const sampleAttribute = (attributeName) => {
    const attribute = geometry.getAttribute(attributeName);
    if (!attribute) {
      return null;
    }

    const output = new Float32Array(sampledCount * attribute.itemSize);
    let cursor = 0;

    for (let i = 0; i < attribute.count; i += step) {
      for (let j = 0; j < attribute.itemSize; j += 1) {
        output[cursor] = attribute.array[i * attribute.itemSize + j];
        cursor += 1;
      }
    }

    return new BufferAttribute(output, attribute.itemSize);
  };

  nextGeometry.setAttribute("position", sampleAttribute("position"));

  const colorAttribute = sampleAttribute("color");
  if (colorAttribute) {
    nextGeometry.setAttribute("color", colorAttribute);
  }

  const normalAttribute = sampleAttribute("normal");
  if (normalAttribute) {
    nextGeometry.setAttribute("normal", normalAttribute);
  }

  return nextGeometry;
}

function createPointCloud(geometry, tint) {
  const preparedGeometry = subsampleGeometry(geometry.clone());
  const hasColor = Boolean(preparedGeometry.getAttribute("color"));
  const material = new PointsMaterial({
    size: 0.03,
    sizeAttenuation: true,
    color: hasColor ? undefined : tint,
    vertexColors: hasColor,
  });

  return { geometry: preparedGeometry, material };
}

function tintObject(root, tint) {
  const material = new MeshStandardMaterial({
    color: tint,
    roughness: 0.55,
    metalness: 0.08,
  });

  root.traverse((child) => {
    if (child.isMesh) {
      child.material = material;
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });

  return root;
}

function useLoadedModel(modelUrl, tint) {
  const [state, setState] = useState({
    status: "idle",
    object: null,
    error: null,
  });

  useEffect(() => {
    if (!modelUrl) {
      setState({ status: "idle", object: null, error: null });
      return undefined;
    }

    const extension = modelUrl.split("?")[0].split(".").pop()?.toLowerCase();
    const loader = extension === "ply" ? new PLYLoader() : new OBJLoader();
    let isMounted = true;

    setState({ status: "loading", object: null, error: null });

    loader.load(
      modelUrl,
      (result) => {
        if (!isMounted) {
          return;
        }

        if (extension === "ply") {
          const { geometry, material } = createPointCloud(result, tint);
          setState({
            status: "ready",
            object: { type: "points", geometry, material },
            error: null,
          });
          return;
        }

        const group = tintObject(result, tint);
        setState({
          status: "ready",
          object: { type: "object", value: group },
          error: null,
        });
      },
      undefined,
      (error) => {
        if (isMounted) {
          setState({ status: "error", object: null, error });
        }
      },
    );

    return () => {
      isMounted = false;
    };
  }, [modelUrl, tint]);

  return state;
}

function SyncControls({ orbitRef, cameraState, onCameraChange }) {
  const isApplyingExternalUpdate = useRef(false);

  useEffect(() => {
    if (!orbitRef.current || !cameraState) {
      return;
    }

    const { camera, target } = orbitRef.current;
    const desiredPosition = new Vector3(...cameraState.position);
    const desiredTarget = new Vector3(...cameraState.target);
    const changed =
      camera.position.distanceTo(desiredPosition) > 0.001 ||
      target.distanceTo(desiredTarget) > 0.001;

    if (!changed) {
      return;
    }

    isApplyingExternalUpdate.current = true;
    camera.position.copy(desiredPosition);
    target.copy(desiredTarget);
    orbitRef.current.update();
    isApplyingExternalUpdate.current = false;
  }, [cameraState, orbitRef]);

  useFrame(() => {
    if (!orbitRef.current || isApplyingExternalUpdate.current) {
      return;
    }

    const { camera, target } = orbitRef.current;
    onCameraChange({
      position: camera.position.toArray(),
      target: target.toArray(),
    });
  });

  return null;
}

function LoadedModel({ model }) {
  if (!model) {
    return null;
  }

  if (model.type === "points") {
    return <points geometry={model.geometry} material={model.material} />;
  }

  return <primitive object={model.value} />;
}

function EmptyState({ message, tone }) {
  return (
    <Html center>
      <div className="rounded-2xl border border-white/10 bg-nightTemple/90 px-4 py-3 text-sm text-creamTemple shadow-glow">
        <span className={tone}>{message}</span>
      </div>
    </Html>
  );
}

export default function ModelViewport({
  title,
  modelUrl,
  tint,
  accentClass,
  cameraState,
  onCameraChange,
}) {
  const orbitRef = useRef(null);
  const { status, object, error } = useLoadedModel(modelUrl, new Color(tint));

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-nightTemple/70">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-creamTemple/55">
            3D Viewport
          </p>
          <h3 className={`mt-1 text-lg font-semibold ${accentClass}`}>
            {title}
          </h3>
        </div>
        <div className={`h-3 w-3 rounded-full ${accentClass.replace("text-", "bg-")}`} />
      </div>

      <div className="h-[22rem] w-full sm:h-[28rem] xl:h-[34rem]">
        <Canvas camera={{ position: [2.5, 2, 2.5], fov: 45 }}>
          <color attach="background" args={["#10071d"]} />
          <ambientLight intensity={0.9} />
          <directionalLight
            position={[6, 8, 5]}
            intensity={1.5}
            color="#fff2ce"
          />
          <spotLight
            position={[-5, 7, 6]}
            intensity={0.8}
            angle={0.4}
            penumbra={0.8}
            color={tint}
          />
          <Bounds fit clip observe margin={1.2}>
            {status === "ready" ? <LoadedModel model={object} /> : null}
          </Bounds>
          {status === "loading" ? (
            <EmptyState message="Loading model..." tone="text-goldTemple" />
          ) : null}
          {status === "error" ? (
            <EmptyState
              message={`Unable to load model: ${error?.message || "Unknown error"}`}
              tone="text-red-200"
            />
          ) : null}
          {status === "idle" ? (
            <EmptyState message="Model unavailable" tone="text-creamTemple/80" />
          ) : null}
          <OrbitControls
            ref={orbitRef}
            enableDamping
            dampingFactor={0.08}
          />
          <SyncControls
            orbitRef={orbitRef}
            cameraState={cameraState}
            onCameraChange={onCameraChange}
          />
          <Environment preset="sunset" />
        </Canvas>
      </div>
    </div>
  );
}
