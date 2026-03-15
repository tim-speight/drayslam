import requests
from bs4 import BeautifulSoup
from pysnmp.hlapi import *

MODEM_URL = "http://192.168.2.1/cgi-bin/status_dsl.asp"
AUTH = ("admin", "password")

def fetch_html():
    r = requests.get(MODEM_URL, auth=AUTH, timeout=5)
    r.raise_for_status()
    return r.text

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    # TODO: extract real values from your modem’s HTML
    return {
        "down_snr": 6.5,
        "up_snr": 7.2,
        "down_rate": 79999,
        "up_rate": 19999,
        "crc_down": 12,
        "crc_up": 0,
        "es": 1,
        "ses": 0,
        "state": "SHOWTIME",
        "uptime_sec": 123456,
    }

def snmp_get(oid, host="192.168.2.1", community="public"):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((host, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )
    error, status, index, varbinds = next(iterator)
    if error or status:
        return None
    return float(varbinds[0][1])

