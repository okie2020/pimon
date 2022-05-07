#!/bin/sh
# For raspberry pi ubuntu or debian based systems

echo "update apt-get and install"
apt-get update
apt-get install -y git python3 python3-pip curl python3-apt

echo "Install requirements"

curl -o /tmp/requirements.txt https://raw.githubusercontent.com/okie2020/pimon/master/requirements.txt
pip3 install -r /tmp/requirements.txt
mkdir -p  /root/bin /root/.config/pimon
curl -o /root/bin/monitor.py https://raw.githubusercontent.com/okie2020/pimon/master/monitor.py
chmod 755 /root/bin/monitor.py

echo "[Unit]
Description=pimon service
After=multi-user.target

[Service]
User=root
Type=idle
ExecStart=/usr/bin/python3 /root/bin/monitor.py

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/pimon.service

systemctl daemon-reload
systemctl enable pimon
systemctl start pimon
systemctl status pimon
