"use client";

import { useRef } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { MathUtils, type Group } from "three";
import type { OfficeCharacter, Position } from "@/lib/office-state";

export function Box({
  position,
  size,
  color,
  rotation,
  emissive,
}: {
  position: Position;
  size: Position;
  color: string;
  rotation?: Position;
  emissive?: string;
}) {
  return (
    <mesh position={position} rotation={rotation} castShadow receiveShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial
        color={color}
        roughness={0.75}
        emissive={emissive}
        emissiveIntensity={emissive ? 0.45 : 0}
      />
    </mesh>
  );
}

function Cylinder({
  position,
  radius,
  height,
  color,
}: {
  position: Position;
  radius: number;
  height: number;
  color: string;
}) {
  return (
    <mesh position={position} castShadow receiveShadow>
      <cylinderGeometry args={[radius, radius, height, 12]} />
      <meshStandardMaterial color={color} roughness={0.8} />
    </mesh>
  );
}

export function Plant({
  position,
  scale = 1,
}: {
  position: Position;
  scale?: number;
}) {
  return (
    <group position={position} scale={scale}>
      <Cylinder
        position={[0, 0.22, 0]}
        radius={0.25}
        height={0.44}
        color="#c9b8a0"
      />
      <Cylinder
        position={[0, 0.6, 0]}
        radius={0.035}
        height={0.8}
        color="#5c7253"
      />
      {[
        [-0.18, 0.82, 0],
        [0.22, 1.02, 0.06],
        [0, 1.25, 0],
        [0.08, 0.73, 0.2],
      ].map((p, i) => (
        <mesh
          key={i}
          position={p as Position}
          rotation={[0, i, 0.3 * (i % 2 ? 1 : -1)]}
          scale={[0.34, 0.45, 0.22]}
          castShadow
        >
          <icosahedronGeometry args={[1, 0]} />
          <meshStandardMaterial
            color={i % 2 ? "#60997d" : "#3c755b"}
            roughness={1}
          />
        </mesh>
      ))}
    </group>
  );
}

export function Desk({
  position,
  color,
  stress,
  screenColor,
}: {
  position: Position;
  color: string;
  stress: number;
  screenColor: string;
}) {
  return (
    <group position={position}>
      <Box position={[0, 0.85, 0]} size={[2.15, 0.14, 1.15]} color="#baa992" />
      {[-0.85, 0.85].map((x) => (
        <Box
          key={x}
          position={[x, 0.4, 0]}
          size={[0.1, 0.8, 0.85]}
          color="#39495a"
        />
      ))}
      <Box
        position={[0, 1.3, -0.24]}
        size={[0.92, 0.57, 0.085]}
        color="#202c39"
      />
      <Box
        position={[0, 1.3, -0.191]}
        size={[0.81, 0.45, 0.014]}
        color={screenColor}
        emissive={screenColor}
      />
      <Box
        position={[0, 1.03, -0.25]}
        size={[0.06, 0.3, 0.06]}
        color="#263543"
      />
      <Box
        position={[0, 0.95, -0.22]}
        size={[0.45, 0.035, 0.25]}
        color="#263543"
      />
      <Box
        position={[0, 0.945, 0.22]}
        size={[0.66, 0.035, 0.23]}
        color="#e0e5e6"
      />
      <Box
        position={[0.47, 0.945, 0.23]}
        size={[0.11, 0.035, 0.17]}
        color="#e0e5e6"
      />
      <Cylinder
        position={[-0.75, 1.01, 0.18]}
        radius={0.085}
        height={0.16}
        color={color}
      />
      <Box
        position={[-0.64, 0.95, -0.28]}
        size={[0.26, 0.035, 0.32]}
        color="#e6e2ce"
        rotation={[0, 0.15, 0]}
      />
      {stress > 70 &&
        [0, 1, 2, 3].map((i) => (
          <Box
            key={i}
            position={[0.68, 0.95 + i * 0.035, -0.15 + i * 0.025]}
            size={[0.4, 0.027, 0.35]}
            rotation={[0, i * 0.23, 0]}
            color={i % 2 ? "#e9d6a2" : "#c5d4c8"}
          />
        ))}
      <Box
        position={[0, 0.42, 0.9]}
        size={[0.56, 0.12, 0.55]}
        color="#364858"
      />
      <Box
        position={[0, 0.69, 1.13]}
        size={[0.55, 0.5, 0.095]}
        color="#364858"
      />
      <Cylinder
        position={[0, 0.2, 0.9]}
        radius={0.055}
        height={0.4}
        color="#8393a4"
      />
      <Box
        position={[0, 0.065, 0.9]}
        size={[0.66, 0.08, 0.1]}
        color="#596d7a"
      />
      <Box
        position={[0, 0.065, 0.9]}
        size={[0.1, 0.08, 0.66]}
        color="#596d7a"
      />
      <Box
        position={[0.87, 0.54, -0.02]}
        size={[0.4, 0.54, 0.7]}
        color="#819097"
      />
      <Box
        position={[0.87, 0.68, 0.34]}
        size={[0.12, 0.025, 0.02]}
        color="#d7dedc"
      />
    </group>
  );
}

const skin: Record<string, string> = {
  developer: "#d8a17d",
  client: "#be8364",
  sales: "#e0b391",
  security: "#805b49",
};
const hair: Record<string, string> = {
  developer: "#473e3a",
  client: "#42333e",
  sales: "#785b3d",
  security: "#292c31",
};

