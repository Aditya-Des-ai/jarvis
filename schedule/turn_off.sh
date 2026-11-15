#!/bin/bash
# Turns Jarvis off completely: stops the watcher, the chat window and the
# morning check-in, and stops them from starting at login.
#
# My data in private/ is left untouched.
#
# Run it:  bash schedule/turn_off.sh

units="$HOME/.config/systemd/user"

systemctl --user disable --now jarvis-watcher.service jarvis-chat.service jarvis-morning.timer 2>/dev/null
rm -f "$units"/jarvis-watcher.service "$units"/jarvis-chat.service \
      "$units"/jarvis-morning.service "$units"/jarvis-morning.timer \
      "$HOME/.local/share/applications/jarvis.desktop"
systemctl --user daemon-reload

echo "Jarvis is off. Nothing is being recorded. Your data in private/ is still there."
