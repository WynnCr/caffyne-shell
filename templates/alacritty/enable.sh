#!/bin/bash

ALACRITTY_CONFIG="$HOME/.config/alacritty/alacritty.toml"
IMPORT_LINE='import = ["~/.config/alacritty/colors.toml"]'

# create config if it doesn't exist
if [ ! -f "$ALACRITTY_CONFIG" ]; then
    mkdir -p "$(dirname "$ALACRITTY_CONFIG")"
    echo "$IMPORT_LINE" > "$ALACRITTY_CONFIG"
    echo "Created $ALACRITTY_CONFIG with import line"
    exit 0
fi

# check if import line is already present
if grep -qF 'colors.toml' "$ALACRITTY_CONFIG"; then
    echo "Import already present, skipping"
    exit 0
fi

# prepend to the top of the file so it's picked up first
echo -e "$IMPORT_LINE\n$(cat "$ALACRITTY_CONFIG")" > "$ALACRITTY_CONFIG"
echo "Added import line to $ALACRITTY_CONFIG"