import type { Config } from "tailwindcss";

// Colores de marca via CSS vars -> white-label sin rebuild (costura multiempresa).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: "var(--brand-primary)",
        "brand-dark": "var(--brand-primary-dark)",
        ok: "#16a34a",
        warn: "#d97706",
        danger: "#dc2626",
        ink: "#0f172a",
        muted: "#64748b",
      },
      maxWidth: { app: "480px" },
      borderRadius: { xl2: "1.25rem" },
    },
  },
  plugins: [],
};
export default config;
