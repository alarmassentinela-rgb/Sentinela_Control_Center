# ADR-0008 — Contraseñas Argon2; biometría del lado del dispositivo

**Estado:** Aceptada (26-jun-2026)

## Contexto
Se requieren contraseñas robustas y soporte biométrico, sin que el gateway gestione datos biométricos.

## Decisión
- Contraseñas con **Argon2** (passlib) + política (longitud/letras+dígitos/no repetitiva); recuperación por OTP; cambio con verificación de la actual.
- **Biometría = responsabilidad del dispositivo/navegador** (Face ID/huella/WebAuthn local). El gateway solo administra identidad y sesiones (emite/valida tokens).

## Consecuencias
- (+) Sin almacenamiento ni transmisión de datos biométricos en el backend.
- (+) Estándar de hashing fuerte.
- (−) La experiencia biométrica depende del cliente (app/navegador).
