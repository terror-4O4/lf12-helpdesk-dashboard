#!/bin/bash
# Richtet llama-server auf dem Mac Pro als Dienst (LaunchDaemon) ein.
#
# Der Dienst
#   - startet beim Hochfahren, ohne dass jemand angemeldet ist
#   - läuft als Standard-User "kiserver" (keine Adminrechte)
#   - läuft im Router-Modus: alle Modelle aus /opt/ki-projekt/models sind
#     verfügbar, das Backend wählt per LLAMA_MODEL, welches benutzt wird
#   - hält immer nur EIN Modell im VRAM (16 GB reichen nicht für mehrere)
#   - ist nur mit API-Key nutzbar und lauscht nur auf der LAN-IP
#   - startet nach einem Absturz automatisch neu
#
# Liegt ein Embedding-Modell in /opt/ki-projekt/models-embedding, richtet das
# Skript zusätzlich einen zweiten Dienst ein (de.lf12.llama-embed, Port 8081).
# Der rechnet auf der CPU die Vektoren für die Suche nach ähnlichen Tickets.
# Eigener Dienst, weil der Router-Modus nur ein Modell gleichzeitig hält und
# sonst bei jeder Suche das Chat-Modell aus dem VRAM werfen würde.
#
# Aufruf auf dem Mac Pro als Admin (nicht als kiserver):
#   sudo bash install-llama-dienst.sh             einrichten oder aktualisieren
#   sudo bash install-llama-dienst.sh --status    Zustand anzeigen
#   sudo bash install-llama-dienst.sh --entfernen Dienst entfernen (Modelle und Key bleiben)
#
# Anpassbar über Umgebungsvariablen, z. B.:
#   sudo LLAMA_HOST=192.168.2.160 STANDARD_MODELL=gemma-4-12b-it-qat-q4_0 bash install-llama-dienst.sh

set -euo pipefail

DIENST_USER="${DIENST_USER:-kiserver}"
BASIS="${BASIS:-/opt/ki-projekt}"
PORT="${LLAMA_PORT:-8080}"
STANDARD_MODELL="${STANDARD_MODELL:-gemma-4-26B-A4B-it-Q4_0}"
KONTEXT="${KONTEXT:-8192}"
EMBED_PORT="${EMBED_PORT:-8081}"

BIN="$BASIS/llama.cpp/build/bin/llama-server"
MODELLE="$BASIS/models"
CONFIG="$BASIS/config"
LOGS="$BASIS/logs"
KEY_DATEI="$CONFIG/api-key"
PRESET="$CONFIG/models.ini"
LOG_DATEI="$LOGS/llama-server.log"
LABEL="de.lf12.llama-server"
PLIST="/Library/LaunchDaemons/$LABEL.plist"
NEWSYSLOG="/etc/newsyslog.d/$LABEL.conf"

# Embedding-Dienst: Modell bewusst NICHT im Ordner models, sonst bietet der
# Router-Modus es als Chat-Modell an (und auswertung.py würde es testen)
EMBED_MODELLE="$BASIS/models-embedding"
EMBED_LABEL="de.lf12.llama-embed"
EMBED_PLIST="/Library/LaunchDaemons/$EMBED_LABEL.plist"
EMBED_LOG="$LOGS/llama-embed.log"
EMBED_NEWSYSLOG="/etc/newsyslog.d/$EMBED_LABEL.conf"

fehler() { echo "FEHLER: $*" >&2; exit 1; }
info()   { echo "==> $*"; }

[ "$(uname -s)" = "Darwin" ] || fehler "Dieses Skript ist nur für macOS gedacht."
[ "$(id -u)" -eq 0 ] || fehler "Bitte mit sudo starten: sudo bash $0"

# --- Status -----------------------------------------------------------------

