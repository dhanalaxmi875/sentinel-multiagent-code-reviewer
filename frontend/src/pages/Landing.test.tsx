import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Landing from "./Landing";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Landing page fallback", () => {
  it("renders the static hero illustration without a WebGL canvas when motion is reduced", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(
        (query: string) =>
          ({
            matches: query.includes("prefers-reduced-motion"),
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(() => false),
          }) as unknown as MediaQueryList,
      ),
    );

    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    expect(
      screen.getByLabelText("Static SentinelCode shield illustration"),
    ).toBeInTheDocument();
    expect(document.querySelector("canvas")).toBeNull();
  });
});
