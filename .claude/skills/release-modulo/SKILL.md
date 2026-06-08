---
name: release-modulo
description: >-
  Corta un release de un módulo sentinela_* (o golfbookvip / aleasystem.io):
  sube la versión en __manifest__.py, hace commit con la convención del repo,
  crea el tag de respaldo y pushea a GitHub. Úsalo cuando terminaste cambios de
  código y quieres versionar + respaldar. NO despliega al server — para eso usa
  después la skill deploy-modulo.
---

# Cortar un release de módulo

Cada release tagueado = punto de restauración (`git checkout <tag>`). El tag en
GitHub ES el respaldo del código (por eso el ADDONS tar.gz del server es temporal).

## 1. Decidir el bump de versión
Versión en `<modulo>/__manifest__.py`, formato **`18.0.1.X.Y`**:
- Bug fix / ajuste menor → sube el último dígito (`...3.82` → `...3.83`).
- Feature nueva → sube el penúltimo, reinicia el último (`...3.82` → `...4.0`).
- (golfbookvip/aleasystem usan `vMAJOR.MINOR.PATCH`, ej. `1.23.0`.)

Editar la línea `'version': '...'` del manifest al nuevo número.

## 2. Commit con la convención del repo
Formato real del historial:
```
<tipo>(<scope>): <descripción en español> (v18.0.1.X.Y)
```
- **tipo**: `feat` (nueva funcionalidad), `fix` (corrección), `docs` (documentación),
  `tools` (scripts/utilidades), `refactor`.
- **scope**: el área corta — `subscriptions`, `monitoring`, `cfdi`, `fsm`, `pcc`, etc.
- La versión entre paréntesis al final (solo para cambios de código de módulo).

Ejemplos reales:
```
feat(subscriptions): botón 'Validar Navegación' — diagnóstico REAL de internet (v18.0.1.3.81)
fix(subscriptions): candado anti-duplicado en facturación (v18.0.1.3.82)
feat(cfdi): titulo dinamico REMISION/FACTURA + fix logo desbordado (v18.0.1.1.2)
```

```bash
git add <modulo>/
git commit -m "<tipo>(<scope>): <desc> (v18.0.1.X.Y)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

## 3. Tag de respaldo
Convención: **`vX.Y.Z-<modulo>`** (la versión del manifest + nombre del módulo):
```bash
git tag v18.0.1.X.Y-<modulo>
```
Ej: `v18.0.1.3.83-sentinela_subscriptions`.

## 4. Push (autorizado, sin confirmar)
Enrique autoriza push directo a `main`. Reglas: avisar qué se sube, sin secretos,
**sin force-push a main**.
```bash
git push origin main && git push origin v18.0.1.X.Y-<modulo>
```

## 5. Reportar
Decir qué versión quedó, el hash del commit y el tag pusheado. Si el cambio debe
llegar a producción, recordar que falta desplegar → encadenar con **deploy-modulo**
(el código en GitHub NO es lo que corre el server hasta el rsync + `-u`).

## Salvaguardas
- No commitear secretos (llaves, passwords, tokens) — revisar el diff antes.
- No `--force` a `main`.
- La versión del commit/tag debe coincidir EXACTAMENTE con la del manifest.
- Solo el módulo tocado en el `git add` — no arrastrar cambios no relacionados.
