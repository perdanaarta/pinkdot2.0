#!/usr/bin/bash

home="$(dirname "$0")/.."

sudo apt install ffmpeg -y

source $home/.env
python="python$PYTHON_VERSION"

mkdir $home/.venv
$python -m venv $home/.venv
source $home/.venv/bin/activate
pip install -r $home/requirements.txt

write_service_file () {
  appname=$1
  
  # Install Systemd Service
  sudo cat > /etc/systemd/system/$appname.service << EOF

[Unit]
Description=$appname discord bot
After=network.target

[Service]
ExecStart=/usr/bin/bash /opt/$appname/scripts/run.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target  
EOF
  
  sudo systemctl daemon-reload 
  sudo systemctl enable $appname.service
  sudo systemctl start $appname.service
}

write_service_file pinkdot








