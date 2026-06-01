# GolfBookVIP — Guía del Organizador

> Para quien arma y dirige los torneos: el Pro del club, el organizador de la sociedad, o quien organiza el juego del sábado. Cubre crear rondas, formatos, jugadores, equipos, apuestas y resultados.
>
> ¿Eres jugador y solo vas a capturar tu score? Esa es la **Guía del Jugador**.

---

## 1. Crear una ronda

1. En tu panel, toca **Nueva ronda**.
2. Elige el **campo** y la **fecha/hora** de salida.
3. Elige el **formato de juego** (ver §2).
4. (Opcional) Define un **tope de handicap** (máximo de golpes que recibe cualquiera).
5. Guarda. La ronda queda en estado **Programada** y se genera un **código/link de invitación**.

Como creador eres el único que puede gestionar equipos, grupos, handicaps y apuestas.

---

## 2. Formatos de juego

| Formato | En una línea |
|---|---|
| **Stroke Play (Medal)** | Suma de todos los golpes; gana el menor total. Formato WHS oficial. |
| **Gran Premio** | Medal play por equipos con puntos por posición de grupo (ver §8). |
| **Stableford** | Puntos por hoyo según golpes vs par; gana el de más puntos. Los hoyos malos valen 0. |
| **Stableford Modificado** | Como Stableford pero penaliza más los hoyos malos y premia más los buenos. |
| **Match Play** | Hoyo a hoyo; gana el hoyo quien hace menos golpes. Resultado en diferencia de hoyos (3&2). |
| **Florida (Best Ball)** | Por equipos de 2–4. El score del equipo en cada hoyo es el **mejor neto** del equipo. |

> **Skins** ya no aparece como formato: es una **apuesta** (ver §10), porque se juega encima de cualquier formato.

Todos los formatos usan **score neto** = golpes brutos − golpes de ventaja del jugador (según su handicap de juego y el stroke index de cada hoyo).

---

## 3. Invitar y agregar jugadores

**Por link / QR (el jugador se une solo):**
- Comparte el **link de invitación** o el **QR**. El jugador entra, se registra o inicia sesión, y queda en la ronda.

**Agregar a mano (buscando):** útil si un jugador no puede confirmar por el link (p. ej. sin internet).
1. En la sección **Jugadores**, toca **➕ Agregar jugador**.
2. Busca por **nombre o usuario**.
3. Toca **Agregar** en el jugador correcto. Queda en la ronda al instante.

---

## 4. Ajustar el handicap de juego de un jugador

En la vida real hay jugadores que no llevan bien su handicap o usan otra app. Como organizador puedes **fijar a mano** los golpes con los que compite cada quien.

1. En **Jugadores**, junto al jugador, toca **✎ Hcp**.
2. Escribe el **handicap de juego** (golpes en esta ronda, 0–54) y Enter.

- Aplica solo a **esta ronda** (no toca el handicap index global del jugador).
- Si ya hay scores capturados, se **recalculan** con el nuevo handicap.

> **Nota — index vs. golpes:** el "handicap index" (ej. 12) es el número portátil del jugador; los "golpes de juego" (course handicap) son los que recibe **en ese campo** y pueden ser distintos (ej. 14 en un campo con slope alto). Con **✎ Hcp** fijas directamente los golpes acordados, sin preocuparte por la conversión.

---

## 5. Quitar un jugador (no se presentó)

1. En **Jugadores**, junto al jugador, toca la **✕** roja.
2. Confirma. Sale de la ronda (se borran sus scores y apuestas).

Disponible mientras la ronda esté **Programada** o **En juego**. Recomendación: arma equipos y grupos **después** del check-in, así los ausentes ya no están.

---

## 6. Equipos y grupos de salida

### Opción rápida — Auto-armar (recomendada para Gran Premio)

1. En **Equipos**, elige el **número de equipos**.
2. Toca **Auto-armar equipos + grupos (Medal Play)**.

Hace todo de un golpe: equipos **balanceados por handicap** + grupos de salida con **un jugador de cada equipo por grupo** (sin compañeros juntos) + publica. Los sobrantes caen en el último grupo.

### Manual

- **Equipos:** elige número de equipos → **Generar equipos** (los balancea por handicap) → mueve jugadores si quieres → **Publicar**.
- **Grupos de salida:** sección **Grupos de salida** → **Asignar grupos** → elige el **número de grupos** y asigna jugadores con los botones. Puedes dejar **grupos de distinto tamaño** (uno de 4 y otro de 5). Botones útiles: **Auto por hándicap** y **Shotgun start** (cada grupo arranca en su hoyo).

> El número de **grupos** define el tamaño: 20 jugadores ÷ 4 grupos = 5 por grupo. Para grupos de un jugador por equipo, usa # de grupos = jugadores ÷ # de equipos.

---

