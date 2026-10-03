#!/usr/bin/env bash
# ==============================================================================
# Vihara - macOS Universal 2 DMG Build, Signing, and Notarization Pipeline
# Builds: dist/Vihara-Universal.dmg
# ==============================================================================
set -euo pipefail

APP_NAME="Vihara"
BUNDLE_DIR="dist/${APP_NAME}.app"
DMG_NAME="dist/Vihara-Universal.dmg"

echo "=== 1. Building Universal 2 PyInstaller Bundle ==="
pyinstaller --clean -y packaging/windows/vihara.spec

echo "=== 2. Signing Embedded Frameworks and dylibs ==="
if [ -d "${BUNDLE_DIR}/Contents/Frameworks" ]; then
    find "${BUNDLE_DIR}/Contents/Frameworks" -type f \( -name "*.dylib" -o -name "*.so" \) | while read -r lib; do
        if [ -n "${APPLE_DEV_CERTIFICATE:-}" ]; then
            codesign --force --timestamp --options runtime \
                --sign "${APPLE_DEV_CERTIFICATE}" "$lib"
        else
            codesign --force -s - "$lib"
        fi
    done
fi

echo "=== 3. Deep Signing Application Bundle with Hardened Runtime ==="
if [ -n "${APPLE_DEV_CERTIFICATE:-}" ]; then
    codesign --force --timestamp --options runtime --deep \
        --entitlements packaging/mac/entitlements.plist \
        --sign "${APPLE_DEV_CERTIFICATE}" \
        "${BUNDLE_DIR}"
else
    echo "APPLE_DEV_CERTIFICATE not set; performing ad-hoc signature for local testing."
    codesign --force --deep -s - "${BUNDLE_DIR}"
fi

echo "=== 4. Assembling Drag-and-Drop DMG ==="
if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "${APP_NAME}" \
        --window-pos 200 120 \
        --window-size 660 400 \
        --icon-size 128 \
        --app-drop-link 480 180 \
        --icon "${APP_NAME}.app" 180 180 \
        --hide-extension "${APP_NAME}.app" \
        "${DMG_NAME}" \
        "${BUNDLE_DIR}" || true
else
    echo "create-dmg not found; using hdiutil fallback."
    hdiutil create -volname "${APP_NAME}" -srcfolder "${BUNDLE_DIR}" -ov -format UDZO "${DMG_NAME}"
fi

echo "=== 5. Submitting DMG to Apple Notary Service ==="
if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ] && [ -n "${APPLE_APP_SPECIFIC_PASSWORD:-}" ]; then
    xcrun notarytool submit "${DMG_NAME}" \
        --apple-id "${APPLE_ID}" \
        --team-id "${APPLE_TEAM_ID}" \
        --password "${APPLE_APP_SPECIFIC_PASSWORD}" \
        --wait

    echo "=== 6. Stapling Notarization Ticket to DMG ==="
    xcrun stapler staple "${DMG_NAME}"

    echo "=== 7. Verifying Gatekeeper Assessment ==="
    spctl --assess --type open --context context:primary-signature "${DMG_NAME}"
    echo "Vihara macOS DMG notarized and ready for zero-friction distribution."
else
    echo "Skipping Apple Notary submission (credentials not configured)."
fi

echo "macOS build completed: ${DMG_NAME}"
