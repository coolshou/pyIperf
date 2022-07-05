# -*- coding: utf-8 -*-


DEFAULT_IPERF3_PORT = 5201
DEFAULT_IPERF2_PORT = 5001

IPERFprotocal = {
    'TCP': 0,  # TCP
    'UDP': 1,   # UDP
}


IPERFUNIT = {}
IPERFUNIT["bits"] = 0  # b
IPERFUNIT["Kbits"] = 1  # kb
IPERFUNIT["Mbits"] = 2  # mb
IPERFUNIT["Gbits"] = 3  # gb
IPERFUNIT["Tbits"] = 4  # tb
IPERFUNIT["Pbits"] = 5  # pb
IPERFUNIT["Ebits"] = 6  # eb
IPERFUNIT["Zbits"] = 7  # zb
IPERFUNIT["Ybits"] = 8  # yb

IPERFUNIT["Bytes"] = 10  # B
IPERFUNIT["KBytes"] = 11  # KB
IPERFUNIT["MBytes"] = 12  # MB
IPERFUNIT["GBytes"] = 13  # GB
IPERFUNIT["TBytes"] = 14  # TB
IPERFUNIT["PBytes"] = 15  # PB
IPERFUNIT["EBytes"] = 16  # EB
IPERFUNIT["ZBytes"] = 17  # ZB
IPERFUNIT["YBytes"] = 18  # YB