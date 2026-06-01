# GolfBookVIP — Organizer Guide

> For whoever sets up and runs the tournaments: the club Pro, the society organizer, or whoever organizes the Saturday game. Covers creating rounds, formats, players, teams, bets and results.
>
> Are you a player who just needs to enter scores? That's the **Player Guide**.

---

## 1. Create a round

1. On your dashboard, tap **New round**.
2. Pick the **course** and the **tee date/time**.
3. Pick the **game format** (see §2).
4. (Optional) Set a **handicap cap** (max strokes anyone can receive).
5. Save. The round becomes **Scheduled** and an **invite code/link** is generated.

As the creator you're the only one who can manage teams, groups, handicaps and bets.

---

## 2. Game formats

| Format | In one line |
|---|---|
| **Stroke Play (Medal)** | Total of all strokes; lowest total wins. Official WHS format. |
| **Gran Premio** | Team medal play with points by group position (see §8). |
| **Stableford** | Points per hole based on strokes vs par; most points wins. Bad holes score 0. |
| **Modified Stableford** | Like Stableford but penalizes bad holes more and rewards great ones more. |
| **Match Play** | Hole by hole; win the hole with fewer strokes. Result as hole difference (3&2). |
| **Florida (Best Ball)** | Teams of 2–4. The team's hole score is the team's **best net**. |

> **Skins** is no longer a format: it's a **bet** (see §10), since it's played on top of any format.

Every format uses **net score** = gross strokes − the player's handicap strokes (based on their playing handicap and each hole's stroke index).

---

## 3. Invite and add players

**By link / QR (player joins on their own):**
- Share the **invite link** or **QR**. The player opens it, registers or logs in, and joins the round.

**Add manually (by search):** useful when a player can't confirm via the link (e.g. no internet).
1. In the **Players** section, tap **➕ Add player**.
2. Search by **name or username**.
3. Tap **Add** on the right player. They join instantly.

---

## 4. Adjust a player's playing handicap

In real life some players don't keep their handicap properly or use another app. As organizer you can **manually set** the strokes each one competes with.

1. In **Players**, next to the player, tap **✎ Hcp**.
2. Type the **playing handicap** (strokes this round, 0–54) and Enter.

- Applies only to **this round** (does not touch the player's global handicap index).
- If scores are already entered, they are **recalculated** with the new handicap.

> **Note — index vs. strokes:** the "handicap index" (e.g. 12) is the player's portable number; the "playing strokes" (course handicap) are what they get **on that course** and may differ (e.g. 14 on a high-slope course). With **✎ Hcp** you set the agreed strokes directly, no conversion worries.

---

## 5. Remove a player (no-show)

1. In **Players**, next to the player, tap the red **✕**.
2. Confirm. They leave the round (their scores and bets are deleted).

Available while the round is **Scheduled** or **In play**. Tip: build teams and groups **after** check-in, so no-shows are already gone.

---

## 6. Teams and tee groups

### Quick option — Auto-build (recommended for Gran Premio)

1. In **Teams**, choose the **number of teams**.
2. Tap **Auto-build teams + groups (Medal Play)**.

It does everything at once: **handicap-balanced** teams + tee groups with **one player from each team per group** (no teammates together) + publishes. Leftovers go in the last group.

### Manual

- **Teams:** choose the number of teams → **Generate teams** (balanced by handicap) → move players if you want → **Publish**.
- **Tee groups:** **Tee groups** section → **Assign groups** → choose the **number of groups** and assign players with the buttons. You can leave **different-sized groups** (one of 4 and one of 5). Handy buttons: **Auto by handicap** and **Shotgun start** (each group starts at its own hole).

> The number of **groups** sets the size: 20 players ÷ 4 groups = 5 per group. For one-player-per-team groups, use # of groups = players ÷ # of teams.

---

## 7. Gran Premio format (in detail)

**Idea:** individual medal play played **as teams**. Each tee group mixes one player from each team; they compete against each other and award points to their team based on their **net position**.

**Points per group:**
- 1st place: **+2**
- 2nd place: **+1**
- Last place: **−1** (always, regardless of group size)
- The rest: **0**

For different group sizes:
- Group of 4 → +2 / +1 / 0 / −1 · Group of 3 → +2 / +1 / −1 · Group of 2 → +2 / −1

**Ties** within a group are broken by **scorecard countback** in net — last 9, 6, 3 holes, then hole 18 and backwards.

**Team Champion:** the team with the **most points** summing all its members. Shows automatically in the **live view**.

**How to set it up:** use **Auto-build** (§6) — # of teams = players per group (foursomes → 4 teams). For fairness, use a number of players that's a multiple of the # of teams (4 teams → 16/20/24).

---

## 8. Group score capture

- Each **tee group** has a **scorer** (can be a single one per group) who records everyone's scores.
- If two different people enter a different value for the same hole, the system flags a **conflict** that must be resolved before finishing.
- Each player can **sign their card** when done.

To resolve a conflict: the affected player or the creator opens the conflicted hole and confirms the correct score.

---

## 9. Bets

Set them up when creating/editing the round (**Bets** section). Several can be combined. Each player can **opt in or out**.

| Bet | How it works |
|---|---|
| **Entry Fee** | Everyone pays an amount. The pot is split among the top 3 **net**: 60% / 30% / 10%. Tie for 1st = split. |
| **Nassau** | Three bets in one: Front (1-9), Back (10-18) and Total. In each segment the **low net** takes the whole pot. |
| **Per hole won** | On each hole, the **low net** collects the amount from those who lost. Tie = split. |
| **Prizes (birdie/eagle/albatross/HIO)** | Each time someone makes one, **every other player** pays them the prize. Each event counts. |
| **3-putt penalty** | Whoever 3-putts a hole pays the amount to **every other player**. |
| **Skins** | A "skin" is won by the outright low score (gross or net, per config) **with no tie**. Tie → carries over to the next hole. |
| **Oyes** | Regional bet — **not yet computed by the system** (rules to be confirmed). |

---

## 10. Profit and loss (settlement)

When the round ends (or live), the **balances** section computes who wins and who pays, summing all active bets.

- **As the creator, you see the full table**: each player's balance and the Grand Total (how much each one collects or pays).
- **Each player sees only their own** amount, for privacy.

It's the "19th hole" settlement: you tell everyone how much they collect or chip in.

---

## 11. Start, follow live and finish

1. **Start round:** switches to **In play** and enables capture.
2. **Follow live:** share the **public link** `golfbookvip.com/en/live/CODE` — anyone (no account) sees the live scoreboard. In Gran Premio it shows the **Team Champion**; in Match the matchups; in Florida the best ball.
3. **Finish round:** closes capture, computes results and **updates players' handicaps**. It's blocked if there are **conflicts** or incomplete cards (you can force it).

---

## Appendix

**Quick glossary**
- **Handicap Index:** the player's portable, official number (WHS).
- **Course Handicap (playing strokes):** strokes received on a specific course = Index × (Slope/113) + (CR − Par).
- **Net score:** gross strokes − handicap strokes received.
- **Stroke Index:** each hole's relative difficulty (1 = hardest); defines which holes get strokes.
- **Differential:** how well you played a round vs the course difficulty; the basis of the handicap calculation.

**Statistics and my handicap:** these are **personal to the player** and live in their **Profile** (handicap trend, GIR, putts, "how is my handicap calculated?"). See the **Player Guide**.
