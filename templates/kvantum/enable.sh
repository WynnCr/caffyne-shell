#!/bin/bash

# set kvantum theme to matugen
kvantummanager --set matugen

# qt5ct config
QT5CT_CONFIG="$HOME/.config/qt5ct/qt5ct.conf"
if [ -f "$QT5CT_CONFIG" ]; then
    # update style if already set to something
    sed -i 's/^style=.*/style=kvantum/' "$QT5CT_CONFIG"
else
    mkdir -p "$(dirname "$QT5CT_CONFIG")"
    cat > "$QT5CT_CONFIG" << EOF
[Appearance]
style=kvantum
EOF
fi

# qt6ct config
QT6CT_CONFIG="$HOME/.config/qt6ct/qt6ct.conf"
if [ -f "$QT6CT_CONFIG" ]; then
    sed -i 's/^style=.*/style=kvantum/' "$QT6CT_CONFIG"
else
    mkdir -p "$(dirname "$QT6CT_CONFIG")"
    cat > "$QT6CT_CONFIG" << EOF
[Appearance]
style=kvantum
EOF
fi

echo "Kvantum theme set to matugen, qt5ct and qt6ct configured"