## 7. Formato Gran Premio (a detalle)

**Idea:** Medal play individual jugado **por equipos**. Cada grupo de salida mezcla un jugador de cada equipo; compiten entre sí y reparten puntos a su equipo según su **posición en neto**.

**Puntos por grupo:**
- 1.º lugar: **+2**
- 2.º lugar: **+1**
- Último lugar: **−1** (siempre, sin importar el tamaño del grupo)
- Los demás: **0**

En grupos de distinto tamaño:
- Grupo de 4 → +2 / +1 / 0 / −1 · Grupo de 3 → +2 / +1 / −1 · Grupo de 2 → +2 / −1

**Empates** dentro del grupo: se rompen por **tarjeta (countback)** en neto — últimos 9, 6, 3 hoyos, luego hoyo 18 y hacia atrás.

**Campeón por Equipos:** el equipo que **más puntos** acumule sumando a todos sus integrantes. Aparece automáticamente en la **vista en vivo**.

**Cómo armarlo:** usa **Auto-armar** (§6) — # de equipos = jugadores por grupo (foursomes → 4 equipos). Para que sea justo, usa un número de jugadores múltiplo del # de equipos (4 equipos → 16/20/24).

---

## 8. Captura de scores en grupo

- Cada **grupo de salida** tiene un **capturista** (puede ser único por grupo) que registra los scores de todos.
- Si dos personas distintas capturan un valor diferente para el mismo hoyo, el sistema marca un **conflicto** y pide resolverlo antes de poder finalizar.
- Cada jugador puede **firmar su tarjeta** al terminar.

Para resolver un conflicto: el jugador afectado o el creador entra al hoyo en conflicto y confirma el score correcto.

---

## 9. Apuestas

Las configuras al crear/editar la ronda (sección **Apuestas**). Se pueden combinar varias. Cada jugador puede **entrar o salir** de la apuesta.

| Apuesta | Cómo funciona |
|---|---|
| **Entrada (Entry Fee)** | Todos pagan un monto. El pot se reparte entre los 3 mejores **neto**: 60% / 30% / 10%. Empate al 1.º = split. |
| **Nassau** | Tres apuestas en una: Salida (1-9), Vuelta (10-18) y Total. En cada segmento el **low neto** se lleva todo el pot. |
| **Por hoyo ganado** | En cada hoyo, el **low neto** cobra el monto a los que perdieron. Empate = split. |
| **Premios (birdie/eagle/albatross/HIO)** | Cada vez que alguien lo hace, **cada otro jugador** le paga el premio. Se cuenta cada evento. |
| **Castigo de 3 putts** | Quien hace 3+ putts en un hoyo paga el monto a **cada otro jugador**. |
| **Skines (Skins)** | Gana una "piel" quien hace el low score (gross o net, según config) **sin empate**. Empate → se acumula (carry-over) al siguiente hoyo. |
| **Oyes** | Apuesta regional — **aún no calculada por el sistema** (reglas por confirmar). |

---

## 10. Pérdidas y ganancias (liquidación)

Al terminar (o en vivo), la sección de **balances** calcula quién gana y quién paga, sumando todas las apuestas activas.

- **Como creador, ves la tabla completa**: el balance de cada jugador y el Gran Total (cuánto cobra o paga cada quien).
- **Cada jugador ve solo lo suyo** (su monto), por privacidad.

Es el cierre de cuentas del "hoyo 19": le dices a cada quien cuánto cobra o cuánto pone.

---

## 11. Iniciar, seguir en vivo y finalizar

1. **Iniciar ronda:** cambia a **En juego** y habilita la captura.
2. **Seguir en vivo:** comparte el **link público** `golfbookvip.com/es/live/CÓDIGO` — cualquiera (sin cuenta) ve el marcador en tiempo real. En Gran Premio muestra el **Campeón por Equipos**; en Match los partidos; en Florida el best ball.
3. **Finalizar ronda:** cierra la captura, calcula resultados y **actualiza el handicap** de los jugadores. Se bloquea si hay **conflictos** o tarjetas incompletas (puedes forzar).

---

## Apéndice

**Glosario rápido**
- **Handicap Index:** el número portátil y oficial del jugador (WHS).
- **Course Handicap (golpes de juego):** los golpes que recibe en un campo específico = Index × (Slope/113) + (CR − Par).
- **Score neto:** golpes brutos − golpes de ventaja recibidos.
- **Stroke Index:** dificultad relativa de cada hoyo (1 = el más difícil); define en qué hoyos se reciben los golpes.
- **Diferencial:** qué tan bien jugaste una ronda vs la dificultad del campo; base del cálculo del handicap.

**Estadísticas y mi handicap:** son **personales del jugador** y viven en su **Perfil** (tendencia de handicap, GIR, putts, "¿cómo se calcula mi handicap?"). Ver la **Guía del Jugador**.
