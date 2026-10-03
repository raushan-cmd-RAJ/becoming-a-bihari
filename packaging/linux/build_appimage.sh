#!/usr/bin/env bash
# ==============================================================================
# Vihara - Linux x86_64 Standalone AppImage Build Pipeline
# Builds: dist/Vihara-x86_64.AppImage
# ==============================================================================
set -euo pipefail

APP_NAME="Vihara"
DIST_DIR="dist"
APPDIR="${DIST_DIR}/AppDir"
OUTPUT_APPIMAGE="${DIST_DIR}/Vihara-x86_64.AppImage"

echo "=== 1. Building PyInstaller onedir Distribution for Linux ==="
pyinstaller --clean -y packaging/windows/vihara.spec

echo "=== 2. Creating AppDir Filesystem Structure ==="
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

# Copy binary payload
cp -r "${DIST_DIR}/vihara/"* "${APPDIR}/usr/bin/"

# Copy desktop entry and icons
cp packaging/linux/vihara.desktop "${APPDIR}/"
cp packaging/linux/vihara.desktop "${APPDIR}/usr/share/applications/"
if [ -f "packaging/icons/app_icon.png" ]; then
    cp packaging/icons/app_icon.png "${APPDIR}/vihara.png"
    cp packaging/icons/app_icon.png "${APPDIR}/usr/share/icons/hicolor/256x256/apps/vihara.png"
fi

# Create standard AppRun entrypoint
cat << 'EOF' > "${APPDIR}/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH:-}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
exec "${HERE}/usr/bin/vihara" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

echo "=== 3. Packaging Standalone AppImage with appimagetool ==="
if command -v appimagetool &> /dev/null; then
    ARCH=x86_64 appimagetool "${APPDIR}" "${OUTPUT_APPIMAGE}"
    echo "Linux AppImage successfully generated: ${OUTPUT_APPIMAGE}"
else
    echo "Notice: appimagetool not found on PATH. AppDir structure is prepared at: ${APPDIR}"
fi
