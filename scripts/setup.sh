#!/usr/bin/bash
 
set -e

home="$(dirname "$0")/.."
source $home/.env
python=python$PYTHON_VERSION

mkdir $home/.venv
$python -m venv $home/.venv

source $home/.venv/bin/activate
pip install -r $home/requirements.txt

sudo apt install ffmpeg -y

app="pinkdot"

# Install Systemd Service
sudo cat > /etc/systemd/system/$app.service << EOF
[Unit]
Description=$app discord bot
After=network.target

[Service]
ExecStart=/usr/bin/bash $home/scripts/run.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload 
sudo systemctl enable $app.service # remove the extension
sudo systemctl start $app.service