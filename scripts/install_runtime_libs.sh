#!/usr/bin/env bash
# Extract Ubuntu shared libraries locally. Does not apt install or alter /usr.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$project_root/.cache/runtime-debs" "$project_root/.cache/runtime"
cd "$project_root/.cache/runtime-debs"
apt-get download libgl1=1.7.0-1build1 libglx0=1.7.0-1build1 \
  libglvnd0=1.7.0-1build1 libglib2.0-0t64=2.80.0-6ubuntu3.8
sha256sum --check "$project_root/requirements-runtime.sha256"
for package in libgl1_1.7.0-1build1_amd64.deb libglx0_1.7.0-1build1_amd64.deb \
  libglvnd0_1.7.0-1build1_amd64.deb libglib2.0-0t64_2.80.0-6ubuntu3.8_amd64.deb; do
  dpkg-deb -x "$package" "$project_root/.cache/runtime"
done
