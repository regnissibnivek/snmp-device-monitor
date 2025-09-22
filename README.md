# SNMP Device Monitoring Mini‑App

This repository contains a lightweight SNMP monitoring tool built with Python and Flask. It polls a list of network devices via SNMP and presents their status and performance metrics in a simple web dashboard.

## Features

* **Device configuration via YAML:** Load a list of devices with IP address, friendly name and SNMP community from `config.yaml`.
* **SNMP polling:** The app uses the [`pysnmp`](https://pysnmp.readthedocs.io/) library to retrieve system uptime, CPU load, memory usage and interface status from each device.
* **Web dashboard:** A Flask‑based front end renders a responsive table with color‑coded status indicators showing which devices are online or offline.
* **Live controls:** Built-in search, filtering and manual refresh tools help you focus on the devices that matter while the dashboard auto-refreshes every 30 seconds.
* **Summary cards:** Aggregated tiles highlight online/offline counts plus average CPU, memory and interface availability at a glance.
* **JSON API:** The `/api/status` endpoint returns all collected metrics as a JSON array for programmatic consumption or integration with other tools.
* **Per-device JSON:** Query `/api/device/<device_id>` (IP address or device name) to poll a single device on demand.
* **Enhanced summary API:** `/api/summary` now reports online/offline percentages alongside average CPU, memory and interface health values.
* **Extensible:** Alert configuration is stubbed out in `config.yaml` so you can wire in email alerts or threshold checks.

## Getting started

### Prerequisites

* Python 3.8+
* `pip` for dependency installation

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/snmp-device-monitor.git
cd snmp-device-monitor
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Update `config.yaml` with your devices and SNMP community strings. Then run the application:

```bash
python app.py
```

Navigate to [`http://localhost:8000`](http://localhost:8000) in your browser to see the dashboard. The JSON API is available at [`http://localhost:8000/api/status`](http://localhost:8000/api/status).

## Configuration

The monitoring targets and alert settings are defined in `config.yaml`.

```yaml
devices:
  - name: Router1
    ip: 192.168.1.1
    community: public
    port: 161
  - name: Switch1
    ip: 192.168.1.2
    community: public
alerts:
  enabled: false
  email: you@example.com
  cpu_threshold: 80
```

* **name**: Friendly name shown in the dashboard.
* **ip**: IP address or hostname of the device.
* **community**: SNMP community string.
* **port**: SNMP port (optional, default is `161`).
* **alerts**: Stub configuration for implementing email alerts. This demo does not include an alerting backend.

## SNMP simulator

If you don’t have real SNMP‑enabled devices to test against, you can use [`snmpsim`](https://pysnmp.readthedocs.io/en/latest/snmpsim.html) to simulate them. After installing the simulator:

```bash
pip install snmpsim
snmpsim-command-responder --agent-udpv4-endpoint=127.0.0.1:16100 --data-dir=snmpsim-data
```

Then add a device to `config.yaml` with `ip: 127.0.0.1` and `port: 16100`.

## Screenshots

Once the application is running you can take screenshots and place them in the `images/` directory. Reference them in this README, for example:

```markdown
![Dashboard screenshot](images/dashboard.png)
```

## Contributing

Pull requests are welcome. Feel free to open issues for feature requests or bug reports.

## License

This project is licensed under the MIT license. See `LICENSE`

## Activity Log

This section tracks minor updates for repository activity purposes.

- Added activity log on September 18, 2025.
