#!/bin/bash
# Downloads an AI model that runs on this laptop, with no internet needed
# afterwards. Optional. Jarvis uses it to sort apps and websites that no rule
# recognises, and it can be the whole brain (brain = "local" in settings.toml).
#
# It downloads about 4 GB into my home folder: the Ollama program (1.5 GB)
# and the model itself. No administrator password is needed.
#
# Run it:  bash schedule/get_local_model.sh     then:  jarvis on

set -e
project="$(cd "$(dirname "$0")/.." && pwd)"
home_of_ollama="$HOME/.local/share/ollama-app"
model="$(cd "$project" && python3 -c "from shared.settings import load_settings; print(load_settings()['local_model'])")"

if [ ! -x "$home_of_ollama/bin/ollama" ]; then
    echo "Downloading Ollama (1.5 GB)..."
    mkdir -p "$home_of_ollama"
    curl -L --fail --progress-bar https://ollama.com/download/ollama-linux-amd64.tar.zst \
        -o "$home_of_ollama/ollama.tar.zst"
    tar --zstd -xf "$home_of_ollama/ollama.tar.zst" -C "$home_of_ollama"
    rm "$home_of_ollama/ollama.tar.zst"
fi

# Start it just for the download if it is not already running.
started_here=""
if ! curl -s -o /dev/null --max-time 2 http://127.0.0.1:11434/api/version; then
    OLLAMA_HOST=127.0.0.1:11434 "$home_of_ollama/bin/ollama" serve >/dev/null 2>&1 &
    started_here=$!
    sleep 4
fi

echo "Downloading the model $model..."
"$home_of_ollama/bin/ollama" pull "$model"

[ -n "$started_here" ] && kill "$started_here"
echo "Done. Run 'jarvis on' so the local model starts with everything else."
