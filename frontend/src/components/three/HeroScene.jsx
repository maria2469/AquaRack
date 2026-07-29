import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Signature visual for AquaMind AI: a small cluster of server racks with a
 * glowing "coolant core" pulsing between them, threaded by rising particle
 * streams that read simultaneously as rising heat, flowing water, and
 * data telemetry — the three things this product reasons about at once.
 */

function RackUnit({ position, height, phase }) {
  const glowRef = useRef();
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (glowRef.current) {
      const pulse = 0.4 + 0.6 * Math.abs(Math.sin(t * 0.6 + phase));
      glowRef.current.material.emissiveIntensity = pulse;
    }
  });

  return (
    <group position={position}>
      {/* rack chassis */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.9, height, 0.7]} />
        <meshStandardMaterial
          color="#0a1420"
          metalness={0.6}
          roughness={0.35}
        />
      </mesh>
      {/* front panel status strip */}
      <mesh ref={glowRef} position={[0, 0, 0.36]}>
        <planeGeometry args={[0.55, height * 0.85]} />
        <meshStandardMaterial
          color="#0d1c2c"
          emissive="#2b7fff"
          emissiveIntensity={0.5}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

function CoolantCore() {
  const ref = useRef();
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (ref.current) {
      ref.current.rotation.y = t * 0.25;
      ref.current.scale.setScalar(1 + Math.sin(t * 1.2) * 0.05);
    }
  });
  return (
    <mesh ref={ref} position={[0, 0.2, 0]}>
      <icosahedronGeometry args={[0.55, 1]} />
      <meshStandardMaterial
        color="#0a1420"
        emissive="#22d3ee"
        emissiveIntensity={1.1}
        wireframe
        toneMapped={false}
      />
    </mesh>
  );
}

function ParticleStream({ count = 140 }) {
  const ref = useRef();

  const { positions, speeds, offsets } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const speeds = new Float32Array(count);
    const offsets = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const radius = 1.2 + Math.random() * 2.6;
      const angle = Math.random() * Math.PI * 2;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = Math.random() * 6 - 3;
      positions[i * 3 + 2] = Math.sin(angle) * radius;
      speeds[i] = 0.25 + Math.random() * 0.5;
      offsets[i] = Math.random() * 10;
    }
    return { positions, speeds, offsets };
  }, [count]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const arr = ref.current.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      arr[i * 3 + 1] += delta * speeds[i];
      if (arr[i * 3 + 1] > 3.2) arr[i * 3 + 1] = -3.2;
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.035}
        color="#67e8f9"
        transparent
        opacity={0.75}
        sizeAttenuation
        toneMapped={false}
      />
    </points>
  );
}

function Rig() {
  const group = useRef();
  useFrame(({ clock, pointer }) => {
    if (!group.current) return;
    const t = clock.getElapsedTime();
    group.current.rotation.y = Math.sin(t * 0.08) * 0.35 + pointer.x * 0.25;
    group.current.rotation.x = pointer.y * 0.08;
  });

  const racks = [
    { position: [-1.6, 0, -0.3], height: 2.4, phase: 0 },
    { position: [-0.7, 0.2, 0.6], height: 2.9, phase: 1.1 },
    { position: [0.9, 0.1, 0.5], height: 2.7, phase: 2.0 },
    { position: [1.8, -0.1, -0.4], height: 2.3, phase: 3.1 },
  ];

  return (
    <group ref={group}>
      {racks.map((r, i) => (
        <RackUnit key={i} {...r} />
      ))}
      <CoolantCore />
      <ParticleStream />
    </group>
  );
}

export default function HeroScene({ className = "" }) {
  return (
    <div className={className} aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0.6, 6.2], fov: 42 }}
        dpr={[1, 1.75]}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={[0, 0, 0, 0]} />
        <ambientLight intensity={0.35} />
        <pointLight position={[4, 4, 4]} intensity={40} color="#2b7fff" />
        <pointLight position={[-4, -2, -3]} intensity={25} color="#22d3ee" />
        <Suspense fallback={null}>
          <Rig />
        </Suspense>
      </Canvas>
    </div>
  );
}
