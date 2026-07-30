import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Custom GLSL Shader for a Cascading 3D Waterfall.
 * Animates high-velocity flowing water streams down a curved vertical surface
 * with foam streaks, specular highlights, and light refractions.
 */
const WaterfallStreamShader = {
  uniforms: {
    uTime: { value: 0 },
    uColorTop: { value: new THREE.Color("#67e8f9") },
    uColorMid: { value: new THREE.Color("#06b6d4") },
    uColorDeep: { value: new THREE.Color("#0284c7") },
    uColorFoam: { value: new THREE.Color("#f0f9ff") },
  },
  vertexShader: `
    uniform float uTime;
    varying vec2 vUv;
    varying float vElevation;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    // Simplex 3D noise
    vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
    vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

    float snoise(vec3 v){
      const vec2 C = vec2(1.0/6.0, 1.0/3.0);
      const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy) );
      vec3 x0 = v - i + dot(i, C.xxx) ;
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min( g.xyz, l.zxy );
      vec3 i2 = max( g.xyz, l.zxy );
      vec3 x1 = x0 - i1 + vec3(C.x);
      vec3 x2 = x0 - i2 + vec3(D.yyy);
      vec3 x3 = x0 - D.yyy;
      i = mod(i, 289.0 );
      vec4 p = permute( permute( permute(
                 i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
               + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
               + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
      float n_ = 0.142857142857;
      vec3  ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_ );
      vec4 x = x_ *ns.x + vec4(C.xxxx);
      vec4 y = y_ *ns.x + vec4(C.xxxx);
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4( x.xy, y.xy );
      vec4 b1 = vec4( x.zw, y.zw );
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
      vec3 p0 = vec3(a0.xy,h.x);
      vec3 p1 = vec3(a0.zw,h.y);
      vec3 p2 = vec3(a1.xy,h.z);
      vec3 p3 = vec3(a1.zw,h.w);
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
      p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
    }

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Downward flowing turbulent noise displacement
      float flowTime = uTime * 4.2;
      float noiseVal = snoise(vec3(pos.x * 2.0, pos.y * 3.0 - flowTime, uTime * 0.8)) * 0.18;
      noiseVal += snoise(vec3(pos.x * 5.0, pos.y * 8.0 - flowTime * 1.8, uTime * 1.5)) * 0.06;

      pos.z += noiseVal;
      vElevation = noiseVal;

      vec4 worldPosition = modelMatrix * vec4(pos, 1.0);
      vWorldPosition = worldPosition.xyz;
      vNormal = normalize(normalMatrix * normal);

      gl_Position = projectionMatrix * viewMatrix * worldPosition;
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform vec3 uColorTop;
    uniform vec3 uColorMid;
    uniform vec3 uColorDeep;
    uniform vec3 uColorFoam;

    varying vec2 vUv;
    varying float vElevation;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      // Flow velocity streaking along vertical UV
      float flowTime = uTime * 5.0;
      float foamStreaks = sin((vUv.y * 25.0 - flowTime) + sin(vUv.x * 12.0)) * 0.5 + 0.5;
      foamStreaks = smoothstep(0.45, 0.9, foamStreaks);

      // Height gradient
      vec3 color = mix(uColorTop, uColorMid, 1.0 - vUv.y);
      color = mix(color, uColorDeep, (1.0 - vUv.y) * 0.5);

      // Foam streaks integration
      color = mix(color, uColorFoam, foamStreaks * 0.7);

      // Top & Bottom splash white water highlights
      float topSplash = smoothstep(0.85, 1.0, vUv.y);
      float bottomSplash = smoothstep(0.15, 0.0, vUv.y);
      color = mix(color, uColorFoam, topSplash * 0.8 + bottomSplash * 0.9);

      // Fresnel specular sheen
      vec3 viewDir = normalize(cameraPosition - vWorldPosition);
      float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 3.0);
      color += vec3(0.5, 0.9, 1.0) * fresnel * 0.7;

      // Soft edge fading on left/right
      float edgeAlpha = smoothstep(0.0, 0.15, vUv.x) * smoothstep(1.0, 0.85, vUv.x);

      gl_FragColor = vec4(color, 0.85 * edgeAlpha);
    }
  `,
};

/**
 * Water Basin Surface Shader (The pool at the bottom of the waterfall)
 */
