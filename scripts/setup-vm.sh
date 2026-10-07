#!/usr/bin/env bash
set -euo pipefail

cp2_bucket=${1:?Usage: bash setup-vm.sh BUCKET_NAME}
cp2_user=$(id -un)
cp2_home=$(getent passwd "$cp2_user" | cut -d: -f6)

if [ ! -f "$cp2_home/src/serve.py" ]; then
  echo 'Copy src/serve.py to the VM before running setup.' >&2
  exit 1
fi
sudo apt-get -o Acquire::ForceIPv4=true -o Acquire::Languages=none \
  -o Acquire::http::Pipeline-Depth=0 -o Acquire::http::Timeout=30 update
sudo apt-get install -y python3-venv python3-pip curl
python3 -m venv "$cp2_home/income-venv"
"$cp2_home/income-venv/bin/python" -m pip install \
  fastapi==0.111.0 uvicorn==0.29.0 scikit-learn==1.4.2 \
  numpy==1.26.4 pandas==2.2.2 joblib==1.4.2 google-cloud-storage==2.16.0
mkdir -p "$cp2_home/models"

sudo tee /etc/systemd/system/income-api.service > /dev/null <<EOF
[Unit]
Description=Income Model Inference Server
After=network-online.target
Wants=network-online.target

[Service]
User=$cp2_user
WorkingDirectory=$cp2_home
Environment="ARTIFACT_BUCKET=$cp2_bucket"
ExecStart=$cp2_home/income-venv/bin/python $cp2_home/src/serve.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable income-api
echo 'VM configured. The Release job will start the API after publishing a model.'
