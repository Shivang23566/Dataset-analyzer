/**
 * ExplodingDatasetViz.tsx
 * Three.js Exploding Dataset Visualization Component
 * 
 * Features:
 * - 800 instanced particles for performance
 * - 5 visualization morphing shapes (cube, scatter, bars, pie, wave)
 * - GSAP-powered smooth transitions
 * - Post-processing bloom effects
 * - Auto-play with manual click control
 */

import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import gsap from 'gsap';

interface Particle {
  currentPosition: THREE.Vector3;
  targetPosition: THREE.Vector3;
  velocity: THREE.Vector3;
  color: THREE.Color;
  colorIndex: number;
  scale: number;
  phase: number;
  frequency: number;
}

interface Visualization {
  name: string;
  icon: string;
  shape: string;
}

interface ExplodingDatasetVizProps {
  onVisualizationChange?: (viz: Visualization, index: number) => void;
}

const CONFIG = {
  particleCount: 800,
  particleSize: 0.08,
  transitionDuration: 2.0,
  autoPlayInterval: 5000,
  colors: [
    new THREE.Color(0xFFE17C), // Gold
    new THREE.Color(0x4ECDC4), // Teal
    new THREE.Color(0xFF6B9D), // Pink
    new THREE.Color(0xA855F7), // Purple
    new THREE.Color(0x3B82F6), // Blue
    new THREE.Color(0x22C55E), // Green
  ],
  visualizations: [
    { name: 'Raw Dataset', icon: '📦', shape: 'cube' },
    { name: 'Scatter Plot', icon: '📊', shape: 'scatter' },
    { name: 'Bar Chart', icon: '📈', shape: 'bars' },
    { name: 'Distribution', icon: '🎯', shape: 'pie' },
    { name: 'Time Series', icon: '📉', shape: 'wave' },
  ] as Visualization[],
};

