import type { Config } from "tailwindcss";

// ── Design Tokens (ÚNICA fuente de verdad de la capa visual) ──────────────────
// Colores de marca via CSS vars -> white-label sin rebuild. El resto espeja los
// valores vigentes del Sprint 1 (no cambia el diseño): radios, sombras, z, tipografía.
// Regla: si existe un token, se usa el token (no hardcodear color/radio/sombra/spacing).
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
        surface: "#ffffff",
      },
      // Escala tipográfica única. Mínimo absoluto = 12px (caption). Nada por debajo.
      fontSize: {
        caption: ["0.75rem", { lineHeight: "1rem" }], // 12px
        aux: ["0.875rem", { lineHeight: "1.25rem" }], // 14px
        body: ["1rem", { lineHeight: "1.5rem" }], // 16px
        subtitle: ["1.125rem", { lineHeight: "1.5rem" }], // 18px
        title: ["1.25rem", { lineHeight: "1.75rem" }], // 20px
        hero: ["1.875rem", { lineHeight: "2.25rem" }], // 30px
      },
      maxWidth: { app: "480px", desktop: "1520px" },
      borderRadius: {
        xl2: "1.25rem", // compat
        pill: "9999px",
        control: "0.75rem", // botones, inputs
        card: "1.25rem", // tarjetas, diálogos
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        overlay: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
      },
      zIndex: { nav: "10", header: "20", overlay: "30", modal: "40" },
      transitionDuration: { base: "150ms" },
    },
  },
  plugins: [],
};
export default config;
