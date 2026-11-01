import { useEffect, useRef } from "react";

const GLOW_SELECTOR = "[data-cursor-glow], .interactive-row";
const LERP = 0.18;

function supportsPointerGlow(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(hover: hover) and (pointer: fine)").matches &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function useCursorGlow() {
  const layerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!supportsPointerGlow()) return;

    const layer = layerRef.current;
    if (!layer) return;

    let frame = 0;
    let visible = !document.hidden;
    let active = false;
    let hovered: HTMLElement | null = null;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let localX = 0;
    let localY = 0;
    let targetLocalX = 0;
    let targetLocalY = 0;

    const renderFrame = () => {
      frame = 0;
      if (!visible || !active) return;
      currentX += (targetX - currentX) * LERP;
      currentY += (targetY - currentY) * LERP;
      layer.style.setProperty("--cursor-x", `${currentX}px`);
      layer.style.setProperty("--cursor-y", `${currentY}px`);
      if (hovered?.isConnected) {
        localX += (targetLocalX - localX) * LERP;
        localY += (targetLocalY - localY) * LERP;
        hovered.style.setProperty("--mx", `${localX}px`);
        hovered.style.setProperty("--my", `${localY}px`);
      }
      if (
        Math.abs(targetX - currentX) > 0.5 ||
        Math.abs(targetY - currentY) > 0.5 ||
        (hovered?.isConnected &&
          (Math.abs(targetLocalX - localX) > 0.5 ||
            Math.abs(targetLocalY - localY) > 0.5))
      ) {
        frame = window.requestAnimationFrame(renderFrame);
      }
    };

    const scheduleFrame = () => {
      if (!frame) frame = window.requestAnimationFrame(renderFrame);
    };

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === "touch" || !visible) return;
      targetX = event.clientX;
      targetY = event.clientY;
      active = true;
      layer.dataset.active = "true";

      const element = (event.target as Element | null)?.closest<HTMLElement>(
        GLOW_SELECTOR,
      );
      if (hovered !== element) {
        hovered?.style.removeProperty("--mx");
        hovered?.style.removeProperty("--my");
        hovered = element;
        localX = 0;
        localY = 0;
        targetLocalX = 0;
        targetLocalY = 0;
      }
      if (hovered) {
        const rect = hovered.getBoundingClientRect();
        targetLocalX = event.clientX - rect.left;
        targetLocalY = event.clientY - rect.top;
      }
      scheduleFrame();
    };

    const deactivate = () => {
      active = false;
      layer.dataset.active = "false";
      hovered?.style.removeProperty("--mx");
      hovered?.style.removeProperty("--my");
      hovered = null;
      if (frame) window.cancelAnimationFrame(frame);
      frame = 0;
    };

    const onVisibility = () => {
      visible = !document.hidden;
      if (!visible) deactivate();
    };
    const onPointerOut = (event: PointerEvent) => {
      if (!event.relatedTarget) deactivate();
    };

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerout", onPointerOut);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerout", onPointerOut);
      document.removeEventListener("visibilitychange", onVisibility);
      if (frame) window.cancelAnimationFrame(frame);
      hovered?.style.removeProperty("--mx");
      hovered?.style.removeProperty("--my");
      delete layer.dataset.active;
    };
  }, []);

  return layerRef;
}