zeige_status() {
    local host
    host="$(ipconfig getifaddr en0 2>/dev/null || true)"
    echo "Dienst:"
    if launchctl print "system/$LABEL" >/dev/null 2>&1; then
        launchctl print "system/$LABEL" | grep -E "^[[:space:]]+(state|pid|last exit code) =" || true
    else
        echo "  nicht eingerichtet"
    fi
    echo "Health:"
    curl -s --max-time 3 "http://${LLAMA_HOST:-$host}:$PORT/health" || echo "  nicht erreichbar"
    echo
    if [ -f "$KEY_DATEI" ]; then
        echo "Modelle:"
        curl -s --max-time 5 -H "Authorization: Bearer $(cat "$KEY_DATEI")" \
            "http://${LLAMA_HOST:-$host}:$PORT/models" \
            | /usr/bin/python3 -c 'import sys,json
for m in json.load(sys.stdin).get("data", []):
    print("  %-40s %s" % (m["id"], m.get("status", {}).get("value", "?")))' 2>/dev/null \
            || echo "  Liste nicht abrufbar"
    fi
    echo "Letzte Log-Zeilen ($LOG_DATEI):"
    tail -n 5 "$LOG_DATEI" 2>/dev/null || echo "  kein Log vorhanden"
    echo
    echo "Embedding-Dienst ($EMBED_LABEL):"
    if launchctl print "system/$EMBED_LABEL" >/dev/null 2>&1; then
        launchctl print "system/$EMBED_LABEL" | grep -E "^[[:space:]]+(state|pid|last exit code) =" || true
        echo -n "  Health: "
        curl -s --max-time 3 "http://${LLAMA_HOST:-$host}:$EMBED_PORT/health" || echo "nicht erreichbar"
        echo
    else
        echo "  nicht eingerichtet (kein Modell in $EMBED_MODELLE?)"
    fi
}

if [ "${1:-}" = "--status" ]; then
    zeige_status
    exit 0
fi

# --- Entfernen --------------------------------------------------------------

if [ "${1:-}" = "--entfernen" ]; then
    info "Stoppe und entferne den Dienst $LABEL"
    launchctl bootout "system/$LABEL" 2>/dev/null || true
    rm -f "$PLIST" "$NEWSYSLOG"
    info "Stoppe und entferne den Dienst $EMBED_LABEL"
    launchctl bootout "system/$EMBED_LABEL" 2>/dev/null || true
    rm -f "$EMBED_PLIST" "$EMBED_NEWSYSLOG"
    echo "Entfernt. Modelle, Konfiguration und API-Key in $BASIS bleiben erhalten."
    exit 0
fi

[ -z "${1:-}" ] || fehler "Unbekannte Option: $1 (erlaubt: --status, --entfernen)"

# --- Voraussetzungen prüfen ---------------------------------------------------

info "Prüfe Voraussetzungen"
id "$DIENST_USER" >/dev/null 2>&1 || fehler "User $DIENST_USER existiert nicht."
MITGLIED="$(dsmemberutil checkmembership -U "$DIENST_USER" -G admin 2>/dev/null || true)"
case "$MITGLIED" in
    *"is a member"*) fehler "$DIENST_USER hat Adminrechte. Der Dienst soll ohne Adminrechte laufen." ;;
esac
[ -x "$BIN" ] || fehler "llama-server nicht gefunden: $BIN (llama.cpp gebaut?)"
HILFE="$("$BIN" --help 2>&1 || true)"
case "$HILFE" in
    *--models-preset*) ;;
    *) fehler "Dieser llama-server kennt den Router-Modus nicht. llama.cpp aktualisieren und neu bauen." ;;
esac
[ -f "$MODELLE/$STANDARD_MODELL.gguf" ] || fehler "Standardmodell fehlt: $MODELLE/$STANDARD_MODELL.gguf"

LLAMA_HOST="${LLAMA_HOST:-$(ipconfig getifaddr en0 2>/dev/null || true)}"
[ -n "$LLAMA_HOST" ] || fehler "Keine LAN-IP auf en0 gefunden. Mit LLAMA_HOST=<IP> angeben."
case "$LLAMA_HOST" in
    10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*) ;;
    *) fehler "$LLAMA_HOST ist keine private Adresse. Der Dienst darf nur im lokalen Netz lauschen." ;;
