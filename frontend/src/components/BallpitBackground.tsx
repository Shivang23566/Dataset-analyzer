/**
 * BallpitBackground Component
 *
 * A high-performance 3D background featuring interactive spheres that react to gravity,
 * friction, and user interaction. Uses Three.js InstancedMesh for rendering efficiency
 * and a custom physical material for advanced lighting effects.
 */

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

class PhysicalScatteringMaterial extends THREE.MeshPhysicalMaterial {
  uniforms: { [key: string]: { value: unknown } } = {
    thicknessDistortion: { value: 0.1 },
    thicknessAmbient: { value: 0 },
    thicknessAttenuation: { value: 0.1 },
    thicknessPower: { value: 2 },
    thicknessScale: { value: 10 },
  };

  constructor(params: THREE.MeshPhysicalMaterialParameters) {
    super(params);
    this.defines = { USE_UV: '' };
    this.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms);
      shader.fragmentShader = `
        uniform float thicknessPower;
        uniform float thicknessScale;
        uniform float thicknessDistortion;
        uniform float thicknessAmbient;
        uniform float thicknessAttenuation;
        ${shader.fragmentShader}
      `;

      shader.fragmentShader = shader.fragmentShader.replace(
        'void main() {',
        `
        void RE_Direct_Scattering(const in IncidentLight directLight, const in vec2 uv, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, inout ReflectedLight reflectedLight) {
          vec3 scatteringHalf = normalize(directLight.direction + (geometryNormal * thicknessDistortion));
          float scatteringDot = pow(saturate(dot(geometryViewDir, -scatteringHalf)), thicknessPower) * thicknessScale;
          #ifdef USE_COLOR
            vec3 scatteringIllu = (scatteringDot + thicknessAmbient) * vColor;
          #else
            vec3 scatteringIllu = (scatteringDot + thicknessAmbient) * diffuse;
          #endif
          reflectedLight.directDiffuse += scatteringIllu * thicknessAttenuation * directLight.color;
        }
        void main() {
        `
      );

      const lightsChunk = THREE.ShaderChunk.lights_fragment_begin
        .split('RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );')
        .join(`
          RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
          RE_Direct_Scattering(directLight, vUv, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, reflectedLight);
        `);
      shader.fragmentShader = shader.fragmentShader.replace('#include <lights_fragment_begin>', lightsChunk);
    };
  }
}

class PhysicsWorld {
  config: Required<Pick<BallpitProps, 'count' | 'gravity' | 'friction' | 'wallBounce' | 'maxVelocity' | 'followCursor' | 'minSize' | 'maxSize'>> & {
    maxX: number;
    maxY: number;
    maxZ: number;
  };
  positionData: Float32Array;
  velocityData: Float32Array;
  sizeData: Float32Array;
  center: THREE.Vector3 = new THREE.Vector3();

  constructor(config: PhysicsWorld['config']) {
    this.config = config;
    const count = config.count;
    this.positionData = new Float32Array(3 * count).fill(0);
    this.velocityData = new Float32Array(3 * count).fill(0);
    this.sizeData = new Float32Array(count).fill(1);
    this.initialize();
  }

  initialize() {
    const { count, maxX, maxY, maxZ, minSize, maxSize } = this.config;

    for (let i = 0; i < count; i++) {
      const idx = 3 * i;
      this.positionData[idx] = THREE.MathUtils.randFloatSpread(2 * maxX);
      this.positionData[idx + 1] = THREE.MathUtils.randFloatSpread(2 * maxY);
      this.positionData[idx + 2] = THREE.MathUtils.randFloatSpread(2 * maxZ);
      this.sizeData[i] = THREE.MathUtils.randFloat(minSize, maxSize);
    }
  }

  update(delta: number) {
    const { count, gravity, friction, wallBounce, maxVelocity, maxX, maxY, maxZ, followCursor } = this.config;

    let startIdx = 0;
    if (followCursor) {
      startIdx = 1;
      const firstPos = new THREE.Vector3().fromArray(this.positionData, 0);
      firstPos.lerp(this.center, 0.1).toArray(this.positionData, 0);
      new THREE.Vector3(0, 0, 0).toArray(this.velocityData, 0);
    }

    for (let i = startIdx; i < count; i++) {
      const base = 3 * i;
      const pos = new THREE.Vector3().fromArray(this.positionData, base);
      const vel = new THREE.Vector3().fromArray(this.velocityData, base);
      const radius = this.sizeData[i];

      vel.y -= delta * gravity * radius;
      vel.multiplyScalar(friction);
      vel.clampLength(0, maxVelocity);
      pos.add(vel);

      for (let j = i + 1; j < count; j++) {
        const otherBase = 3 * j;
        const otherPos = new THREE.Vector3().fromArray(this.positionData, otherBase);
        const diff = new THREE.Vector3().copy(otherPos).sub(pos);
        const dist = diff.length();
        const sumRadius = radius + this.sizeData[j];

        if (dist < sumRadius) {
          const overlap = sumRadius - dist;
          const correction = diff.normalize().multiplyScalar(0.5 * overlap);
          pos.sub(correction);
          otherPos.add(correction);

          const relVel = new THREE.Vector3().fromArray(this.velocityData, otherBase).sub(vel);
          const impulse = correction.clone().multiplyScalar(relVel.dot(correction.normalize()));
          vel.add(impulse);

          otherPos.toArray(this.positionData, otherBase);
        }
      }

      if (followCursor) {
        const followerPos = new THREE.Vector3().fromArray(this.positionData, 0);
        const diff = new THREE.Vector3().copy(followerPos).sub(pos);
        const d = diff.length();
        const sumRadius = radius + this.sizeData[0];
        if (d < sumRadius) {
          const correction = diff.normalize().multiplyScalar(sumRadius - d);
          pos.sub(correction);
          vel.sub(correction.multiplyScalar(0.2));
        }
      }

      if (Math.abs(pos.x) + radius > maxX) {
        pos.x = Math.sign(pos.x) * (maxX - radius);
        vel.x *= -wallBounce;
      }
      if (pos.y - radius < -maxY) {
        pos.y = -maxY + radius;
        vel.y *= -wallBounce;
      } else if (gravity === 0 && pos.y + radius > maxY) {
        pos.y = maxY - radius;
        vel.y *= -wallBounce;
      }
      if (Math.abs(pos.z) + radius > maxZ) {
        pos.z = Math.sign(pos.z) * (maxZ - radius);
        vel.z *= -wallBounce;
      }

      pos.toArray(this.positionData, base);
      vel.toArray(this.velocityData, base);
    }
  }
}

