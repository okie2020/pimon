#!/bin/sh

declare -i install=1
declare -i update=0
declare -i remove=0

if [[ $(id -u) -ne 0 ]]; then
  echo "This script must be executed as root or using sudo."
  exit 99
fi
systemd="$(ps --no-headers -o comm 1)"
if [ ! "${systemd}" = "systemd" ]; then
  echo "This system is not running systemd.  Exiting..."
  exit 100
fi

while getopts ":hur:" option; do
   case $option in
      h) # display Help
         echo "Pimon Install Script."
         echo
         echo "Syntax: pimon.sh -[h|r|u]"
         echo "options:"
         echo "h     Print this help."
         echo "r     Remove pimon and dependancies."
         echo "u     Update pimon to newest version."
         echo
         exit;;
      u) # Run update
         update=1
         install=0
         ;;
      r) # Remove
         remove=1
         install=0
         ;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

if [ ${remove} -eq 0 ] && [ ${update} -eq 0 ] && [ ${install} -eq 1 ] then  # Install
  DEB_PACKAGE_NAME="git curl python3 python3-pip python3-apt"
  if cat /etc/*release | grep ^NAME | grep Ubuntu; then
    echo "==============================================="
    echo               "Installing packages"
    echo "==============================================="
    apt-get update
    apt-get install -y $DEB_PACKAGE_NAME
  elif cat /etc/*release | grep ^NAME | grep Debian ; then
    echo "==============================================="
    echo               "Installing packages"
    echo "==============================================="
    apt-get update
    apt-get install -y $DEB_PACKAGE_NAME
  else
    echo "OS NOT SUPPORTED, check Github for supported OS"
    exit 1
  fi
  echo "==============================================="
  echo               "Installing Pimon"
  echo "==============================================="
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
  KillSignal=SIGINT
  ExecStart=/usr/bin/python3 /root/bin/monitor.py

  [Install]
  WantedBy=multi-user.target" > /etc/systemd/system/pimon.service
  systemctl daemon-reload
  systemctl enable pimon
  systemctl start pimon
fi

if [ ${remove} -eq 1 ] && [ ${update} -eq 0 ] && [ ${install} -eq 0 ] then  # Remove
  systemctl stop pimon
  systemctl remove pimon
  rm /etc/systemd/system/pimon.service
  rm /root/bin/monitor.py
  rm -rf /root/.config/pimon
  curl -o /tmp/requirements.txt https://raw.githubusercontent.com/okie2020/pimon/master/requirements.txt
  pip uninstall -r /tmp/requirements.txt -y
fi

if [ ${remove} -eq 0 ] && [ ${update} -eq 1 ] && [ ${install} -eq 0 ] then  # Update
  curl -o /tmp/requirements.txt https://raw.githubusercontent.com/okie2020/pimon/master/requirements.txt
  pip install -r /tmp/requirements.txt -y
  curl -o /root/bin/monitor.py https://raw.githubusercontent.com/okie2020/pimon/master/monitor.py
  chmod 755 /root/bin/monitor.py
  fi
exit 0


