#!/usr/bin/env bash
###############################################################################
# copy_to_usb.sh  —  Copia TODO el contexto a una USB de un jalón.
#   Corre en ESTA PC (DellCli/WSL).
#   Uso:   ./copy_to_usb.sh [/mnt/X]      (X = letra de la USB; si se omite, pregunta)
###############################################################################
set -uo pipefail

SRC_KEYS="$HOME/.ssh"
SRC_MEM="/home/egarza/.claude/projects/-mnt-c-Users-dell-DellCli/memory"
SRC_REPO="/mnt/c/Users/dell/DellCli"

echo "==============================================="
echo "  Copia de contexto Sentinela -> USB"
echo "==============================================="

# --- 1. Determinar la USB ---------------------------------------------------
USB="${1:-}"
if [[ -z "$USB" ]]; then
  echo "Discos montados (descarta C: que es el disco de Windows):"
  ls -d /mnt/*/ 2>/dev/null
  read -rp "Escribe la ruta de tu USB (ej. /mnt/d): " USB
fi
if [[ ! -d "$USB" ]]; then
  echo "ERROR: '$USB' no existe o no está montada. Conéctala y reintenta."
  exit 1
fi
if [[ ! -w "$USB" ]]; then
  echo "ERROR: no tengo permiso de escritura en '$USB'."
  exit 1
fi

DEST="$USB/sentinela_handoff"
mkdir -p "$DEST"/{llaves,memoria,repo_pcc,docs}
echo ">> Destino: $DEST"
echo

# --- 2. Llaves SSH (sensible) ----------------------------------------------
echo ">> Llaves SSH:"
for f in id_rsa_sentinela id_ed25519_github config; do
  if [[ -f "$SRC_KEYS/$f" ]]; then
    cp "$SRC_KEYS/$f" "$DEST/llaves/" && echo "   ✔ $f"
  else
    echo "   (no encontrada: $f)"
  fi
done
echo

# --- 3. Memoria de Claude (sensible) ---------------------------------------
echo ">> Memoria de Claude:"
if [[ -d "$SRC_MEM" ]]; then
  rm -rf "$DEST/memoria/memory"
  cp -r "$SRC_MEM" "$DEST/memoria/" && echo "   ✔ $(ls "$SRC_MEM" | wc -l) archivos de memoria"
else
  echo "   (no encontrada la carpeta de memoria)"
fi
echo

# --- 4. Scripts PCC + rollbacks + handoff ----------------------------------
echo ">> Scripts y rollbacks del PCC:"
cp -r "$SRC_REPO/pcc_madrugada" "$DEST/repo_pcc/" 2>/dev/null && echo "   ✔ pcc_madrugada/ (scripts + handoff)"
cp "$SRC_REPO"/ROLLBACK_*PCC*.py "$DEST/repo_pcc/" 2>/dev/null && echo "   ✔ ROLLBACK_*PCC*"
cp "$SRC_REPO"/ROLLBACK_*ARGUS*.py "$DEST/repo_pcc/" 2>/dev/null && echo "   ✔ ROLLBACK_*ARGUS*"
cp "$SRC_REPO"/failoverConfig_ORIGINAL*.rsc "$DEST/repo_pcc/" 2>/dev/null && echo "   ✔ failoverConfig_ORIGINAL"
cp "$SRC_REPO/pcc_madrugada/HANDOFF_PCC_MADRUGADA.md" "$DEST/docs/" 2>/dev/null && echo "   ✔ HANDOFF en docs/"
echo

# --- 5. Generar setup_laptop.sh (se corre EN LA LAPTOP) --------------------
cat > "$DEST/setup_laptop.sh" <<'LAPTOP'
#!/usr/bin/env bash
# Correr EN LA LAPTOP (WSL Ubuntu). Instala llaves + memoria desde esta USB.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
echo ">> Instalando llaves SSH..."
mkdir -p ~/.ssh
cp "$HERE"/llaves/* ~/.ssh/ 2>/dev/null && chmod 600 ~/.ssh/id_* 2>/dev/null && echo "   ✔ llaves en ~/.ssh"
echo ">> Instalando memoria de Claude..."
mkdir -p ~/.claude/projects/-mnt-c-Users-dell-DellCli/
rm -rf ~/.claude/projects/-mnt-c-Users-dell-DellCli/memory
cp -r "$HERE"/memoria/memory ~/.claude/projects/-mnt-c-Users-dell-DellCli/ 2>/dev/null && echo "   ✔ memoria instalada"
echo
echo ">> FALTA (hazlo a mano una vez):"
echo "   1) Node + Claude Code:  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs && npm install -g @anthropic-ai/claude-code"
echo "   2) Repo:                cd /mnt/c/Users/dell/ && git clone <tu-repo> DellCli   (o copia repo_pcc/ de la USB)"
echo "   3) Python:              pip install routeros_api"
echo
echo ">> Verificar red (desde casa, en la red por antenas):"
python3 -c "import socket;socket.create_connection(('192.168.10.254',8728),5);print('   Balanceador 192.168.10.254 ALCANZABLE ✔')" 2>/dev/null \
  || echo "   ✗ NO alcanzo el Balanceador. Revisa que estés en la red local."
echo
echo "Listo. Abre Claude en /mnt/c/Users/dell/DellCli y dile:"
echo "  'Lee pcc_madrugada/HANDOFF_PCC_MADRUGADA.md y continuemos el balanceo WISP.'"
LAPTOP
chmod +x "$DEST/setup_laptop.sh"
echo ">> Generado: setup_laptop.sh (córrelo en la laptop)"
echo

# --- 6. LEEME ---------------------------------------------------------------
cat > "$DEST/LEEME.txt" <<'README'
=== USB de traspaso Sentinela — balanceo PCC madrugada ===

CONTENIDO:
  llaves/      -> llaves SSH (server + GitHub) + config   [SENSIBLE]
  memoria/     -> memoria de Claude (todo el contexto)    [SENSIBLE]
  repo_pcc/    -> scripts del PCC, rollbacks, handoff
  docs/        -> HANDOFF_PCC_MADRUGADA.md
  setup_laptop.sh -> córrelo EN LA LAPTOP para instalar llaves+memoria

EN LA LAPTOP (WSL Ubuntu):
  1. Instala Claude Code:
       curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
       sudo apt install -y nodejs
       npm install -g @anthropic-ai/claude-code
  2. Trae el repo:   cd /mnt/c/Users/dell/ && git clone <tu-repo> DellCli
       (o copia repo_pcc/ de esta USB a esa carpeta)
  3. pip install routeros_api
  4. Corre desde la USB:   bash /mnt/<USB>/sentinela_handoff/setup_laptop.sh
  5. Verifica red:  python3 -c "import socket;socket.create_connection(('192.168.10.254',8728),5);print('OK')"
  6. Abre 'claude' en /mnt/c/Users/dell/DellCli y di:
       "Lee pcc_madrugada/HANDOFF_PCC_MADRUGADA.md y continuemos el balanceo WISP."

SEGURIDAD: guarda esta USB con cuidado (trae llaves y credenciales). No la pierdas.
README
echo ">> Generado: LEEME.txt"
echo

# --- 7. Resumen -------------------------------------------------------------
echo "==============================================="
echo "  ✅ COPIA COMPLETA"
echo "  Todo en: $DEST"
du -sh "$DEST" 2>/dev/null
echo "  En la laptop corre:  bash $DEST/setup_laptop.sh"
echo "==============================================="