export interface BallpitProps {
  count?: number;
  colors?: string[];
  ambientColor?: string;
  ambientIntensity?: number;
  lightIntensity?: number;
  minSize?: number;
  maxSize?: number;
  gravity?: number;
  friction?: number;
  wallBounce?: number;
  maxVelocity?: number;
  followCursor?: boolean;
  className?: string;
}

export default function BallpitBackground({
  count = 200,
  colors = ['#6366F1', '#0EA5E9', '#8B5CF6'],
  ambientColor = '#080B14',
  ambientIntensity = 1,
  lightIntensity = 200,
  minSize = 0.5,
  maxSize = 1,
  gravity = 0.5,
  friction = 0.9975,
  wallBounce = 0.95,
  maxVelocity = 0.15,
  followCursor = true,
  className = '',
}: BallpitProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const canvas = canvasRef.current;
    const parent = containerRef.current;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const scene = new THREE.Scene();
    const roomEnv = new RoomEnvironment();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envTexture = pmrem.fromScene(roomEnv).texture;

    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 1000);
    camera.position.z = 20;

    const geometry = new THREE.SphereGeometry(1, 32, 32);
    const material = new PhysicalScatteringMaterial({
      envMap: envTexture,
      metalness: 0.5,
      roughness: 0.5,
      clearcoat: 1,
      clearcoatRoughness: 0.15,
    });

    const imesh = new THREE.InstancedMesh(geometry, material, count);
    scene.add(imesh);

    const ambient = new THREE.AmbientLight(ambientColor, ambientIntensity);
    scene.add(ambient);

    const pointLight = new THREE.PointLight(colors[0], lightIntensity);
    scene.add(pointLight);

    const config = {
      count,
      minSize,
      maxSize,
      gravity,
      friction,
      wallBounce,
      maxVelocity,
      followCursor,
      maxX: 5,
      maxY: 5,
      maxZ: 2,
    };
    const physics = new PhysicsWorld(config);

    const threeColors = colors.map((c) => new THREE.Color(c));
    for (let i = 0; i < count; i++) {
      const color = threeColors[i % threeColors.length];
      imesh.setColorAt(i, color);
    }
    if (imesh.instanceColor) {
      imesh.instanceColor.needsUpdate = true;
    }

    const raycaster = new THREE.Raycaster();
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    const intersection = new THREE.Vector3();
    const pointer = new THREE.Vector2();

    const updatePointer = (e: MouseEvent | TouchEvent) => {
      const x = 'touches' in e ? e.touches[0].clientX : e.clientX;
      const y = 'touches' in e ? e.touches[0].clientY : e.clientY;
      const rect = canvas.getBoundingClientRect();
      pointer.x = ((x - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((y - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(pointer, camera);
      raycaster.ray.intersectPlane(plane, intersection);
      physics.center.copy(intersection);
    };

    window.addEventListener('mousemove', updatePointer);
    window.addEventListener('touchstart', updatePointer);
    window.addEventListener('touchmove', updatePointer);

    const resize = () => {
      const w = parent.offsetWidth;
      const h = parent.offsetHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();

      const fovRad = (camera.fov * Math.PI) / 180;
      const worldHeight = 2 * Math.tan(fovRad / 2) * camera.position.z;
      const worldWidth = worldHeight * camera.aspect;
      physics.config.maxX = worldWidth / 2;
      physics.config.maxY = worldHeight / 2;
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(parent);
    resize();

    let animationFrameId = 0;
    const clock = new THREE.Clock();
    const dummy = new THREE.Object3D();

    const animate = () => {
      const delta = clock.getDelta();
      physics.update(Math.min(delta, 0.1));

      for (let i = 0; i < count; i++) {
        dummy.position.fromArray(physics.positionData, i * 3);
        const s = physics.sizeData[i];

        if (i === 0 && !followCursor) {
          dummy.scale.setScalar(0);
        } else {
          dummy.scale.setScalar(s);
        }

        dummy.updateMatrix();
        imesh.setMatrixAt(i, dummy.matrix);

        if (i === 0) pointLight.position.copy(dummy.position);
      }
      imesh.instanceMatrix.needsUpdate = true;

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('mousemove', updatePointer);
      window.removeEventListener('touchstart', updatePointer);
      window.removeEventListener('touchmove', updatePointer);
      resizeObserver.disconnect();
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      pmrem.dispose();
      roomEnv.dispose();
    };
  }, [
    count,
    colors,
    ambientColor,
    ambientIntensity,
    lightIntensity,
    minSize,
    maxSize,
    gravity,
    friction,
    wallBounce,
    maxVelocity,
    followCursor,
  ]);

  return (
    <div ref={containerRef} className={`ballpit-container ${className}`}>
      <canvas ref={canvasRef} className="ballpit-canvas" />
    </div>
  );
}
