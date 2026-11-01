import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders with default variant", () => {
    render(<Badge>Test</Badge>);
    const badge = screen.getByText("Test");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-white/5");
  });

  it("renders with critical variant", () => {
    render(<Badge variant="critical">Critical</Badge>);
    const badge = screen.getByText("Critical");
    expect(badge.className).toContain("bg-critical/10");
    expect(badge.className).toContain("text-critical");
  });

  it("renders with high variant", () => {
    render(<Badge variant="high">High</Badge>);
    const badge = screen.getByText("High");
    expect(badge.className).toContain("bg-high/10");
  });

  it("renders with medium variant", () => {
    render(<Badge variant="medium">Medium</Badge>);
    const badge = screen.getByText("Medium");
    expect(badge.className).toContain("bg-medium/10");
  });

  it("renders with low variant", () => {
    render(<Badge variant="low">Low</Badge>);
    const badge = screen.getByText("Low");
    expect(badge.className).toContain("bg-low/10");
  });

  it("renders with safe variant", () => {
    render(<Badge variant="safe">Safe</Badge>);
    const badge = screen.getByText("Safe");
    expect(badge.className).toContain("bg-safe/10");
  });

  it("renders with brand variant", () => {
    render(<Badge variant="brand">Brand</Badge>);
    const badge = screen.getByText("Brand");
    expect(badge.className).toContain("bg-brand/15");
  });

  it("renders with high confidence", () => {
    render(
      <Badge variant="secondary" confidence="high">
        High
      </Badge>,
    );
    const badge = screen.getByText("High");
    expect(badge.className).toContain("font-bold");
  });

  it("renders with medium confidence", () => {
    render(
      <Badge variant="secondary" confidence="medium">
        Medium
      </Badge>,
    );
    const badge = screen.getByText("Medium");
    expect(badge.className).toContain("border-2");
  });

  it("renders with low confidence", () => {
    render(
      <Badge variant="secondary" confidence="low">
        Low
      </Badge>,
    );
    const badge = screen.getByText("Low");
    expect(badge.className).toContain("border-dashed");
  });
});
