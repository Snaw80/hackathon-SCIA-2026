"use client";

import { useEffect, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { OrthographicCamera } from "three";
import type { projectOffice } from "@/lib/office-state";
import { Box, Desk, Person, Plant } from "./office-objects";

export type SceneProps = {
  room: ReturnType<typeof projectOffice>;
  selected: string;
  animate: boolean;
  reset: number;
  orbitEnabled: boolean;
  onSelect: (id: string) => void;
  onUnavailable: () => void;
};

function CameraRig({ reset, enabled }: { reset: number; enabled: boolean }) {
  const { camera, size, invalidate } = useThree();
  const controls = useRef<OrbitControlsImpl>(null);
  useEffect(() => {
    if (camera instanceof OrthographicCamera) {
      camera.zoom = Math.min(size.width / 17.5, size.height / 12.5);
      camera.position.set(11, 10, 13);
      camera.lookAt(0, 0.6, 0);
      camera.updateProjectionMatrix();
      controls.current?.target.set(0, 0.6, 0);
      controls.current?.update();
      invalidate();
    }
  }, [camera, size.width, size.height, reset, invalidate]);
  return enabled ? (
    <OrbitControls
      ref={controls}
      target={[0, 0.6, 0]}
      enablePan={false}
      enableZoom={false}
      enableDamping={false}
      minPolarAngle={0.55}
      maxPolarAngle={1.15}
      minAzimuthAngle={0.1}
      maxAzimuthAngle={1.25}
    />
  ) : null;
}

function ContextGuard({ onUnavailable }: { onUnavailable: () => void }) {
  const canvas = useThree((s) => s.gl.domElement);
  useEffect(() => {
    const lost = (event: Event) => {
      event.preventDefault();
      onUnavailable();
    };
    canvas.addEventListener("webglcontextlost", lost);
    return () => canvas.removeEventListener("webglcontextlost", lost);
  }, [canvas, onUnavailable]);
  return null;
}

function Room({ room }: Pick<SceneProps, "room">) {
  const signal =
    room.security === "safe"
      ? "#9edc99"
      : room.security === "critical"
        ? "#ef867a"
        : "#edbd73";
  return (
    <>
      <Box position={[0, -0.21, 0]} size={[12.5, 0.42, 9]} color="#354757" />
      <Box position={[0, 0.015, 0]} size={[12.1, 0.04, 8.6]} color="#899a9b" />
      {[-4, -2, 0, 2, 4].map((x) => (
        <Box
          key={x}
          position={[x, 0.04, 0]}
          size={[0.018, 0.008, 8.55]}
          color="#7f9092"
        />
      ))}
      <Box
        position={[0, 1.6, -4.35]}
        size={[12.5, 3.4, 0.16]}
        color="#536579"
      />
      <Box position={[-6.2, 1.3, 0]} size={[0.16, 2.8, 8.8]} color="#6b7c89" />
      <Box
        position={[0, 0.16, -4.23]}
        size={[12.25, 0.28, 0.09]}
        color="#344657"
      />
      <Box
        position={[-6.08, 0.16, 0]}
        size={[0.09, 0.28, 8.65]}
        color="#526270"
      />
      <Box
        position={[-3.5, 2, -4.23]}
        size={[3.5, 1.7, 0.08]}
        color="#263b50"
      />
      <Box
        position={[-3.5, 2, -4.17]}
        size={[3.22, 1.43, 0.02]}
        color="#9cc5ce"
        emissive="#659caa"
      />
      <Box
        position={[-3.5, 2, -4.12]}
        size={[0.06, 1.43, 0.04]}
        color="#3c5267"
      />
      <Box
        position={[-3.5, 2, -4.12]}
        size={[3.22, 0.06, 0.04]}
        color="#3c5267"
      />
      <Box
        position={[-3.5, 1.24, -4.03]}
        size={[3.6, 0.1, 0.3]}
        color="#aab7b6"
      />
      <Box
        position={[1.15, 2.05, -4.22]}
        size={[3.5, 1.75, 0.13]}
        color="#233442"
      />
      <Box
        position={[1.15, 2.05, -4.14]}
        size={[3.27, 1.51, 0.02]}
        color="#162730"
      />
      <Html
        position={[1.15, 2.25, -4.08]}
        transform
        distanceFactor={3}
        zIndexRange={[3, 0]}
        style={{ pointerEvents: "none" }}
      >
        <div className="office-wall-display">
          <span>DELIVERY CONTROL</span>
          <strong>
            {room.progress}
            <small>%</small>
          </strong>
          <div>
            <i style={{ width: `${room.progress}%` }} />
          </div>
        </div>
      </Html>
      <Box
        position={[4.3, 1.1, -4.05]}
        size={[1.28, 2.1, 0.45]}
        color="#283b4c"
      />
      {[0, 1, 2, 3].map((i) => (
        <group key={i}>
          <Box
            position={[4.3, 0.45 + i * 0.42, -3.8]}
            size={[1.05, 0.29, 0.02]}
            color="#354b5b"
          />
          <Box
            position={[4.64, 0.45 + i * 0.42, -3.78]}
            size={[0.09, 0.06, 0.02]}
            color={signal}
            emissive={signal}
          />
        </group>
      ))}
      <Plant position={[-5.25, 0, -3.45]} scale={1.2} />
      <Plant position={[5.3, 0, 3.45]} scale={1.2} />
      <Plant position={[-5.3, 0, 3.45]} scale={0.8} />
      <Box
        position={[-5.8, 1.05, 0.1]}
        size={[0.48, 0.12, 1.4]}
        color="#d0c0a8"
      />
      <Plant position={[-5.75, 1.1, 0.15]} scale={0.45} />
      <mesh
        position={[0, 0.048, 1]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[3.25, 3.4]} />
        <meshStandardMaterial color="#647b7c" roughness={1} />
      </mesh>
      <mesh position={[0, 0.85, 0.1]} castShadow receiveShadow>
        <cylinderGeometry args={[1.13, 1.13, 0.12, 48]} />
        <meshStandardMaterial color="#c9b69a" roughness={0.8} />
      </mesh>
      <mesh position={[0, 0.42, 0.1]} castShadow>
        <cylinderGeometry args={[0.16, 0.36, 0.85, 12]} />
        <meshStandardMaterial color="#3c515d" />
      </mesh>
      <Box
        position={[0, 0.93, 0.1]}
        size={[0.36, 0.035, 0.48]}
        color="#e8e2cf"
        rotation={[0, 0.2, 0]}
      />
      <Box
        position={[0.4, 0.94, -0.18]}
        size={[0.27, 0.04, 0.35]}
        color="#526e78"
        rotation={[0, -0.3, 0]}
      />
      <Html
        position={[0, 0.07, 3.35]}
        transform
        rotation={[-Math.PI / 2, 0, 0]}
        distanceFactor={4}
        zIndexRange={[2, 0]}
        style={{ pointerEvents: "none" }}
      >
        <div className="office-floor-mark">MELTDOWN / 01</div>
      </Html>
      {room.characters.map((actor) => (
        <Desk
          key={actor.id}
          position={[actor.home[0], 0, actor.home[2] - 1.05]}
          color={actor.color}
          stress={actor.stress}
          screenColor={actor.id === "security" ? signal : actor.color}
        />
      ))}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.45, 0]}
        receiveShadow
      >
        <planeGeometry args={[200, 200]} />
        <shadowMaterial transparent opacity={0.24} />
      </mesh>
    </>
  );
}