esac

# Läuft noch ein von Hand gestarteter llama-server? Der belegt den Port.
if launchctl print "system/$LABEL" >/dev/null 2>&1; then
    info "Dienst ist bereits eingerichtet, wird aktualisiert"
    launchctl bootout "system/$LABEL" 2>/dev/null || true
    sleep 3
fi
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN
    fehler "Port $PORT ist belegt. Den von Hand gestarteten llama-server erst mit Ctrl+C beenden."
fi

# --- Ordner, API-Key, Modell-Voreinstellungen -----------------------------------

info "Lege Konfiguration in $CONFIG an"
mkdir -p "$CONFIG" "$LOGS" "$EMBED_MODELLE"
chown "$DIENST_USER":staff "$CONFIG" "$LOGS" "$EMBED_MODELLE"
chmod 750 "$CONFIG" "$LOGS" "$EMBED_MODELLE"

NEUER_KEY=0
if [ ! -s "$KEY_DATEI" ]; then
    # 32 Byte Zufall als Hex, nur kiserver darf die Datei lesen
    ( umask 077; openssl rand -hex 32 > "$KEY_DATEI" )
    NEUER_KEY=1
fi
chown "$DIENST_USER":staff "$KEY_DATEI"
chmod 600 "$KEY_DATEI"

# Einstellungen pro Modell. Der Abschnitt [*] gilt für alle Modelle.
# Wichtig: Diese Werte stehen bewusst NICHT auf der Kommandozeile des Dienstes,
# denn Kommandozeilen-Argumente würden die Werte pro Modell überschreiben.
cat > "$PRESET" <<EOF
version = 1

; Erzeugt von scripts/macpro/install-llama-dienst.sh, Änderungen werden beim
; nächsten Lauf überschrieben.

[*]
; alle Schichten auf die GPU (W5700X, Vulkan)
n-gpu-layers = 99
; Kontext für Ticket plus Kundendoku
c = $KONTEXT
; Denkmodus aus: 5- bis 8-mal schneller bei gleicher Qualität (Testprotokoll T10/T11)
reasoning-budget = 0

[$STANDARD_MODELL]
; beim Start des Dienstes sofort laden, damit die erste Anfrage nicht wartet
load-on-startup = true
EOF
# Abschnitte nur für vorhandene Modelle, sonst verlangt llama-server einen Pfad
if [ -f "$MODELLE/gpt-oss-20b-MXFP4.gguf" ]; then
    cat >> "$PRESET" <<EOF

[gpt-oss-20b-MXFP4]
; gpt-oss lässt sich nicht ganz abschalten, nur auf "low" stellen (T13)
reasoning-budget = -1
reasoning-effort = low
EOF
fi
chown "$DIENST_USER":staff "$PRESET"
chmod 640 "$PRESET"

# --- LaunchDaemon --------------------------------------------------------------

info "Schreibe $PLIST"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <!-- Läuft als kiserver, nicht als root -->
    <key>UserName</key>
    <string>$DIENST_USER</string>
    <key>GroupName</key>
    <string>staff</string>

    <key>ProgramArguments</key>
    <array>
        <string>$BIN</string>
        <string>--models-dir</string>
        <string>$MODELLE</string>
        <string>--models-preset</string>
        <string>$PRESET</string>
        <string>--models-max</string>
        <string>1</string>
        <string>--host</string>
        <string>$LLAMA_HOST</string>
        <string>--port</string>
        <string>$PORT</string>
        <string>--api-key-file</string>
        <string>$KEY_DATEI</string>
        <string>--no-webui</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$BASIS</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/$DIENST_USER</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <!-- Beim Hochfahren starten und nach Absturz neu starten (frühestens nach 30 s) -->
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <!-- Volle Leistung, macOS soll den Dienst nicht drosseln -->
    <key>ProcessType</key>
    <string>Interactive</string>

    <key>StandardOutPath</key>
    <string>$LOG_DATEI</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DATEI</string>
