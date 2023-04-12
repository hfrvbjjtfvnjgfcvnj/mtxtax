#!/bin/bash

DIR="$(dirname "${0}")"
cd "${DIR}"

USER="$(whoami)"
if [ 'root' != "${USER}" ] ;
then
	echo "ERROR: setup.sh must be run as root."
	exit 1
fi

USER=mtxtax
if id ${USER};
then
	echo "Warning: '${USER}' user exists. Not creating a new one."
else
	useradd -r -s /bin/false ${USER}
	usermod -a -G dialout ${USER}
	echo "Created user: '${USER}'"
fi

INST_DIR="/opt/mtxtax"
echo "Installing to ${INST_DIR}"
if [ -d "${INST_DIR}" ] ;
then
	echo "Warning: '${INST_DIR}' already exists. This should be OK, but make note incase somethings breaks."
fi
mkdir -p ${INST_DIR}
chown -R ${USER} ${INST_DIR}

echo "Installing Python3 requirements..."
if [ -e "${INST_DIR}/venv" ] ;
then
	rm -rfv "${INST_DIR}/venv"
fi
python3 -m venv ${INST_DIR}/venv
source ${INST_DIR}/venv/bin/activate
${INST_DIR}/venv/bin/pip install --upgrade pip
${INST_DIR}/venv/bin/pip3 install -r requirements.txt

cp mtxtax *.py *.sh *.xml ${INST_DIR}/
if [ -f ${INST_DIR}/config.json ] ;
then
	echo "Warning: Config file '${INST_DIR}/config.json' already exists. Not installing a new one"
else
	cp config.example.json ${INST_DIR}/config.json
fi
chown -R ${USER} ${INST_DIR}

cp mtxtax.service /lib/systemd/system/
systemctl daemon-reload
systemctl enable mtxtax.service

echo "NOTE: Update ${INST_DIR}/config.json prior to starting crows_nest service."

