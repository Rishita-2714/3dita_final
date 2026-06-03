import { useEffect, useState } from "react";
import { BufferGeometry, Float32BufferAttribute, Uint8BufferAttribute } from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { subsampleGeometry } from "../utils/subsample";

function getFileExtension(url = "") {
  const hashFileName = url.includes("#")
    ? decodeURIComponent(url.split("#").pop() || "")
    : "";
  const path = hashFileName || url.split("?")[0].split("#")[0];

  return path.split(".").pop()?.toLowerCase() || "";
}

function mergeObjMeshes(group) {
  const geometries = [];

  group.updateMatrixWorld(true);

  group.traverse((child) => {
    if (!child.isMesh || !child.geometry) {
      return;
    }

    const geometry = child.geometry.clone();
    geometry.applyMatrix4(child.matrixWorld);
    geometries.push(geometry);
  });

  if (geometries.length === 0) {
    throw new Error("OBJ file did not contain any mesh geometry.");
  }

  const mergedGeometry =
    geometries.length === 1 ? geometries[0] : mergeGeometries(geometries, false);

  geometries.forEach((geometry) => {
    if (geometry !== mergedGeometry) {
      geometry.dispose();
    }
  });

  if (!mergedGeometry) {
    throw new Error("Unable to merge OBJ mesh geometries.");
  }

  return mergedGeometry;
}

function loadPly(url) {
  const loader = new PLYLoader();

  return new Promise((resolve, reject) => {
    loader.load(url, resolve, undefined, reject);
  });
}

function loadObj(url) {
  const loader = new OBJLoader();

  return new Promise((resolve, reject) => {
    loader.load(
      url,
      (group) => {
        try {
          resolve(mergeObjMeshes(group));
        } catch (error) {
          reject(error);
        }
      },
      undefined,
      reject,
    );
  });
}

async function loadTxtPointCloud(url) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Unable to load TXT point cloud.");
  }

  const text = await response.text();
  const positions = [];
  const colors = [];
  const normals = [];
  let hasUnitColors = false;

  text.split(/\r?\n/).forEach((line) => {
    const parts = line
      .trim()
      .split(/[\s,]+/)
      .map(Number);

    if (parts.length >= 3 && parts.slice(0, 3).every(Number.isFinite)) {
      positions.push(parts[0], parts[1], parts[2]);

      if (parts.length >= 6 && parts.slice(3, 6).every(Number.isFinite)) {
        const rgb = parts.slice(3, 6);
        if (rgb.every((value) => value >= 0 && value <= 1)) {
          hasUnitColors = true;
        }
        colors.push(...rgb);
      }

      if (parts.length === 9 && parts.slice(6, 9).every(Number.isFinite)) {
        normals.push(parts[6], parts[7], parts[8]);
      }

      if (parts.length >= 10 && parts.slice(7, 10).every(Number.isFinite)) {
        normals.push(parts[7], parts[8], parts[9]);
      }
    }
  });

  if (positions.length === 0) {
    throw new Error("TXT file did not contain numeric x y z point rows.");
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));

  if (colors.length === positions.length) {
    const normalizedColors = hasUnitColors
      ? colors.map((value) => Math.max(0, Math.min(255, Math.round(value * 255))))
      : colors.map((value) => Math.max(0, Math.min(255, Math.round(value))));
    const colorAttribute = new Uint8BufferAttribute(normalizedColors, 3);
    colorAttribute.normalized = true;
    geometry.setAttribute("color", colorAttribute);
  }

  if (normals.length === positions.length) {
    geometry.setAttribute("normal", new Float32BufferAttribute(normals, 3));
  }

  return geometry;
}

export function useModelLoader(url, maxPoints = 200000) {
  const [state, setState] = useState({
    geometry: null,
    isLoading: false,
    error: null,
    pointCount: 0,
    renderedPointCount: 0,
    hasVertexColors: false,
    isMesh: false,
  });

  useEffect(() => {
    if (!url) {
      setState({
        geometry: null,
        isLoading: false,
        error: null,
        pointCount: 0,
        renderedPointCount: 0,
        hasVertexColors: false,
        isMesh: false,
      });
      return undefined;
    }

    let isMounted = true;
    const extension = getFileExtension(url);

    async function loadModel() {
      setState({
        geometry: null,
        isLoading: true,
        error: null,
        pointCount: 0,
        renderedPointCount: 0,
        hasVertexColors: false,
        isMesh: false,
      });

      try {
        let loadedGeometry;

        if (extension === "ply") {
          loadedGeometry = await loadPly(url);
        } else if (extension === "obj") {
          loadedGeometry = await loadObj(url);
        } else if (extension === "txt") {
          loadedGeometry = await loadTxtPointCloud(url);
        } else {
          throw new Error(
            `Unsupported model format ".${extension || "unknown"}". Please use a .ply, .obj, or .txt file.`,
          );
        }

        const geometry =
          loadedGeometry instanceof BufferGeometry
            ? loadedGeometry.clone()
            : loadedGeometry;
        const isMesh = Boolean(geometry.index && geometry.index.count >= 3);

        if (!geometry.getAttribute("normal")) {
          geometry.computeVertexNormals();
        }

        const sampledGeometry = isMesh ? geometry : subsampleGeometry(geometry, maxPoints);
        const sourcePosition = geometry.getAttribute("position");
        const renderedPosition = sampledGeometry.getAttribute("position");

        if (isMounted) {
          setState({
            geometry: sampledGeometry,
            isLoading: false,
            error: null,
            pointCount: sourcePosition?.count || 0,
            renderedPointCount: renderedPosition?.count || 0,
            hasVertexColors: Boolean(sampledGeometry.getAttribute("color")),
            isMesh,
          });
        }
      } catch (error) {
        if (isMounted) {
          setState({
            geometry: null,
            isLoading: false,
            error:
              error instanceof Error
                ? error
                : new Error("Unable to load the selected 3D model."),
            pointCount: 0,
            renderedPointCount: 0,
            hasVertexColors: false,
            isMesh: false,
          });
        }
      }
    }

    loadModel();

    return () => {
      isMounted = false;
    };
  }, [maxPoints, url]);

  return state;
}
