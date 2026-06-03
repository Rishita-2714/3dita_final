import * as THREE from "three";

export function subsampleGeometry(geometry, maxPoints = 200000) {
  const position = geometry.getAttribute("position");

  if (!position || position.count <= maxPoints) {
    return geometry;
  }

  const targetPoints =
    position.count <= 500000
      ? position.count
      : position.count <= 1200000
        ? Math.max(maxPoints, 700000)
        : position.count <= 2500000
          ? Math.max(maxPoints, 850000)
          : maxPoints;

  if (position.count <= targetPoints) {
    return geometry;
  }

  const step = Math.ceil(position.count / targetPoints);
  const sampledCount = Math.ceil(position.count / step);
  const sampledGeometry = new THREE.BufferGeometry();

  const sampleAttribute = (attributeName) => {
    const attribute = geometry.getAttribute(attributeName);

    if (!attribute) {
      return null;
    }

    const sampledArray = new attribute.array.constructor(
      sampledCount * attribute.itemSize,
    );
    let cursor = 0;

    for (let i = 0; i < attribute.count; i += step) {
      for (let itemIndex = 0; itemIndex < attribute.itemSize; itemIndex += 1) {
        sampledArray[cursor] =
          attribute.array[i * attribute.itemSize + itemIndex];
        cursor += 1;
      }
    }

    return new THREE.BufferAttribute(
      sampledArray,
      attribute.itemSize,
      attribute.normalized,
    );
  };

  sampledGeometry.setAttribute("position", sampleAttribute("position"));

  const color = sampleAttribute("color");
  if (color) {
    sampledGeometry.setAttribute("color", color);
  }

  const normal = sampleAttribute("normal");
  if (normal) {
    sampledGeometry.setAttribute("normal", normal);
  }

  sampledGeometry.computeBoundingBox();
  sampledGeometry.computeBoundingSphere();

  return sampledGeometry;
}
