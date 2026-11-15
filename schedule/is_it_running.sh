#!/bin/bash
# Shows whether each part of Jarvis is running.
#
# Run it:  bash schedule/is_it_running.sh

project="$(cd "$(dirname "$0")/.." && pwd)"

show() {
    if systemctl --user is-active --quiet "$2"; then
        echo "  running   $1"
    else
        echo "  STOPPED   $1"
    fi
}

show "window watcher" jarvis-watcher.service
show "chat window" jarvis-chat.service
show "morning check-in timer" jarvis-morning.timer

next="$(systemctl --user show jarvis-morning.timer --property=NextElapseUSecRealtime --value 2>/dev/null)"
[ -n "$next" ] && echo "  next check-in: $next"

today="$project/private/records/windows/$(date +%F).jsonl"
if [ -f "$today" ]; then
    echo "  window notes today: $(wc -l < "$today")"
else
    echo "  window notes today: none yet"
fi
