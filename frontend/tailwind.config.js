/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "rgba(10, 8, 25, 0.78)",
        panel: "rgba(255, 255, 255, 0.06)",
        border: "rgba(255, 255, 255, 0.12)",
        text: "#F2F0FF",
        secondary: "#B8B1D3",
        brand: "#8B5CF6",
        critical: "#F85149",
        high: "#FF8C42",
        medium: "#E3B341",
        low: "#58A6FF",
        safe: "#3FB950",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: { lg: "1.25rem", xl: "1.5rem", "2xl": "1.75rem" },
      boxShadow: {
        glass:
          "0 24px 70px rgba(4, 2, 18, .42), inset 0 1px 0 rgba(255,255,255,.16)",
      },
    },
  },
  plugins: [],
};
