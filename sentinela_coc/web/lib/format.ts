// Formato y mensajes amigables para el cliente final.

export function money(v?: number | null, currency = "MXN"): string {
  if (v == null) return "—";
  try {
    return new Intl.NumberFormat("es-MX", { style: "currency", currency }).format(v);
  } catch {
    return `$${v.toFixed(2)}`;
  }
}

export function formatDate(s?: string | null): string {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(+d)) return s;
  return new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

// Mensajes de error amigables (nunca exponer detalles técnicos al cliente).
export function friendlyError(e: unknown): string {
  const status = (e as { status?: number })?.status;
  if (status === 401) return "Tu sesión expiró. Inicia sesión de nuevo para continuar.";
  if (status === 404) return "No encontramos lo que buscabas.";
  if (status === 429) return "Demasiados intentos. Espera un momento e inténtalo de nuevo.";
  if (status === 502 || status === 503) return "Estamos teniendo problemas para conectar. Inténtalo en unos segundos.";
  if (e instanceof TypeError) return "Sin conexión. Revisa tu internet e inténtalo de nuevo.";
  return "Algo salió mal. Inténtalo de nuevo.";
}

// B1 (UAT): mensaje del paso de verificación de OTP según el error REAL del Gateway.
// No cambia la lógica ni el contrato: solo mapea el `error`/status a un texto correcto
// (antes se mostraba un texto fijo "código no válido" para todos los casos).
// "invalid" sigue cubriendo incorrecto/expirado (B2 queda diferido por decisión de producto).
export function authVerifyError(e: unknown): string {
  const err = e as { status?: number; code?: string };
  if (err?.code === "rate" || err?.status === 429)
    return "Demasiados intentos. Espera un momento e inténtalo de nuevo.";
  if (err?.code === "odoo_unavailable" || err?.status === 502 || err?.status === 503)
    return "Estamos teniendo problemas para conectar. Inténtalo en unos segundos.";
  if (e instanceof TypeError)
    return "Sin conexión. Revisa tu internet e inténtalo de nuevo.";
  return "El código no es válido o expiró. Revísalo e inténtalo de nuevo.";
}

const SERVICE_ICON: Record<string, string> = {
  internet: "🌐",
  alarm: "🛡️",
  gps: "📍",
  maintenance: "🔧",
  domain: "🌎",
};

export function serviceIcon(serviceType?: string): string {
  return (serviceType && SERVICE_ICON[serviceType]) || "•";
}

export function statusLabel(status?: string): string {
  switch (status) {
    case "active":
      return "Activo";
    case "suspended":
      return "Suspendido";
    case "pending_signature":
      return "Contrato por firmar";
    case "inactive":
      return "Inactivo";
    default:
      return status || "—";
  }
}