export default function OfficeScene(props: SceneProps) {
  return (
    <Canvas
      orthographic
      shadows
      dpr={[1, 1.5]}
      frameloop={props.animate ? "always" : "demand"}
      camera={{ position: [11, 10, 13], zoom: 35, near: 0.1, far: 100 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      fallback={
        <div className="office-unavailable">
          WebGL is unavailable. Opening the 2D team overview…
        </div>
      }
      style={{ touchAction: props.orbitEnabled ? "none" : "pan-y" }}
      aria-label="Interactive 3D crisis office"
    >
      <ambientLight intensity={1.25} />
      <hemisphereLight args={["#d9eefa", "#74827f", 1.5]} />
      <directionalLight
        position={[2, 10, 6]}
        intensity={2.8}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-9}
        shadow-camera-right={9}
        shadow-camera-top={9}
        shadow-camera-bottom={-9}
        shadow-normalBias={0.045}
      />
      <directionalLight
        position={[-4, 4, -3]}
        intensity={1.3}
        color="#b5dbea"
      />
      <Room room={props.room} />
      {props.room.characters.map((actor) => (
        <Person
          key={actor.id}
          actor={actor}
          selected={props.selected === actor.id}
          animate={props.animate}
          onSelect={props.onSelect}
        />
      ))}
      <CameraRig reset={props.reset} enabled={props.orbitEnabled} />
      <ContextGuard onUnavailable={props.onUnavailable} />
    </Canvas>
  );
}
