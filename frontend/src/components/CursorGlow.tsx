import { useCursorGlow } from "../hooks/useCursorGlow";

export function CursorGlow() {
  const ref = useCursorGlow();
  return <div ref={ref} className="ambient-cursor-glow" aria-hidden="true" />;
}
