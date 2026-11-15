#!/bin/bash
# Turns Jarvis off completely: stops the watcher, the chat window, the
# morning check-in and the local AI model, and stops them from starting at login.
#
# My data in private/ is left untouched.
# The jarvis command stays, so "jarvis on" brings everything back.
#
# Run it:  jarvis off

units="$HOME/.config/systemd/user"

systemctl --user disable --now jarvis-watcher.service jarvis-chat.service \
    jarvis-morning.timer jarvis-local-model.service 2>/dev/null
rm -f "$units"/jarvis-watcher.service "$units"/jarvis-chat.service \
      "$units"/jarvis-morning.service "$units"/jarvis-morning.timer \
      "$units"/jarvis-local-model.service \
      "$HOME/.local/share/applications/jarvis.desktop"
systemctl --user daemon-reload

echo "Jarvis is off. Nothing is being recorded. Your data in private/ is still there."