export function Person({
  actor,
  selected,
  animate,
  onSelect,
}: {
  actor: OfficeCharacter;
  selected: boolean;
  animate: boolean;
  onSelect: (id: string) => void;
}) {
  const root = useRef<Group>(null);
  const body = useRef<Group>(null);
  const leftArm = useRef<Group>(null);
  const rightArm = useRef<Group>(null);
  const time = useRef(0);
  const destination = actor.position;
  useFrame((_, delta) => {
    if (!root.current || !body.current || !leftArm.current || !rightArm.current)
      return;
    time.current += Math.min(delta, 0.05);
    const t = time.current;
    const moving =
      Math.hypot(
        root.current.position.x - destination[0],
        root.current.position.z - destination[2],
      ) > 0.025;
    root.current.position.x = animate
      ? MathUtils.damp(root.current.position.x, destination[0], 5, delta)
      : destination[0];
    root.current.position.z = animate
      ? MathUtils.damp(root.current.position.z, destination[2], 5, delta)
      : destination[2];
    body.current.position.y =
      animate && (moving || actor.pose === "celebrate")
        ? Math.abs(Math.sin(t * 7)) * 0.07
        : 0;
    body.current.rotation.z =
      animate && actor.stress > 70 ? Math.sin(t * 3) * 0.025 : 0;
    body.current.rotation.x = actor.pose === "blocked" ? 0.18 : 0;
    const gesture =
      actor.pose === "talking" ? 0.6 : actor.pose === "celebrate" ? 2.4 : 0.12;
    leftArm.current.rotation.z =
      gesture + (animate ? Math.sin(t * 3) * 0.07 : 0);
    rightArm.current.rotation.z = -gesture;
    leftArm.current.rotation.x =
      animate && (moving || actor.pose === "working")
        ? Math.sin(t * 8) * 0.2
        : 0;
    rightArm.current.rotation.x = -leftArm.current.rotation.x;
  });
  return (
    <group ref={root} position={actor.home}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.025, 0]}>
        <ringGeometry
          args={[selected ? 0.38 : 0.31, selected ? 0.44 : 0.34, 40]}
        />
        <meshBasicMaterial
          color={actor.stress > 70 ? "#ff9c83" : actor.color}
          transparent
          opacity={selected ? 1 : 0.4}
        />
      </mesh>
      <group
        ref={body}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(actor.id);
        }}
      >
        <Box
          position={[-0.12, 0.25, 0]}
          size={[0.16, 0.5, 0.19]}
          color="#273745"
        />
        <Box
          position={[0.12, 0.25, 0]}
          size={[0.16, 0.5, 0.19]}
          color="#273745"
        />
        <Box
          position={[-0.12, 0.065, 0.055]}
          size={[0.2, 0.13, 0.33]}
          color="#e1ded3"
        />
        <Box
          position={[0.12, 0.065, 0.055]}
          size={[0.2, 0.13, 0.33]}
          color="#e1ded3"
        />
        <Box
          position={[0, 0.72, 0]}
          size={[0.5, 0.54, 0.28]}
          color={actor.color}
        />
        <Box
          position={[0, 1.04, 0]}
          size={[0.14, 0.15, 0.14]}
          color={skin[actor.id] || "#c89875"}
        />
        <mesh position={[0, 1.26, 0]} castShadow>
          <boxGeometry args={[0.38, 0.4, 0.34]} />
          <meshStandardMaterial
            color={skin[actor.id] || "#c89875"}
            roughness={0.9}
          />
        </mesh>
        <Box
          position={[0, 1.46, -0.025]}
          size={[0.41, 0.13, 0.38]}
          color={hair[actor.id] || "#333333"}
        />
        {actor.id === "client" && (
          <Box
            position={[0, 1.25, -0.17]}
            size={[0.43, 0.42, 0.12]}
            color="#42333e"
          />
        )}
        {[-0.08, 0.08].map((x) => (
          <Box
            key={x}
            position={[x, 1.28, 0.179]}
            size={[0.045, 0.045, 0.02]}
            color="#25313b"
          />
        ))}
        {actor.id === "developer" && (
          <>
            <Box
              position={[-0.09, 1.29, 0.19]}
              size={[0.15, 0.1, 0.03]}
              color="#344d60"
            />
            <Box
              position={[0.09, 1.29, 0.19]}
              size={[0.15, 0.1, 0.03]}
              color="#344d60"
            />
          </>
        )}
        {actor.id === "sales" && (
          <Box
            position={[0, 0.75, 0.155]}
            size={[0.075, 0.37, 0.025]}
            color="#735740"
          />
        )}
        {actor.id === "security" && (
          <Box
            position={[-0.12, 0.8, 0.16]}
            size={[0.09, 0.13, 0.02]}
            color="#e3eddd"
          />
        )}
        <group ref={leftArm} position={[-0.32, 0.94, 0]}>
          <Box
            position={[0, -0.18, 0]}
            size={[0.14, 0.4, 0.18]}
            color={actor.color}
          />
          <Box
            position={[0, -0.42, 0]}
            size={[0.14, 0.12, 0.15]}
            color={skin[actor.id]}
          />
        </group>
        <group ref={rightArm} position={[0.32, 0.94, 0]}>
          <Box
            position={[0, -0.18, 0]}
            size={[0.14, 0.4, 0.18]}
            color={actor.color}
          />
          <Box
            position={[0, -0.42, 0]}
            size={[0.14, 0.12, 0.15]}
            color={skin[actor.id]}
          />
        </group>
      </group>
      <Html position={[0, 1.98, 0]} center zIndexRange={[5, 0]}>
        <button
          type="button"
          className={`office-name ${selected ? "selected" : ""}`}
          style={{ "--person-color": actor.color } as React.CSSProperties}
          aria-label={`Inspect ${actor.name}`}
          aria-pressed={selected}
          onClick={() => onSelect(actor.id)}
        >
          <span />
          {actor.name}
          {actor.stress > 70 && <b aria-label="High pressure">!</b>}
        </button>
      </Html>
    </group>
  );
}
