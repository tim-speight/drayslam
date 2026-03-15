import time
import threading
from p4p.server import Server
from pvschema import PV_DEFS
from parser import fetch_html, parse_html, snmp_get

def update_loop():
    while True:
        try:
            html = fetch_html()
            stats = parse_html(html)

            PV_DEFS["NET:VDSL:LINE:DOWN_SNR"].value = stats["down_snr"]
            PV_DEFS["NET:VDSL:LINE:UP_SNR"].value = stats["up_snr"]
            PV_DEFS["NET:VDSL:LINE:DOWN_RATE"].value = stats["down_rate"]
            PV_DEFS["NET:VDSL:LINE:UP_RATE"].value = stats["up_rate"]
            PV_DEFS["NET:VDSL:LINE:CRC_DOWN"].value = stats["crc_down"]
            PV_DEFS["NET:VDSL:LINE:CRC_UP"].value = stats["crc_up"]
            PV_DEFS["NET:VDSL:LINE:ES"].value = stats["es"]
            PV_DEFS["NET:VDSL:LINE:SES"].value = stats["ses"]
            PV_DEFS["NET:VDSL:LINE:STATE"].value = stats["state"]
            PV_DEFS["NET:VDSL:LINE:UPTIME_SEC"].value = stats["uptime_sec"]

            # SNMP throughput
            PV_DEFS["NET:VDSL:WAN:IN_OCTETS"].value = snmp_get("1.3.6.1.2.1.31.1.1.1.6.2")
            PV_DEFS["NET:VDSL:WAN:OUT_OCTETS"].value = snmp_get("1.3.6.1.2.1.31.1.1.1.10.2")

        except Exception as e:
            print("Update error:", e)

        time.sleep(5)

def main():
    t = threading.Thread(target=update_loop, daemon=True)
    t.start()
    with Server(providers=[PV_DEFS]):
        print("VDSL IOC running")
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()