export default function ExplodingDatasetViz({ onVisualizationChange }: ExplodingDatasetVizProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const composerRef = useRef<EffectComposer | null>(null);
  const instancedMeshRef = useRef<THREE.InstancedMesh | null>(null);
  const trailsRef = useRef<THREE.Points | null>(null);
  const particlesRef = useRef<Particle[]>([]);
  const currentVizIndexRef = useRef(0);
  const isTransitioningRef = useRef(false);
  const timeRef = useRef(0);
  const mouseRef = useRef(new THREE.Vector2(0, 0));
  const targetRotationRef = useRef(new THREE.Vector2(0, 0));
  const autoPlayTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Shape generators
  const generateCubePositions = useCallback(() => {
    const positions: THREE.Vector3[] = [];
    const gridSize = Math.ceil(Math.cbrt(CONFIG.particleCount));
    const spacing = 2.0 / gridSize;

    for (let i = 0; i < CONFIG.particleCount; i++) {
      const x = (i % gridSize) * spacing - 1 + spacing / 2;
      const y = (Math.floor(i / gridSize) % gridSize) * spacing - 1 + spacing / 2;
      const z = Math.floor(i / (gridSize * gridSize)) * spacing - 1 + spacing / 2;

      positions.push(new THREE.Vector3(
        x + (Math.random() - 0.5) * spacing * 0.3,
        y + (Math.random() - 0.5) * spacing * 0.3,
        z + (Math.random() - 0.5) * spacing * 0.3
      ));
    }
    return positions;
  }, []);

  const generateScatterPositions = useCallback(() => {
    const positions: THREE.Vector3[] = [];
    for (let i = 0; i < CONFIG.particleCount; i++) {
      const clusterX = (Math.random() - 0.5) * 2;
      const clusterY = clusterX * 0.7 + (Math.random() - 0.5) * 0.8;
      const clusterZ = (Math.random() - 0.5) * 1.5;
      positions.push(new THREE.Vector3(clusterX * 1.8, clusterY * 1.8, clusterZ));
    }
    return positions;
  }, []);

  const generateBarPositions = useCallback(() => {
    const positions: THREE.Vector3[] = [];
    const barCount = 8;
    const particlesPerBar = Math.floor(CONFIG.particleCount / barCount);

    for (let bar = 0; bar < barCount; bar++) {
      const barHeight = 0.3 + Math.random() * 1.7;
      const barX = (bar / (barCount - 1)) * 3.5 - 1.75;

      for (let p = 0; p < particlesPerBar; p++) {
        const heightRatio = p / particlesPerBar;
        const y = heightRatio * barHeight - 1;
        const z = (Math.random() - 0.5) * 0.3;
        const x = barX + (Math.random() - 0.5) * 0.3;
        positions.push(new THREE.Vector3(x, y, z));
      }
    }

    while (positions.length < CONFIG.particleCount) {
      positions.push(new THREE.Vector3(
        (Math.random() - 0.5) * 0.1,
        -1 + Math.random() * 0.5,
        0
      ));
    }
    return positions;
  }, []);

  const generatePiePositions = useCallback(() => {
    const positions: THREE.Vector3[] = [];
    const segments = 6;
    const segmentSizes: number[] = [];

    let total = 0;
    for (let i = 0; i < segments; i++) {
      const size = 0.5 + Math.random();
      segmentSizes.push(size);
      total += size;
    }
    segmentSizes.forEach((_, i) => segmentSizes[i] /= total);

    let currentAngle = 0;
    let particleIndex = 0;

    for (let seg = 0; seg < segments; seg++) {
      const segmentAngle = segmentSizes[seg] * Math.PI * 2;
      const particlesInSegment = Math.floor(CONFIG.particleCount * segmentSizes[seg]);

      for (let p = 0; p < particlesInSegment && particleIndex < CONFIG.particleCount; p++) {
        const angle = currentAngle + Math.random() * segmentAngle;
        const radius = 0.3 + Math.random() * 1.2;
        const height = (Math.random() - 0.5) * 0.4;
        positions.push(new THREE.Vector3(
          Math.cos(angle) * radius,
          height,
          Math.sin(angle) * radius
        ));
        particleIndex++;
      }
      currentAngle += segmentAngle;
    }

    while (positions.length < CONFIG.particleCount) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.5 + Math.random() * 0.8;
      positions.push(new THREE.Vector3(
        Math.cos(angle) * radius,
        (Math.random() - 0.5) * 0.3,
        Math.sin(angle) * radius
      ));
    }
    return positions;
  }, []);

  const generateWavePositions = useCallback(() => {
    const positions: THREE.Vector3[] = [];
    const rows = 20;
    const cols = Math.ceil(CONFIG.particleCount / rows);

    for (let i = 0; i < CONFIG.particleCount; i++) {
      const row = Math.floor(i / cols);
      const col = i % cols;
      const x = (col / (cols - 1)) * 4 - 2;
      const z = (row / (rows - 1)) * 2 - 1;
      const y = Math.sin(x * 2 + row * 0.3) * 0.5 +
                Math.cos(z * 3) * 0.3 +
                (Math.random() - 0.5) * 0.2;
      positions.push(new THREE.Vector3(x, y, z));
    }
    return positions;
  }, []);

  const getPositionsForShape = useCallback((shapeName: string) => {
    switch (shapeName) {
      case 'cube': return generateCubePositions();
      case 'scatter': return generateScatterPositions();
      case 'bars': return generateBarPositions();
      case 'pie': return generatePiePositions();
      case 'wave': return generateWavePositions();
      default: return generateCubePositions();
    }
  }, [generateCubePositions, generateScatterPositions, generateBarPositions, generatePiePositions, generateWavePositions]);

  const morphToShape = useCallback((shapeName: string, animate = true) => {
    if (isTransitioningRef.current && animate) return;

    const targetPositions = getPositionsForShape(shapeName);
    const particles = particlesRef.current;

    particles.forEach((particle, i) => {
      if (targetPositions[i]) {
        particle.targetPosition.copy(targetPositions[i]);
      }
    });

    if (animate) {
      isTransitioningRef.current = true;

      particles.forEach((particle, i) => {
        const explodeDirection = particle.currentPosition.clone().normalize();
        const explodeDistance = 1 + Math.random() * 1.5;
        const midPoint = particle.currentPosition.clone().add(
          explodeDirection.multiplyScalar(explodeDistance)
        );

        gsap.timeline()
          .to(particle.currentPosition, {
            x: midPoint.x,
            y: midPoint.y,
            z: midPoint.z,
            duration: CONFIG.transitionDuration * 0.4,
            ease: 'power2.out',
            delay: Math.random() * 0.2,
          })
          .to(particle.currentPosition, {
            x: particle.targetPosition.x,
            y: particle.targetPosition.y,
            z: particle.targetPosition.z,
            duration: CONFIG.transitionDuration * 0.6,
            ease: 'elastic.out(1, 0.5)',
            onComplete: i === 0 ? () => { isTransitioningRef.current = false; } : undefined,
          });
      });
    } else {
      particles.forEach((particle) => {
        particle.currentPosition.copy(particle.targetPosition);
      });
    }
  }, [getPositionsForShape]);

  const nextVisualization = useCallback(() => {
    currentVizIndexRef.current = (currentVizIndexRef.current + 1) % CONFIG.visualizations.length;
    const viz = CONFIG.visualizations[currentVizIndexRef.current];
    morphToShape(viz.shape);
    onVisualizationChange?.(viz, currentVizIndexRef.current);
  }, [morphToShape, onVisualizationChange]);

  const goToVisualization = useCallback((index: number) => {
    if (index === currentVizIndexRef.current || isTransitioningRef.current) return;
    currentVizIndexRef.current = index;
    const viz = CONFIG.visualizations[index];
    morphToShape(viz.shape);
    onVisualizationChange?.(viz, index);
  }, [morphToShape, onVisualizationChange]);

  const startAutoPlay = useCallback(() => {
    if (autoPlayTimerRef.current) {
      clearInterval(autoPlayTimerRef.current);
    }
    autoPlayTimerRef.current = setInterval(() => {
      if (!isTransitioningRef.current) {
        nextVisualization();
      }
    }, CONFIG.autoPlayInterval);
  }, [nextVisualization]);

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const rect = container.getBoundingClientRect();

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050507);
    scene.fog = new THREE.FogExp2(0x050507, 0.15);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(50, rect.width / rect.height, 0.1, 100);
    camera.position.set(0, 0, 6);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(rect.width, rect.height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.5;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Post-processing
    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(new UnrealBloomPass(
      new THREE.Vector2(rect.width, rect.height),
      1.2, 0.5, 0.7
    ));
    composerRef.current = composer;

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.4));
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.8);
    keyLight.position.set(5, 5, 5);
    scene.add(keyLight);

    const goldLight = new THREE.PointLight(0xFFE17C, 0.6, 15);
    goldLight.position.set(-3, 2, 3);
    scene.add(goldLight);

    const tealLight = new THREE.PointLight(0x4ECDC4, 0.6, 15);
    tealLight.position.set(3, -2, 3);
    scene.add(tealLight);

    const pinkLight = new THREE.PointLight(0xFF6B9D, 0.4, 15);
    pinkLight.position.set(0, 3, -3);
    scene.add(pinkLight);

    // Create particles
    const geometry = new THREE.SphereGeometry(CONFIG.particleSize, 16, 16);
    const material = new THREE.MeshStandardMaterial({
      metalness: 0.3,
      roughness: 0.4,
      envMapIntensity: 0.5,
    });

    const instancedMesh = new THREE.InstancedMesh(geometry, material, CONFIG.particleCount);
    instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    instancedMeshRef.current = instancedMesh;

    const dummy = new THREE.Object3D();
    const colorArray = new Float32Array(CONFIG.particleCount * 3);
    const particles: Particle[] = [];

    for (let i = 0; i < CONFIG.particleCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 0.5 + Math.random() * 0.5;
      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = radius * Math.cos(phi);

      const color = CONFIG.colors[i % CONFIG.colors.length];

      particles.push({
        currentPosition: new THREE.Vector3(x, y, z),
        targetPosition: new THREE.Vector3(x, y, z),
        velocity: new THREE.Vector3(),
        color: color.clone(),
        colorIndex: i % CONFIG.colors.length,
        scale: 0.8 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2,
        frequency: 0.5 + Math.random() * 1.5,
      });

      dummy.position.set(x, y, z);
      dummy.scale.setScalar(particles[i].scale);
      dummy.updateMatrix();
      instancedMesh.setMatrixAt(i, dummy.matrix);

      colorArray[i * 3] = color.r;
      colorArray[i * 3 + 1] = color.g;
      colorArray[i * 3 + 2] = color.b;
    }

    instancedMesh.instanceColor = new THREE.InstancedBufferAttribute(colorArray, 3);
    scene.add(instancedMesh);
    particlesRef.current = particles;

    // Trails
    const trailGeometry = new THREE.BufferGeometry();
    const trailCount = 200;
    const trailPositions = new Float32Array(trailCount * 3);
    const trailColors = new Float32Array(trailCount * 3);

    for (let i = 0; i < trailCount; i++) {
      trailPositions[i * 3] = (Math.random() - 0.5) * 4;
      trailPositions[i * 3 + 1] = (Math.random() - 0.5) * 4;
      trailPositions[i * 3 + 2] = (Math.random() - 0.5) * 4;
      const color = CONFIG.colors[i % CONFIG.colors.length];
      trailColors[i * 3] = color.r;
      trailColors[i * 3 + 1] = color.g;
      trailColors[i * 3 + 2] = color.b;
    }

    trailGeometry.setAttribute('position', new THREE.BufferAttribute(trailPositions, 3));
    trailGeometry.setAttribute('color', new THREE.BufferAttribute(trailColors, 3));

    const trails = new THREE.Points(trailGeometry, new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }));
    scene.add(trails);
    trailsRef.current = trails;

    // Initial shape
    morphToShape('cube', false);
    onVisualizationChange?.(CONFIG.visualizations[0], 0);

    // Animation loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      timeRef.current += 0.016;

      // Update particles
      const particleDummy = new THREE.Object3D();
      particlesRef.current.forEach((particle, i) => {
        const floatOffset = Math.sin(timeRef.current * particle.frequency + particle.phase) * 0.02;
        particleDummy.position.copy(particle.currentPosition);
        particleDummy.position.y += floatOffset;
        particleDummy.rotation.x = timeRef.current * 0.5 + particle.phase;
        particleDummy.rotation.y = timeRef.current * 0.3 + particle.phase;
        const pulseScale = 1 + Math.sin(timeRef.current * 2 + particle.phase) * 0.1;
        particleDummy.scale.setScalar(particle.scale * pulseScale);
        particleDummy.updateMatrix();
        instancedMeshRef.current?.setMatrixAt(i, particleDummy.matrix);
      });
      if (instancedMeshRef.current) {
        instancedMeshRef.current.instanceMatrix.needsUpdate = true;
      }

      // Update camera
      const rotationSpeed = 0.05;
      if (cameraRef.current) {
        cameraRef.current.position.x += (targetRotationRef.current.y * 2 - cameraRef.current.position.x) * rotationSpeed;
        cameraRef.current.position.y += (targetRotationRef.current.x * 2 - cameraRef.current.position.y) * rotationSpeed;
        cameraRef.current.lookAt(0, 0, 0);

        if (Math.abs(targetRotationRef.current.x) < 0.01 && Math.abs(targetRotationRef.current.y) < 0.01) {
          const autoRotate = Math.sin(timeRef.current * 0.2) * 0.3;
          cameraRef.current.position.x = Math.sin(autoRotate) * 6;
          cameraRef.current.position.z = Math.cos(autoRotate) * 6;
          cameraRef.current.lookAt(0, 0, 0);
        }
      }

      // Update trails
      if (trailsRef.current) {
        const trailPosArray = trailsRef.current.geometry.attributes.position.array as Float32Array;
        for (let i = 0; i < trailPosArray.length / 3; i++) {
          trailPosArray[i * 3] += Math.sin(timeRef.current + i) * 0.002;
          trailPosArray[i * 3 + 1] += Math.cos(timeRef.current + i * 0.5) * 0.002;
          trailPosArray[i * 3 + 2] += Math.sin(timeRef.current * 0.5 + i) * 0.001;
          if (trailPosArray[i * 3] > 3) trailPosArray[i * 3] = -3;
          if (trailPosArray[i * 3] < -3) trailPosArray[i * 3] = 3;
          if (trailPosArray[i * 3 + 1] > 3) trailPosArray[i * 3 + 1] = -3;
          if (trailPosArray[i * 3 + 1] < -3) trailPosArray[i * 3 + 1] = 3;
        }
        trailsRef.current.geometry.attributes.position.needsUpdate = true;
        trailsRef.current.rotation.y += 0.001;
      }

      composerRef.current?.render();
    };
    animate();

    // Start auto-play
    startAutoPlay();

    // Resize handler
    const handleResize = () => {
      const newRect = container.getBoundingClientRect();
      if (cameraRef.current) {
        cameraRef.current.aspect = newRect.width / newRect.height;
        cameraRef.current.updateProjectionMatrix();
      }
      rendererRef.current?.setSize(newRect.width, newRect.height);
      composerRef.current?.setSize(newRect.width, newRect.height);
    };
    window.addEventListener('resize', handleResize);

    // Mouse handlers
    const handleMouseMove = (e: MouseEvent) => {
      const newRect = container.getBoundingClientRect();
      mouseRef.current.x = ((e.clientX - newRect.left) / newRect.width) * 2 - 1;
      mouseRef.current.y = -((e.clientY - newRect.top) / newRect.height) * 2 + 1;
      targetRotationRef.current.x = mouseRef.current.y * 0.2;
      targetRotationRef.current.y = mouseRef.current.x * 0.3;
    };

    const handleMouseLeave = () => {
      targetRotationRef.current.set(0, 0);
    };

    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    // Visibility change
    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (autoPlayTimerRef.current) clearInterval(autoPlayTimerRef.current);
      } else {
        startAutoPlay();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if (autoPlayTimerRef.current) clearInterval(autoPlayTimerRef.current);
      
      renderer.dispose();
      composer.dispose();
      geometry.dispose();
      material.dispose();
      
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [morphToShape, startAutoPlay, onVisualizationChange]);

  const handleClick = useCallback(() => {
    nextVisualization();
    startAutoPlay();
  }, [nextVisualization, startAutoPlay]);

  const handleDotClick = useCallback((index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    goToVisualization(index);
    startAutoPlay();
  }, [goToVisualization, startAutoPlay]);

  return {
    containerRef,
    handleClick,
    handleDotClick,
    visualizations: CONFIG.visualizations,
    currentVizIndexRef,
  };
}

export { CONFIG as EXPLODING_VIZ_CONFIG };
export type { Visualization };