</dict>
</plist>
EOF
chown root:wheel "$PLIST"
chmod 644 "$PLIST"
plutil -lint "$PLIST" >/dev/null || fehler "plist ist ungültig: $PLIST"

# Log-Datei rotieren: ab 10 MB, 5 alte Dateien behalten
cat > "$NEWSYSLOG" <<EOF
# logfilename                 [owner:group]   mode count size(KB) when flags
$LOG_DATEI  $DIENST_USER:staff  640  5     10240    *    J
EOF

# --- Starten ----------------------------------------------------------------------

info "Starte Dienst"
touch "$LOG_DATEI"
chown "$DIENST_USER":staff "$LOG_DATEI"
chmod 640 "$LOG_DATEI"
launchctl bootstrap system "$PLIST"
launchctl enable "system/$LABEL"

info "Warte auf den Server (max. 30 s)"
for _ in $(seq 1 30); do
    curl -s --max-time 2 "http://$LLAMA_HOST:$PORT/health" >/dev/null 2>&1 && break
    sleep 1
done
curl -s --max-time 2 "http://$LLAMA_HOST:$PORT/health" >/dev/null 2>&1 \
    || fehler "Server antwortet nicht. Log prüfen: tail -n 50 $LOG_DATEI"

info "Warte, bis $STANDARD_MODELL geladen ist (max. 3 Min.)"
GELADEN=0
for _ in $(seq 1 90); do
    if curl -s --max-time 3 -H "Authorization: Bearer $(cat "$KEY_DATEI")" \
        "http://$LLAMA_HOST:$PORT/models" \
        | /usr/bin/python3 -c "import sys,json
d=json.load(sys.stdin).get('data',[])
sys.exit(0 if any(m['id']=='$STANDARD_MODELL' and m.get('status',{}).get('value')=='loaded' for m in d) else 1)" 2>/dev/null
    then
        GELADEN=1
        break
    fi
    sleep 2
done

# --- Embedding-Dienst (optional) ------------------------------------------------