const BasinWaterShader = {
  uniforms: {
    uTime: { value: 0 },
    uColorDeep: { value: new THREE.Color("#022c43") },
    uColorCyan: { value: new THREE.Color("#06b6d4") },
    uColorTeal: { value: new THREE.Color("#10b981") },
    uColorFoam: { value: new THREE.Color("#e0f2fe") },
  },
  vertexShader: `
    uniform float uTime;
    varying vec2 vUv;
    varying float vElevation;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Concentric impact ripples expanding from center waterfall base (0,0)
      float distFromImpact = length(pos.xy);
      float ripple = sin(distFromImpact * 4.0 - uTime * 4.0) * exp(-distFromImpact * 0.35) * 0.15;

      pos.z += ripple;
      vElevation = ripple;

      vec4 worldPosition = modelMatrix * vec4(pos, 1.0);
      vWorldPosition = worldPosition.xyz;
      vNormal = normalize(normalMatrix * normal);

      gl_Position = projectionMatrix * viewMatrix * worldPosition;
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform vec3 uColorDeep;
    uniform vec3 uColorCyan;
    uniform vec3 uColorTeal;
    uniform vec3 uColorFoam;

    varying vec2 vUv;
    varying float vElevation;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      float mixStep = smoothstep(-0.2, 0.2, vElevation);
      vec3 color = mix(uColorDeep, uColorCyan, mixStep);

      // Splash foam around center impact
      float distFromImpact = length(vWorldPosition.xz);
      float foamRadius = smoothstep(2.5, 0.2, distFromImpact);
      color = mix(color, uColorFoam, foamRadius * 0.55);

      vec3 viewDir = normalize(cameraPosition - vWorldPosition);
      float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 3.0);
      color += vec3(0.4, 0.85, 0.95) * fresnel * 0.7;

      gl_FragColor = vec4(color, 0.88);
    }
  `,
};

function WaterfallStream() {
  const meshRef = useRef();
  const materialRef = useRef();

  useFrame(({ clock }) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    }
  });

  return (
    <mesh ref={meshRef} position={[0, 0.8, -0.2]} rotation={[0.1, 0, 0]}>
      {/* Curved vertical curtain geometry */}
      <cylinderGeometry args={[2.2, 3.2, 5.8, 48, 64, true, -Math.PI * 0.4, Math.PI * 0.8]} />
      <shaderMaterial
        ref={materialRef}
        args={[WaterfallStreamShader]}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function BasinWaterPlane() {
  const meshRef = useRef();
  const materialRef = useRef();

  useFrame(({ clock }) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    }
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2.2, 0, 0]} position={[0, -1.8, 0]}>
      <planeGeometry args={[22, 22, 96, 96]} />
      <shaderMaterial
        ref={materialRef}
        args={[BasinWaterShader]}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function SplashMistParticles({ count = 280 }) {
  const ref = useRef();

  const { positions, speeds, sizes } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const speeds = new Float32Array(count);
    const sizes = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Emitter at waterfall impact area [0, -1.8, 0]
      const angle = Math.random() * Math.PI * 2;
      const radius = Math.random() * 2.4;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = -1.8 + Math.random() * 1.5;
      positions[i * 3 + 2] = Math.sin(angle) * radius - 0.2;

      speeds[i] = 0.6 + Math.random() * 1.2;
      sizes[i] = 0.05 + Math.random() * 0.09;
    }
    return { positions, speeds, sizes };
  }, [count]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const arr = ref.current.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      // Mist spray bursting upwards and outward from waterfall impact
      arr[i * 3 + 1] += delta * speeds[i];
      arr[i * 3] += (Math.random() - 0.5) * 0.02;
      arr[i * 3 + 2] += (Math.random() - 0.5) * 0.02;

      if (arr[i * 3 + 1] > 2.5) {
        const angle = Math.random() * Math.PI * 2;
        const radius = Math.random() * 2.2;
        arr[i * 3] = Math.cos(angle) * radius;
        arr[i * 3 + 1] = -1.8;
        arr[i * 3 + 2] = Math.sin(angle) * radius - 0.2;
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
        size={0.07}
        color="#e0f2fe"
        transparent
        opacity={0.7}
        sizeAttenuation
        toneMapped={false}
      />
    </points>
  );
}

function CascadingDroplets({ count = 220 }) {
  const ref = useRef();

  const { positions, speeds } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const speeds = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 4.5;
      positions[i * 3 + 1] = Math.random() * 5.5 - 1.5;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 2.0 - 0.2;
      speeds[i] = 2.5 + Math.random() * 3.5;
    }
    return { positions, speeds };
  }, [count]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const arr = ref.current.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      // High speed falling droplets within waterfall column
      arr[i * 3 + 1] -= delta * speeds[i];

      if (arr[i * 3 + 1] < -1.8) {
        arr[i * 3 + 1] = 3.6;
        arr[i * 3] = (Math.random() - 0.5) * 4.2;
        arr[i * 3 + 2] = (Math.random() - 0.5) * 1.8 - 0.2;
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
        size={0.05}
        color="#38bdf8"
        transparent
        opacity={0.85}
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
    groupRef.current.rotation.y = Math.sin(t * 0.05) * 0.15 + pointer.x * 0.12;
    groupRef.current.rotation.x = pointer.y * 0.04;
  });

  return (
    <group ref={groupRef}>
      <WaterfallStream />
      <BasinWaterPlane />
      <SplashMistParticles />
      <CascadingDroplets />
    </group>
  );
}

export default function WaterSaveScene({ className = "" }) {
  return (
    <div className={className} aria-hidden="true">
      <Canvas
        camera={{ position: [0, 1.2, 7.8], fov: 46 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={[0, 0, 0, 0]} />
        <ambientLight intensity={0.3} />
        <pointLight position={[0, 4, 3]} intensity={55} color="#38bdf8" />
        <pointLight position={[-4, -1, -2]} intensity={35} color="#10b981" />
        <pointLight position={[4, -1, 2]} intensity={30} color="#06b6d4" />
        <Scene />
      </Canvas>
    </div>
  );
}
