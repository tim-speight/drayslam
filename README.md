# DraySLAM — VDSL EPICS IOC

A lightweight EPICS PVAccess IOC that exposes VDSL line metrics from a
Draytek Vigor 160 modem. Designed for use with Phoebus and the EPICS
Archiver Appliance to provide long-term DSLAM stability diagnostics.

## Features

- Scrapes DSL metrics from the modem's HTML status page
- Polls WAN throughput via SNMP
- Publishes metrics as EPICS PVAccess PVs using `p4p`
- Compatible with Phoebus for live displays
- Archiver-ready PV schema for long-term trending
- Runs as a systemd service on a Raspberry Pi 4

## Service runner
sudo systemctl daemon-reload
sudo systemctl enable vdsl-ioc
sudo systemctl start vdsl-ioc

## Repository Structure
ioc ui archiver tools

## Setup

### 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### 2. Run IOC manually
python3 vdsl_ioc.py

### 3. Install as systemd service (Pi4)

See `docs/deployment.md` for full instructions.

## PV Schema

See `docs/pv_reference.md` for the full list of PVs and metadata.

## License
BSD-3 - to be compliant with EPICS
