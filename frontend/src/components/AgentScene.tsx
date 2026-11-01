import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";

const agents = [
  {
    label: "Bug",
    color: "#fda4af",
    position: [-1.55, 0.9, 0.2] as [number, number, number],
  },
  {
    label: "Security",
    color: "#c4b5fd",
    position: [1.5, 0.85, -0.2] as [number, number, number],
  },
  {
    label: "Quality",
    color: "#a5b4fc",
    position: [-1.65, -0.75, -0.1] as [number, number, number],
  },
  {
    label: "Test coverage",
    color: "#67e8f9",
    position: [1.55, -0.78, 0.1] as [number, number, number],
  },
  {
    label: "Semgrep",
    color: "#86efac",
    position: [0, 1.7, -0.3] as [number, number, number],
  },
];

function hasWebGLSupport(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

function Shield() {
  const group = useRef<THREE.Group>(null);
  const geometry = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(0, 1.35);
    shape.lineTo(1, 0.95);
    shape.lineTo(0.88, -0.25);
    shape.quadraticCurveTo(0.65, -0.95, 0, -1.35);
    shape.quadraticCurveTo(-0.65, -0.95, -0.88, -0.25);
    shape.lineTo(-1, 0.95);
    shape.closePath();
    return new THREE.ExtrudeGeometry(shape, {
      depth: 0.14,
      bevelEnabled: true,
      bevelSegments: 3,
      steps: 1,
      bevelSize: 0.09,
      bevelThickness: 0.08,
      curveSegments: 10,
    });
  }, []);
  useFrame(({ clock, pointer }) => {
    if (group.current) {
      group.current.rotation.y =
        Math.sin(clock.elapsedTime * 0.32) * 0.3 + pointer.x * 0.12;
      group.current.rotation.x =
        Math.sin(clock.elapsedTime * 0.2) * 0.05 - pointer.y * 0.08;
      group.current.position.y = Math.sin(clock.elapsedTime * 0.7) * 0.08;
    }
  });
  return (
    <group ref={group} position={[0, 0, 0]} scale={0.8}>
      <mesh geometry={geometry} position={[0, 0, -0.08]}>
        <meshPhysicalMaterial
          color="#a78bfa"
          metalness={0.12}
          roughness={0.14}
          transmission={0.62}
          thickness={0.8}
          ior={1.3}
          clearcoat={1}
          clearcoatRoughness={0.08}
          transparent
          opacity={0.94}
          emissive="#5b21b6"
          emissiveIntensity={0.24}
        />
      </mesh>
      <mesh position={[0, -0.02, 0.12]} scale={0.42}>
        <torusGeometry args={[1, 0.025, 10, 80]} />
        <meshBasicMaterial color="#e9d5ff" transparent opacity={0.8} />
      </mesh>
    </group>
  );
}

function AgentOrbit() {
  const group = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (group.current) group.current.rotation.y = clock.elapsedTime * 0.12;
  });
  return (
    <group ref={group}>
      {agents.map((agent) => (
        <group key={agent.label} position={agent.position}>
          <mesh>
            <sphereGeometry args={[0.085, 24, 24]} />
            <meshStandardMaterial
              color={agent.color}
              emissive={agent.color}
              emissiveIntensity={1.8}
              roughness={0.25}
            />
          </mesh>
          <mesh scale={1.85}>
            <sphereGeometry args={[0.085, 16, 16]} />
            <meshBasicMaterial color={agent.color} transparent opacity={0.12} />
          </mesh>
          <Line
            points={[
              [0, 0, 0],
              [agent.position[0] * -0.62, agent.position[1] * -0.62, 0],
            ]}
            color={agent.color}
            transparent
            opacity={0.28}
            lineWidth={1}
          />
        </group>
      ))}
    </group>
  );
}

function SceneContent() {
  return (
    <>
      <ambientLight intensity={0.85} />
      <pointLight position={[4, 3, 5]} intensity={38} color="#a78bfa" />
      <pointLight position={[-4, -3, 2]} intensity={20} color="#22d3ee" />
      <Shield />
      <AgentOrbit />
    </>
  );
}

export default function AgentScene() {
  const host = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [active, setActive] = useState(!document.hidden);
  const [small, setSmall] = useState(
    () => window.matchMedia("(max-width: 720px)").matches,
  );
  const [webglAvailable] = useState(hasWebGLSupport);

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.05 },
    );
    observer.observe(element);
    const visibility = () => setActive(!document.hidden);
    const resize = () =>
      setSmall(window.matchMedia("(max-width: 720px)").matches);
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("resize", resize, { passive: true });
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div
      ref={host}
      className="hero-scene relative h-[330px] w-full overflow-hidden rounded-[32px] sm:h-[430px]"
      aria-label="Animated three-dimensional shield with orbiting review agent nodes"
    >
      <div className="pointer-events-none absolute inset-[10%] rounded-full bg-violet-500/20 blur-[70px]" />
      {visible && active && !small && webglAvailable ? (
        <Canvas
          dpr={[1, 2]}
          camera={{ position: [0, 0, 5.5], fov: 42 }}
          gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}
        >
          <SceneContent />
        </Canvas>
      ) : (
        <StaticScene />
      )}
      <div className="pointer-events-none absolute inset-0">
        {agents.map((agent, index) => (
          <span
            key={agent.label}
            className={`absolute rounded-full border border-white/10 bg-[#100c24]/75 px-2.5 py-1 text-[9px] font-medium text-secondary shadow-[0_8px_25px_rgba(0,0,0,.28)] backdrop-blur-xl sm:px-3 sm:text-[10px] ${index === 0 ? "left-[3%] top-[25%]" : index === 1 ? "right-[2%] top-[27%]" : index === 2 ? "bottom-[27%] left-[2%]" : index === 3 ? "bottom-[24%] right-[1%]" : "left-1/2 top-[7%] -translate-x-1/2"}`}
          >
            {agent.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function StaticScene() {
  return (
    <div
      className="absolute inset-0 grid place-items-center"
      aria-hidden="true"
    >
      <div className="relative grid h-56 w-56 place-items-center rounded-full bg-[radial-gradient(circle,rgba(139,92,246,.35),rgba(79,70,229,.10)_48%,transparent_70%)]">
        <svg
          viewBox="0 0 180 200"
          className="h-40 w-40 drop-shadow-[0_0_28px_rgba(139,92,246,.55)]"
        >
          <defs>
            <linearGradient id="shield-fallback" x1="0" x2="1" y1="0" y2="1">
              <stop stopColor="#c4b5fd" stopOpacity=".85" />
              <stop offset="1" stopColor="#6d28d9" stopOpacity=".35" />
            </linearGradient>
          </defs>
          <path
            d="M90 12 155 38v48c0 47-27 79-65 102C52 165 25 133 25 86V38z"
            fill="url(#shield-fallback)"
            stroke="#ddd6fe"
            strokeOpacity=".65"
            strokeWidth="2"
          />
          <path
            d="m61 99 19 19 40-44"
            fill="none"
            stroke="#f5f3ff"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="8"
          />
        </svg>
        <span className="absolute inset-1 rounded-full border border-violet-200/25" />
        <span className="absolute inset-5 rounded-full border border-cyan-200/15" />
      </div>
    </div>
  );
}
