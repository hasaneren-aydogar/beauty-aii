#!/usr/bin/env bash
# Fetch HairFastGAN code + pretrained weights into ai-models/. Requires git, python, NVIDIA GPU for inference.
set -euo pipefail
cd "$(dirname "$0")/../ai-models"
[ -d HairFastGAN ] || git clone https://github.com/AIRI-Institute/HairFastGAN.git
cd HairFastGAN
pip install -r requirements.txt
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(repo_id="AIRI-Institute/HairFastGAN", local_dir="pretrained_models")
PY
echo "Done. Set AI_BACKEND=hairfast in .env. Check upstream README if file layout differs."
