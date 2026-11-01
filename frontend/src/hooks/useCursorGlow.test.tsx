import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CursorGlow } from "../components/CursorGlow";

describe("cursor glow", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("does not attach pointer listeners when reduced motion is enabled", () => {
    const originalMatchMedia = window.matchMedia;
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn((query: string) => ({
        matches: query.includes("prefers-reduced-motion"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    const addEventSpy = vi.spyOn(window, "addEventListener");

    render(<CursorGlow />);

    expect(
      addEventSpy.mock.calls.some(([eventName]) => eventName === "pointermove"),
    ).toBe(false);
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: originalMatchMedia,
    });
  });
});
