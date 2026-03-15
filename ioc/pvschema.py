from p4p.nt import NTScalar

PV_DEFS = {
    "NET:VDSL:LINE:DOWN_SNR":   NTScalar("d").wrap(0.0),
    "NET:VDSL:LINE:UP_SNR":     NTScalar("d").wrap(0.0),
    "NET:VDSL:LINE:DOWN_RATE":  NTScalar("d").wrap(0.0),
    "NET:VDSL:LINE:UP_RATE":    NTScalar("d").wrap(0.0),
    "NET:VDSL:LINE:CRC_DOWN":   NTScalar("i").wrap(0),
    "NET:VDSL:LINE:CRC_UP":     NTScalar("i").wrap(0),
    "NET:VDSL:LINE:ES":         NTScalar("i").wrap(0),
    "NET:VDSL:LINE:SES":        NTScalar("i").wrap(0),
    "NET:VDSL:LINE:STATE":      NTScalar("s").wrap("UNKNOWN"),
    "NET:VDSL:LINE:UPTIME_SEC": NTScalar("i").wrap(0),
    "NET:VDSL:WAN:IN_OCTETS":   NTScalar("d").wrap(0.0),
    "NET:VDSL:WAN:OUT_OCTETS":  NTScalar("d").wrap(0.0),
}

