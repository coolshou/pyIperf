# -*- coding: utf-8 -*-

import traceback
import time
import re
import os
try:
    from PyQt5.QtCore import QObject, QThread
except ImportError as err:
    traceback.print_tb(err.__traceback__)
    raise SystemExit("pip install \n %s" % err)
    
from iperfcomm import IPERFprotocal

class IperfParser(QObject):
    '''class to parser iperf output'''

    def __init__(self, lines=[], iperfver=3, parent=None):
        # datas: lines of iperf output
        super(IperfParser, self).__init__(parent)
        self._DEBUG = 5
        self.iperfver = iperfver
        self.tID = '%s' % int(QThread.currentThreadId())
        if len(lines)>0:
            self.load(lines)
        
        # store result
        self._result = {}  # store final in dict format
        self._resultunit = ""  # store final sum unit
        self._detail = []  # store every line of data

    def load(self, lines):
        for line in lines:
            line = line.rstrip("\n")
            if len(line)>0:
                print("line:%s" % line)
                # record
                self._detail.append(line)

    def _handel_dataline(self, tID, line):
        '''handle data output from iperf'''
        curDirection = "Tx"
        detail = line.strip()
        if len(detail) > 0:
            # recore every line except empty line
            if detail=="\r":
                # do not record line contain only \r
                pass
            else:
                self._detail.append(detail)
        if ("[" in line) and ("]" in line):
            # this suould be data we care
            if "local" in line:
                # record header data
                # print("HEADER: %s" % (line))
                self.log("HEADER: %s" % line, 4)
            elif "Interval" in line:
                # ignore header line
                time.sleep(0.5)
            else:
                # --parallel index
                # may be "SUM" or num
                iPalls = line[1:4].split()
                if type(iPalls) == list:
                    iPall = iPalls[0]
                # print("iPall: %s (%s)" % (iPall, type(iPall)))

                # result data = remove parallel index [xxx], [SUM]
                data = line[5:].strip()
                if self.iperfver == 2:
                    # iperf2: determine Tx or Rx
                    if "port 5001" in data:
                        idx = data.index("port 5001")
                        if idx > 50:
                            # should be Tx
                            curDirection = "Tx"
                        else:
                            # should be Rx
                            curDirection = "Rx"
                elif self.iperfver == 3:
                    # TODO: iperf3 : curDirection is wrong!!
                    if "Reverse mode" in data:
                        curDirection = "Rx"
                    if data.count("[") == 1:
                        # --bidir
                        if "RX" in data:
                            curDirection = "Rx"
                        if "TX" in data:
                            curDirection = "Tx"
                ndata = "%s %s" % (curDirection, data)
                if "SUM" != iPall:
                    # just notice result when iperf is running for later User
                    # eg: throughput chart
                    self.signal_result.emit(tID, int(iPall), ndata)
                if self._parallel > 1:
                    # TODO: handle each pair of data
                    if "SUM" == iPall:
                        # only procress data when --parallel > 1
                        pass
                    else:
                        return

                if self.iperfver == 3:
                    self._parser_dataline3(iPall, tID, data)
                elif self.iperfver == 2:
                    # TODO: error data:
                    # [SUM]  0.0-30.1 sec  0.00 (null)s  198999509338 Bytes/sec
                    self._parser_dataline2(iPall, tID, ndata)
                else:
                    self.log( "TODO(iperf v%s)line: %s" % (self.iperfver, line))
        elif ("failed" in line) or ("error" in line):
            # something wrong!
            eMsg = "error handle: %s" % line
            self.log(eMsg)
            self.signal_finished.emit(0, eMsg)
            self.do_stop()
        else:
            self.log("IGNORE: %s" % (line))
            pass

    def _parser_dataline2(self, iPall, tID, data):
        '''parser iperf v2 throughput'''
        # TCP
        #  99.0-100.0 sec  7.52 GBytes  64.6 Gbits/sec
        #   0.0-100.0 sec   839 GBytes  72.0 Gbits/sec
        # UDP
        #  0.0-100.0 sec  12.5 MBytes  1.05 Mbits/sec
        # ds = re.findall(r"[-+]?\d*\.\d+|\d+", data)  # float & int with sign
        # self.log(tID, "_parser_dataline2: %s" % (data))
        ds = re.findall(r"\d*\.\d+|\d+", data)  # float & int

        if len(ds) >= 4:
            self._result[iPall] = round(float(ds[3]), 2)
            try:
                startT = float(ds[0])
                endT = float(ds[1])
            except ValueError as err:
                self.log(tID, "_parser_dataline2 ERROR: %s" % err)
                return -1
            if (int(startT) == 0) and (self._duration == int(endT)):
                # final result
                if self._tradeoff:
                    if "Tx" in data:
                        # idx = data.index("Tx")
                        iPall = "%s%s" % (iPall, "Tx")
                    if "Rx" in data:
                        # idx = data.index("Rx")
                        iPall = "%s%s" % (iPall, "Rx")
                    #
                self._result[iPall] = round(float(ds[2]), 2)
                self.log(tID, "_result[%s]:%s" % (iPall, self._result[iPall]))
                time.sleep(3)
                if self._tradeoff:
                    self._tradeoffCount = self._tradeoffCount + 1
                    if self._tradeoffCount >= 2:
                        self.do_stop()
                else:
                    self.do_stop()
        else:
            self.log(tID, "unknown format:%s" % data)
            self.sig_data.emit(tID, iPall, data)

    def _parser_dataline3(self, iPall, tID, data):
        '''parser iperf v3 throughput'''
        self.log(tID, "_parser_dataline3: %s" % (data))
        if "(omitted)" in data:
            pass
        elif "sender" in data:
            pass
        elif "receiver" in data:
            if data.count("[") == 1:
                # --bidir mode
                # [TX-C]   0.00-10.26  sec  73.7 MBytes  60.3 Mbits/sec                  receiver
                key = data[1:3]
                ds = re.findall(r"[-+]?\d*\.\d+|\d+", data)  # float & int
                self._result["%s" % key] = round(float(ds[3]), 2)
            else:
                # Tx or Rx only
                #    0.00-10.00  sec   101 MBytes  85.1 Mbits/sec                  receiver
                ds = re.findall(r"[-+]?\d*\.\d+|\d+", data)  # float & int
                self._result[iPall] = round(float(ds[3]), 2)
                if self._tcp == IPERFprotocal.get("UDP"):
                    # TODO --bidir
                    print("UDP ds: %s (%s)" % (ds, data))
                    try:
                        self._lost = int(ds[5])
                        self._total = int(ds[6])
                        self._per = round(float(ds[7]), 5)
                    except Exception as err:
                        self.log(tID, "ERROR: %s" % err)
        else:
            # every line of data
            self.sig_data.emit(tID, iPall, data)

    
    def log(self, msg, level=1):
        # msg : message to log
        # level : debug level
        if self._DEBUG > level:
            # print("Iperf log: (%s) %s" % (mType, msg))
            msg = "(%s) %s" % (self.__class__.__name__, msg)
            # self.signal_debug.emit(self.__class__.__name__, msg)
            print(msg)