#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python --version
python scripts/prepare_cloudflare_assets.py --check-source

venv=$(mktemp -d)
trap 'rm -rf -- "$venv"' EXIT
python -m venv "$venv"
"$venv/bin/python" -m pip install -r requirements-blog.txt
"$venv/bin/python" scripts/build_blog.py
"$venv/bin/python" -m unittest discover -s tests
"$venv/bin/python" scripts/prepare_cloudflare_assets.py