richte_embedding_ein() {
    local modell="${EMBED_DATEI:-}"
    if [ -z "$modell" ]; then
        # genau eine .gguf-Datei im Ordner erwartet
        local anzahl
        anzahl="$(find "$EMBED_MODELLE" -maxdepth 1 -name '*.gguf' 2>/dev/null | wc -l | tr -d ' ')"
        if [ "$anzahl" = "0" ]; then
            echo "HINWEIS: Kein Embedding-Modell in $EMBED_MODELLE, Embedding-Dienst wird nicht eingerichtet."
            return 0
        fi
        [ "$anzahl" = "1" ] || fehler "Mehrere .gguf in $EMBED_MODELLE. Mit EMBED_DATEI=<Datei> angeben."
        modell="$(find "$EMBED_MODELLE" -maxdepth 1 -name '*.gguf')"
    fi
    [ -f "$modell" ] || fehler "Embedding-Modell nicht gefunden: $modell"

    info "Richte Embedding-Dienst ein ($(basename "$modell"), Port $EMBED_PORT, CPU)"
    if launchctl print "system/$EMBED_LABEL" >/dev/null 2>&1; then
        launchctl bootout "system/$EMBED_LABEL" 2>/dev/null || true
        sleep 2
    fi
    if lsof -nP -iTCP:"$EMBED_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        fehler "Port $EMBED_PORT ist belegt."
    fi

    cat > "$EMBED_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$EMBED_LABEL</string>
    <key>UserName</key>
    <string>$DIENST_USER</string>
    <key>GroupName</key>
    <string>staff</string>

    <!-- Nur Embeddings, auf der CPU (--device none), damit der VRAM dem Chat-Modell bleibt -->
    <key>ProgramArguments</key>
    <array>
        <string>$BIN</string>
        <string>-m</string>
        <string>$modell</string>
        <string>--embeddings</string>
        <string>--device</string>
        <string>none</string>
        <string>-ngl</string>
        <string>0</string>
        <string>-c</string>
        <string>2048</string>
        <string>-b</string>
        <string>2048</string>
        <string>-ub</string>
        <string>2048</string>
        <string>--host</string>
        <string>$LLAMA_HOST</string>
        <string>--port</string>
        <string>$EMBED_PORT</string>
        <string>--api-key-file</string>
        <string>$KEY_DATEI</string>
        <string>--no-webui</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$BASIS</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>StandardOutPath</key>
    <string>$EMBED_LOG</string>
    <key>StandardErrorPath</key>
    <string>$EMBED_LOG</string>
</dict>
</plist>
PLIST
    chown root:wheel "$EMBED_PLIST"
    chmod 644 "$EMBED_PLIST"
    plutil -lint "$EMBED_PLIST" >/dev/null || fehler "plist ist ungültig: $EMBED_PLIST"

    cat > "$EMBED_NEWSYSLOG" <<CONF
# logfilename                 [owner:group]   mode count size(KB) when flags
$EMBED_LOG  $DIENST_USER:staff  640  5     10240    *    J
CONF
    touch "$EMBED_LOG"
    chown "$DIENST_USER":staff "$EMBED_LOG"
    chmod 640 "$EMBED_LOG"

    launchctl bootstrap system "$EMBED_PLIST"
    launchctl enable "system/$EMBED_LABEL"

    info "Warte auf den Embedding-Server (max. 60 s)"
    for _ in $(seq 1 60); do
        curl -s --max-time 2 "http://$LLAMA_HOST:$EMBED_PORT/health" | grep -q '"ok"' && break
        sleep 1
    done
    # Probe: ein Vektor für einen Testsatz
    if curl -s --max-time 30 -H "Authorization: Bearer $(cat "$KEY_DATEI")" \
        -H "Content-Type: application/json" -d '{"input": ["Drucker druckt nicht"]}' \
        "http://$LLAMA_HOST:$EMBED_PORT/v1/embeddings" \
        | /usr/bin/python3 -c "import sys,json; v=json.load(sys.stdin)['data'][0]['embedding']; print('    Probe ok, Vektor mit', len(v), 'Zahlen')" 2>/dev/null
    then
        EMBED_OK=1
    else
        echo "WARNUNG: Embedding-Server liefert keinen Vektor. Log prüfen: tail -n 50 $EMBED_LOG"
    fi
}

EMBED_OK=0
richte_embedding_ein

echo
zeige_status
echo
if [ "$EMBED_OK" -eq 1 ]; then
    info "Embedding-Dienst läuft auf Port $EMBED_PORT."
fi
if [ "$GELADEN" -eq 1 ]; then
    info "Fertig. Der Dienst läuft und $STANDARD_MODELL ist geladen."
else
    echo "WARNUNG: $STANDARD_MODELL ist nach 3 Minuten noch nicht geladen. Log prüfen: tail -n 50 $LOG_DATEI"
fi
grep -m1 -E "Vulkan0|ggml_vulkan: 0 =" "$LOG_DATEI" >/dev/null 2>&1 \
    || echo "HINWEIS: Im Log ist (noch) keine Vulkan-GPU zu sehen. Prüfen mit: grep -i vulkan $LOG_DATEI"

cat <<EOF

Für die .env des Backends (MacBook bzw. später Mac Pro):

LLAMA_URL=http://$LLAMA_HOST:$PORT
LLAMA_MODEL=$STANDARD_MODELL
LLAMA_API_KEY=$(cat "$KEY_DATEI")
EMBED_URL=http://$LLAMA_HOST:$EMBED_PORT

EOF
if [ "$NEUER_KEY" -eq 1 ]; then
    echo "Der API-Key wurde neu erzeugt. Nur persönlich weitergeben, nie ins Repo oder in Trello."
else
    echo "Der bestehende API-Key wurde weiterverwendet."
fi
echo "Key später erneut anzeigen: sudo cat $KEY_DATEI"
