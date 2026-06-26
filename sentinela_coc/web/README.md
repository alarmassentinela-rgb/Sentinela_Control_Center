# web — SPA del Portal COC (Next.js)

Frontend del Centro de Operaciones del Cliente. Consume **solo** el Gateway (`api.sentinela.mx`).

> Se inicializa en **Sprint 1** (shell de login OTP + `/v1/me` + `/v1/config/theme` como stretch del Sprint 0).

- Branding por `GET /v1/config/theme` (white-label sin rebuild — costura multiempresa).
- Mobile-first (residencial) + densidad alta (empresarial). PWA resiliente a mala conexión.
- Dominio: `portal.sentinela.mx` (Cloudflare/NPM).
- Base de wireframes: `WIREFRAMES_RESIDENCIAL_COC.md`, `WIREFRAMES_EMPRESARIAL_COC.md`.
