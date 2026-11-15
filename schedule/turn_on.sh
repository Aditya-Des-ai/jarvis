#!/bin/bash
# Turns Jarvis on, and keeps it on after every login.
#
# It starts these things:
#   1. the window watcher   (always running, notes what I'm doing)
#   2. the chat window      (always running)
#   3. the morning check-in (once a day; if the laptop was off, at next login)
#   4. the local AI model   (only if it was downloaded with schedule/get_local_model.sh)
#
# It also adds the short "jarvis" command, so from then on:
#   jarvis        opens the chat window
#   jarvis off    turns everything off
#
# Run it:  bash schedule/turn_on.sh

set -e
project="$(cd "$(dirname "$0")/.." && pwd)"
units="$HOME/.config/systemd/user"
local_model="$HOME/.local/share/ollama-app/bin/ollama"
mkdir -p "$units" "$HOME/.local/share/applications" "$HOME/.local/bin"

read_setting() {
    (cd "$project" && python3 -c "from shared.settings import load_settings; print(load_settings()['$1'])")
}
checkin_time="$(read_setting morning_checkin_time)"
programs="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

cat > "$units/jarvis-watcher.service" <<EOF
[Unit]
Description=Jarvis: notes which window I'm using
PartOf=graphical-session.target
After=graphical-session.target

[Service]
WorkingDirectory=$project
ExecStart=/usr/bin/python3 -m watchers.window_watcher
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target
EOF

cat > "$units/jarvis-chat.service" <<EOF
[Unit]
Description=Jarvis: the chat window
PartOf=graphical-session.target
After=graphical-session.target

[Service]
WorkingDirectory=$project
Environment=$programs
ExecStart=/usr/bin/python3 -m chat.chat_window
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target
EOF

cat > "$units/jarvis-morning.service" <<EOF
[Unit]
Description=Jarvis: the morning check-in

[Service]
Type=oneshot
WorkingDirectory=$project
Environment=$programs
# Give the laptop a minute to connect to the internet after waking up.
ExecStartPre=/bin/sleep 60
ExecStart=/usr/bin/python3 -m brain.morning_checkin
EOF

cat > "$units/jarvis-morning.timer" <<EOF
[Unit]
Description=Jarvis: runs the morning check-in once a day

[Timer]
OnCalendar=*-*-* $checkin_time:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

parts="jarvis-watcher.service jarvis-chat.service jarvis-morning.timer"

# The local AI model, if it has been downloaded.
if [ -x "$local_model" ]; then
    cat > "$units/jarvis-local-model.service" <<EOF
[Unit]
Description=Jarvis: the AI model that runs on this laptop

[Service]
# Only this laptop can reach it.
Environment=OLLAMA_HOST=127.0.0.1:11434
ExecStart=$local_model serve
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
    parts="$parts jarvis-local-model.service"
fi

# A "Jarvis" entry in the apps menu that opens the chat window.
cat > "$HOME/.local/share/applications/jarvis.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=Talk to Jarvis
Exec=$project/jarvis
Icon=user-available
Terminal=false
Categories=Utility;
EOF

# The short command: "jarvis" from any terminal.
ln -sf "$project/jarvis" "$HOME/.local/bin/jarvis"

systemctl --user daemon-reload
systemctl --user enable $parts
systemctl --user restart $parts

echo "Jarvis is on."
echo "  Open the chat:    jarvis"
echo "  Morning check-in: every day at $checkin_time"
echo "  Everything else:  jarvis help"
[ -x "$local_model" ] || echo "  Local AI model:   not downloaded (optional: bash schedule/get_local_model.sh)"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "  Note: open a new terminal for the jarvis command to work." ;;
esac
