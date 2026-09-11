#!/usr/bin/env bash
# Refresh the vendored copy of brink-flair-modbus from a sibling checkout.
#
# The integration ships the library inside itself so it installs from HACS
# with no PyPI package to wait on. This script is the only supported way to
# update that copy: edit the library in its own repository, run its tests
# there, then run this.
set -euo pipefail

source=${1:-../brink-flair-modbus}
target="$(dirname "$0")/../custom_components/brink_flair/brink_flair_modbus"

if [ ! -d "$source/src/brink_flair_modbus" ]; then
    echo "No library checkout at $source" >&2
    exit 1
fi

rm -rf "$target"
cp -R "$source/src/brink_flair_modbus" "$target"
find "$target" -name __pycache__ -type d -exec rm -rf {} +
echo "Vendored $(git -C "$source" rev-parse --short HEAD 2>/dev/null || echo 'unknown') into $target"
