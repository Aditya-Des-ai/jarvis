#!/bin/bash
# Turns Jarvis on, and keeps it on after every login.
#
# It starts three things:
#   1. the window watcher   (always running, notes what I'm doing)
#   2. the chat window      (always running, at http://localhost:8765)
#   3. the morning check-in (once a day; if the laptop was off, at next login)
#
# Run it:  bash schedule/turn_on.sh
# Undo it: bash schedule/turn_off.sh

set -e
project="$(cd "$(dirname "$0")/.." && pwd)"
units="$HOME/.config/systemd/user"
mkdir -p "$units" "$HOME/.local/share/applications"

read_setting() {
    (cd "$project" && python3 -c "from shared.settings import load_settings; print(load_settings()['$1'])")
}
checkin_time="$(read_setting morning_checkin_time)"
chat_port="$(read_setting chat_port)"
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

# A "Jarvis" entry in the apps menu that opens the chat window.
cat > "$HOME/.local/share/applications/jarvis.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=Talk to Jarvis
Exec=xdg-open http://localhost:$chat_port
Icon=user-available
Terminal=false
Categories=Utility;
EOF

systemctl --user daemon-reload
systemctl --user enable --now jarvis-watcher.service jarvis-chat.service jarvis-morning.timer

echo "Jarvis is on."
echo "  Chat window:      http://localhost:$chat_port  (or search 'Jarvis' in the apps menu)"
echo "  Morning check-in: every day at $checkin_time"
echo "  Check on it:      bash schedule/is_it_running.sh"
