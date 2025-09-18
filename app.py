import yaml
from flask import Flask, jsonify, render_template
from pysnmp.hlapi import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    nextCmd,
    getCmd,
)




def build_status_summary(statuses):
    """
    Create a summary of device statuses counting online and offline devices.

    Parameters
    ----------
    statuses : list of dict
        List of device status dictionaries from build_statuses().

    Returns
    -------
    dict
        Dictionary with keys 'online' and 'offline' representing the counts.
    """
    summary = {'online': 0, 'offline': 0}
    for device in statuses:
        status = device.get('metrics', {}).get('status')
        if status == 'online':
            summary['online'] += 1
        else:
            summary['offline'] += 1
    return summary

def load_config(path: str = 'config.yaml'):
    """
    Load the YAML configuration file containing devices and alert settings.

    Parameters
    ----------
    path : str
        Path to the YAML configuration file. Defaults to 'config.yaml'.

    Returns
    -------
    dict
        Parsed configuration data.
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def snmp_get(community: str, ip: str, oid: str, port: int = 161, timeout: int = 1, retries: int = 1):
    """
    Perform a single SNMP GET request and return the value of the given OID.

    If the request fails due to timeout or other error, None is returned.

    Parameters
    ----------
    community : str
        SNMP community string.
    ip : str
        IP address or hostname of the target device.
    oid : str
        OID to retrieve.
    port : int, optional
        SNMP port, by default 161.
    timeout : int, optional
        Timeout in seconds, by default 1.
    retries : int, optional
        Number of retry attempts, by default 1.
    """
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((ip, port), timeout=timeout, retries=retries),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
    )
    if errorIndication or errorStatus:
        return None
    for varBind in varBinds:
        return varBind[1].prettyPrint()


def snmp_walk(community: str, ip: str, oid: str, port: int = 161, timeout: int = 1, retries: int = 1):
    """
    Perform an SNMP walk over an OID subtree.

    Returns a list of values. If the request fails, an empty list is returned.

    Parameters
    ----------
    community : str
        SNMP community string.
    ip : str
        IP address or hostname of the target device.
    oid : str
        Base OID to walk.
    port : int, optional
        SNMP port, by default 161.
    timeout : int, optional
        Timeout in seconds, by default 1.
    retries : int, optional
        Number of retry attempts, by default 1.
    """
    results = []
    for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((ip, port), timeout=timeout, retries=retries),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False,
    ):
        if errorIndication or errorStatus:
            break
        for varBind in varBinds:
            results.append(varBind[1])
    return results


def get_device_metrics(device: dict):
    """
    Collect metrics for a single device via SNMP.

    A device is expected to define at least an IP address and optionally
    `community` and `port` keys. Returns a dictionary containing the device
    status and metric values.

    If the device does not respond to a basic sysUpTime query, it is marked
    offline and no further OIDs are polled.

    Parameters
    ----------
    device : dict
        Configuration for a single device from config.yaml.

    Returns
    -------
    dict
        Dictionary of metric names to values.
    """
    ip = device.get('ip')
    community = device.get('community', 'public')
    port = device.get('port', 161)
    metrics = {}

    # Primary connectivity check using sysUpTime.0
    sys_up_time = snmp_get(community, ip, '1.3.6.1.2.1.1.3.0', port)
    if sys_up_time is None:
        metrics['status'] = 'offline'
        return metrics

    # Device responded; gather details
    sys_name = snmp_get(community, ip, '1.3.6.1.2.1.1.5.0', port)
    metrics['status'] = 'online'
    metrics['sysUpTime'] = sys_up_time
    metrics['sysName'] = sys_name

    # CPU load: average hrProcessorLoad values
    cpu_load_values = snmp_walk(community, ip, '1.3.6.1.2.1.25.3.3.1.2', port)
    if cpu_load_values:
        try:
            cpu_ints = [int(x) for x in cpu_load_values]
            metrics['cpuLoad'] = sum(cpu_ints) / len(cpu_ints)
        except ValueError:
            metrics['cpuLoad'] = None
    else:
        metrics['cpuLoad'] = None

    # Memory usage: approximate using hrStorageUsed/Size tables
    used_values = snmp_walk(community, ip, '1.3.6.1.2.1.25.2.3.1.6', port)
    size_values = snmp_walk(community, ip, '1.3.6.1.2.1.25.2.3.1.5', port)
    if used_values and size_values and len(used_values) == len(size_values):
        try:
            used_total = sum(int(u) for u in used_values)
            size_total = sum(int(s) for s in size_values)
            if size_total > 0:
                metrics['memoryUsage'] = used_total / size_total * 100.0
            else:
                metrics['memoryUsage'] = None
        except ValueError:
            metrics['memoryUsage'] = None
    else:
        metrics['memoryUsage'] = None

    # Interface statuses: compute ratio of interfaces that are 'up'
    if_statuses = snmp_walk(community, ip, '1.3.6.1.2.1.2.2.1.8', port)
    if if_statuses:
        try:
            statuses_int = [int(status) for status in if_statuses]
            up_count = sum(1 for s in statuses_int if s == 1)
            total = len(statuses_int)
            metrics['interfacesUp'] = up_count
            metrics['interfacesTotal'] = total
            metrics['interfacesUpPct'] = (up_count / total) * 100.0
        except ValueError:
            metrics['interfacesUp'] = None
            metrics['interfacesTotal'] = None
            metrics['interfacesUpPct'] = None
    else:
        metrics['interfacesUp'] = None
        metrics['interfacesTotal'] = None
        metrics['interfacesUpPct'] = None

    return metrics


def build_statuses():
    """Load configuration and return a list of device status dictionaries."""
    config = load_config()
    statuses = []
    for device in config.get('devices', []):
        metrics = get_device_metrics(device)
        statuses.append(
            {
                'name': device.get('name', device.get('ip')),
                'ip': device.get('ip'),
                'metrics': metrics,
            }
        )
    return statuses


app = Flask(__name__)


@app.route('/api/status')
def api_status():
    """Return JSON array of device statuses."""
    statuses = build_statuses()
    return jsonify(statuses)

@app.route('/api/summary')
def api_summary():
    """Return JSON summary of device statuses."""
    statuses = build_statuses()
    summary = build_status_summary(statuses)
    return jsonify(summary)



@app.route('/')
def index():
    """Render the HTML dashboard."""
    devices = build_statuses()
    return render_template('index.html', devices=devices)


if __name__ == '__main__':
    # Run a development web server. For production, use a proper WSGI server.
    app.run(host='0.0.0.0', port=8000)
