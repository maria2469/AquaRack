import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Clean & Optimized 3D Scene for the Problem Page:
 * Represents an Overheating AI Server Rack with an Evaporating Cooling Water Pipe.
 * Directly visualises AquaMind AI's core problem: high thermal compute load causing water depletion & wastage.
 */

function OverheatingServerRack({ position = [2.0, -0.2, 0] }) {
  const rackRef = useRef();
  const thermalGlowRef = useRef();
  const ledRef = useRef();

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    // Subtle thermal vibration when rack is under 95%+ GPU load
    if (rackRef.current) {
      rackRef.current.position.y = position[1] + Math.sin(t * 14.0) * 0.015;
    }

    // Frantic red thermal warning pulse on status LEDs
    if (ledRef.current) {
      const pulse = 0.4 + 0.6 * Math.abs(Math.sin(t * 3.5));
      ledRef.current.material.emissiveIntensity = pulse * 1.8;
    }

    // Thermal heat emission pulsing from server core
    if (thermalGlowRef.current) {
      const heat = 0.5 + 0.5 * Math.sin(t * 2.0);
      thermalGlowRef.current.material.emissiveIntensity = heat * 1.4;
    }
  });

  return (
    <group ref={rackRef} position={position} rotation={[0, -0.35, 0]}>
      {/* Rack Main Chassis */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1.2, 2.8, 1.0]} />
        <meshStandardMaterial color="#0b131e" metalness={0.8} roughness={0.25} />
      </mesh>

      {/* Rack Front Panel Grill */}
      <mesh position={[0, 0, 0.51]}>
        <planeGeometry args={[1.0, 2.5]} />
        <meshStandardMaterial color="#050a10" roughness={0.8} />
      </mesh>

      {/* Overheating GPU Server Blades (4 Slots) */}
      {[-0.8, -0.25, 0.3, 0.85].map((y, i) => (
        <group key={i} position={[0, y, 0.52]}>
          <mesh>
            <boxGeometry args={[0.92, 0.35, 0.05]} />
            <meshStandardMaterial color="#1e293b" metalness={0.5} />
          </mesh>
          {/* Heat Ventilation Vent Glowing Red */}
          <mesh position={[0, 0, 0.03]}>
            <planeGeometry args={[0.75, 0.2]} />
            <meshStandardMaterial color="#1e1b4b" emissive="#ef4444" emissiveIntensity={0.8} />
          </mesh>
        </group>
      ))}

      {/* Red Warning Status LEDs Strip */}
      <mesh ref={ledRef} position={[0.42, 0, 0.53]}>
        <boxGeometry args={[0.04, 2.4, 0.02]} />
        <meshStandardMaterial
          color="#ef4444"
          emissive="#ef4444"
          emissiveIntensity={1.5}
          toneMapped={false}
        />
      </mesh>

      {/* Thermal Heat Core Glow (Behind Server) */}
      <mesh ref={thermalGlowRef} position={[0, 0, -0.1]}>
        <boxGeometry args={[1.1, 2.6, 0.8]} />
        <meshStandardMaterial
          color="#450a0a"
          emissive="#dc2626"
          emissiveIntensity={0.8}
          wireframe
          transparent
          opacity={0.35}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

/**
 * Cooling Water Depletion Gauge (Glass Pipe with Draining Water Level)
 */
function WaterDepletionGauge({ position = [3.5, -0.2, 0.2] }) {
  const waterLevelRef = useRef();

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (waterLevelRef.current) {
      // Water level continuously dropping / fluctuating due to unoptimized evaporation
      const level = 0.5 + 0.35 * Math.sin(t * 0.8);
      waterLevelRef.current.scale.set(1, Math.max(0.1, level), 1);
      waterLevelRef.current.position.y = (level - 1) * 1.1;
    }
  });

  return (
    <group position={position}>
      {/* Outer Glass Pipe */}
      <mesh>
        <cylinderGeometry args={[0.22, 0.22, 2.4, 24]} />
        <meshStandardMaterial color="#64748b" transparent opacity={0.3} roughness={0.1} metalness={0.9} />
      </mesh>

      {/* Draining Water Reservoir Inside */}
      <group position={[0, 0, 0]}>
        <mesh ref={waterLevelRef}>
          <cylinderGeometry args={[0.18, 0.18, 2.2, 20]} />
          <meshStandardMaterial color="#0284c7" emissive="#0369a1" emissiveIntensity={0.7} toneMapped={false} />
        </mesh>
      </group>

      {/* Pipe Mounting Rings */}
      {[-1.1, 0, 1.1].map((y, i) => (
        <mesh key={i} position={[0, y, 0]}>
          <torusGeometry args={[0.24, 0.03, 8, 24]} />
          <meshStandardMaterial color="#334155" metalness={0.8} />
        </mesh>
      ))}
    </group>
  );
}

/**
 * Thermal Heat Steam Particles rising from the overheating server
 */
function ThermalSteamParticles({ count = 120 }) {
  const ref = useRef();

  const { positions, speeds } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const speeds = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = 1.8 + (Math.random() - 0.5) * 2.2;
      positions[i * 3 + 1] = -1.2 + Math.random() * 3.5;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 1.8;
      speeds[i] = 0.4 + Math.random() * 0.8;
    }
    return { positions, speeds };
  }, [count]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const arr = ref.current.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      arr[i * 3 + 1] += delta * speeds[i];
      if (arr[i * 3 + 1] > 2.2) {
        arr[i * 3 + 1] = -1.2;
        arr[i * 3] = 1.8 + (Math.random() - 0.5) * 2.2;
      }
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
        size={0.06}
        color="#f59e0b"
        transparent
        opacity={0.5}
        sizeAttenuation
        toneMapped={false}
      />
    </points>
  );
}

function Scene() {
  const groupRef = useRef();

  useFrame(({ clock, pointer }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    groupRef.current.rotation.y = Math.sin(t * 0.05) * 0.12 + pointer.x * 0.12;
    groupRef.current.rotation.x = pointer.y * 0.04;
  });

  return (
    <group ref={groupRef}>
      <OverheatingServerRack position={[2.0, -0.2, 0]} />
      <WaterDepletionGauge position={[3.3, -0.2, 0.2]} />
      <ThermalSteamParticles />
    </group>
  );
}

export default function WaterDropScene({ className = "" }) {
  return (
    <div className={className} aria-hidden="true">
      <Canvas
        camera={{ position: [0.6, 0.2, 5.4], fov: 42 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={[0, 0, 0, 0]} />
        <ambientLight intensity={0.4} />
        
        {/* Warning red thermal lighting */}
        <pointLight position={[2.5, 2.5, 3.0]} intensity={50} color="#ef4444" />
        <pointLight position={[3.5, -1.0, 2.0]} intensity={30} color="#f59e0b" />
        <pointLight position={[-3.0, 0.0, -2.0]} intensity={20} color="#22d3ee" />
        
        <Scene />
      </Canvas>
    </div>
  );
}
