# Technical Packaging & Architecture Deliverables

This directory contains the production-grade packaging, installer, auto-updater, and theme/meme pack architecture specifications for Vihara ("Becoming a Bihari").

## Contents
1. `standalone_installer_and_autoupdate_architecture.md`: Multi-platform single-click zero-friction installer specs, PyInstaller onedir binary builds, AI model decoupling, atomic background auto-updater with rollback, and low-footprint background system tray integration.
2. `meme_pack_specification.md`: `.lucidpack` package format, asset folder structure, lifecycle loader, hot-reloading file watcher, and validation rules.
3. `meme_pack_schema.json`: Formal JSON Schema (Draft-07) validating pack manifests.
4. `sample_pack/`: Reference pack implementation adhering strictly to schema.
