import type { Metadata, Viewport } from "next";

import "./globals.css";

export const metadata: Metadata = {
  // Metadatos del DOCUMENTO (pestaña del navegador / SEO), no UI visual. La identidad
  // VISIBLE del portal vive únicamente en <BrandMark> (logo de Odoo + título). Estos son
  // estáticos por requerirse en SSR antes de cargar el theme; alinear con el branding actual.
  title: "Sentinela — Portal del Cliente",
  description: "Portal del Cliente de Sentinela.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#0B5FFF",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
