#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 13:45:15 2017

@author: jimmy

    subprocrss base iperf3 python class

"""

import time
import sys
import traceback
# import datetime
import subprocess
import os
import platform
# import logging
import psutil
import ast
# import zlib
import re

try:
    from PyQt5.QtCore import (QCoreApplication, QThread, QEventLoop,
                              pyqtSlot, pyqtSignal, QObject)
    # from PyQt5.QtWidgets import (QApplication)
except ImportError as err:
    raise SystemExit("pip install PyQt5\n %s" % err)

basedir = os.path.join(os.getcwd(), os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, "..", "..", "pyWAT"))
from nbstreamreader import NonBlockingStreamReader as NBSR

from iperfcomm import IPERFprotocal, DEFAULT_IPERF3_PORT, DEFAULT_IPERF2_PORT


def kill(proc_pid):
    '''kill procress id'''
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

# LOCKER = QMutex()
LOCKER = None

class Iperf(QObject):
    '''manager class to control iperf2/iperf3 running'''
    __VERSION__ = '20201123'

    # thread id, iParallel, data
    signal_result = pyqtSignal(int, int, str)
    signal_finished = pyqtSignal(int, str)
    signal_error = pyqtSignal(str, str)
    signal_debug = pyqtSignal(str, str)  # class, msg

    # thread id, --parallel num, iperf live data output
    sig_data = pyqtSignal(int, str, str)

    default_port = DEFAULT_IPERF3_PORT

    def __init__(self, port=DEFAULT_IPERF3_PORT, iperfver=3, parent=None):
        super(Iperf, self).__init__(parent)
        self._DEBUG = 3
        if getattr(sys, 'frozen', False):
            # we are running in a |PyInstaller| bundle
            self._basedir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            self._basedir = os.path.dirname(__file__)
        # iperf binary
        if platform.machine() in ['i386', 'i486', 'i586', 'i686']:
            arch = 'x86'
        else:
            arch = platform.machine()
        self.iperfver = iperfver
        if self.iperfver == 3:
            iperfname = "iperf3"
        else:
            iperfname = "iperf"

        self.iperf = os.path.join(self._basedir, 'bin', platform.system())
        if platform.system() == 'Linux':
            self.iperf = os.path.join(self.iperf, arch, '%s' % iperfname)
        elif platform.system() == 'Windows':
            self.iperf = os.path.join(self.iperf, arch, '%s.exe' % iperfname)
        else:
            self.log("WARNING", "Not support platform :%s" % platform.system())

        self.port = port
        self._tcp = IPERFprotocal.get("TCP")  # 0: TCP, 1: UDP,...

        self.stoped = False  # user stop
        self.sCmd = []

        self._parallel = 1  # for report result use
        self._duration = 0  # -t N sec
        # iperf2 -r, --tradeoff Do a bidirectional test individually
        self._tradeoff = False
        self._tradeoffCount = 0
        self._bidir = False
        # store result
        self._result = {}  # store final in dict format
        self._resultunit = ""  # store final sum unit
        self._detail = []  # store every line of data
        self.child = None  # subprocress of iperf
        '''store iperf UDP packet error rate (PER) result'''
        # self._per = ""
        self._lost = -1  # udp lost packet
        self._total = -1  # udp total packet
        self._per = -1   # udp pcaket lost rate %

    def set_bidir(self, isBidir=True):
        self._bidir = isBidir

    def set_protocal(self, protocal):
        '''set iperf run protocal: 0: TCP, 1: UDP'''
        if protocal in [0, "0"]:
            self._tcp = IPERFprotocal.get("TCP")
        elif protocal in [1, "1"]:
            self._tcp = IPERFprotocal.get("UDP")
        else:
            print("Unknown protocal:%s" % protocal)

    def enqueue_output(self, out, queue):
        '''store out line by line in queue'''
        for line in iter(out.readline, b''):
            queue.put(line)
        self.log("enqueue_output", "enqueue_output: %s" % line)

    def execCmd(self, sCmd):
        '''exec sCmd and return subprocess.Popen'''
        self.proc = None
        try:
            # cmd = "%s %s" % (self.cmd, "ei")
            cmd = sCmd
            self.log("execCmd", "exec cmd: %s" % cmd)
            self.proc = subprocess.Popen(cmd, shell=False, bufsize=1000,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        except Exception as err:
            self.traceback("execCmd:%s" % err)
            return None

        return self.proc

    def version(self):
        '''get iperf version, return version number'''
        cmd = "%s %s" % (self.iperf, "-v")
        proc = self.execCmd(cmd)
        if proc is None:
            return -1
        retval = proc.wait()
        if retval == 0:
            for line in proc.stdout:
                line = line.decode("utf-8")
                if 'iperf' in line:
                    return line.split()[1]
        else:
            return retval

    def getPID(self):
        '''get proc's pid '''
        if self.proc:
            return self.proc.pid
        else:
            return -1

    def isRunning(self):
        ''' check is running'''
        self.log("isRunning", "stoped: %s" % self.stoped)
        return not self.stoped

    @pyqtSlot()
    def do_stop(self):
        ''' stop the thread  '''
        if LOCKER:
            LOCKER.lock()
        self.stoped = True
        if self.child:
            self.child.terminate()
            # set proc obj to None to remove Z (Zombie) proc under linux
            self.child = None
        self.sCmd.clear()
        if LOCKER:
            LOCKER.unlock()
    
    def getMaxWindowSize(self):
        # # https://segmentfault.com/a/1190000000473365
        # Linux Max = 425984 = 212992 * 2
        # cat /proc/sys/net/core/rmem_max
        # cat /proc/sys/net/core/rmem_default
        # cat /proc/sys/net/core/wmem_max
        # cat /proc/sys/net/core/wmem_default
        # cat /proc/sys/net/ipv4/tcp_window_scaling
        # https://access.redhat.com/documentation/zh-tw/red_hat_enterprise_linux/6/html/performance_tuning_guide/s-network-dont-adjust-defaults
        # #read
        # sudo sysctl -w net.core.rmem_max=67108864
        # sysctl -w net.core.rmem_default=N
        # #write
        # sudo sysctl -w net.core.wmem_max=67108864
        # sysctl -w net.core.wmem_default=N
        # #apply swtting
        # sudo sysctl -p

        # android (samsung S22+)           
        #  cat /proc/sys/net/core/rmem_max    => 16777216
        #  cat /proc/sys/net/core/wmem_max    => 8388608


        # FIX setting
        # /etc/sysctl.d/mem.conf
        # net.core.rmem_default=67108864
        # net.core.wmem_default=67108864

        # net.core.rmem_max=67108864
        # net.core.wmem_max=67108864
        # sudo service procps force-reload

        iResult = -1
        if platform.platform() == "Linux":
            result = subprocess.run(['cat', '/proc/sys/net/core/wmem_max'], stdout=subprocess.PIPE)
            if type(result.stdout) == bytes:
                try:
                    iResult = int(result.stdout.decode())
                except Exception as err:
                    self.log("getMaxWindowSize", "getMaxWindowSize: %s" % err)
        elif platform.platform() == "windows":
            print("TODO: get Windows TCP window size")
            # iResult = 121460
        else:
            print("TODO: get %s TCP window size" % platform.platform())
        return iResult

    def get_port(self):
        '''return port'''
        return self.port

    def get_packeterrorrate(self):
        '''get store iperf UDP packet error rate (PER) result'''
        # return str(self._per)
        return self._per

    def get_per_detail(self):
        '''get store iperf UDP lost/total/packet error rate (PER) result'''
        # return str(self._per)
        return self._lost, self._total, self._per, self._result

    def get_result(self):
        '''get store iperf average result in dict'''
        if self._bidir:
            if len(self._result.keys())>1:
                iSum = self._result.get("SUM")
                if iSum is None:
                    self._result["SUM"] = sum(self._result.values())
                print("_result sum: %s, _result: %s" % (iSum, self._result))
        return self._result

    def get_resultunit(self):
        '''get store iperf average result'''
        # print("get_resultunit: %s" % self._result)
        return str(self._resultunit)

    def get_resultdetail(self):
        '''get store iperf all result lines'''
        return self._detail

    def clear_resultdetail(self):
        '''clear result data to free memory usage??'''
        self._detail.clear()

    def set_cmd(self, cmd):
        if LOCKER:
            LOCKER.lock()
        self.sCmd = cmd
        if LOCKER:
            LOCKER.unlock()

    def set_parallel(self, parallel):
        '''set parallel to get correct result'''
        if parallel <= 0:
            parallel = 1
        self._parallel = parallel

    def set_duration(self, duration):
        if duration <= 0:
            duration = 1
        self._duration = duration

    def set_tradeoff(self, tradeoff):
        if tradeoff:
            self._tradeoff = True
        else:
            self._tradeoff = False

    @pyqtSlot()
    def task(self):
        # pexpect way to run program, !!!!not work on windows!!!!
        # Note: This is never called directly. It is called by Qt once the
        # thread environment has been set up.
        # exec by QThread.start()
        # tID = QThread.currentThread()
        tID = '%s' % int(QThread.currentThreadId())
        self._result = {}
        self.stoped = False
        self._tradeoffCount = 0
        self.exiting = False
        self.log('task', "start task", 4)
        self.child = None
        while not self.exiting:
            try:
                while len(self.sCmd) <= 0:
                    QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                    self.log("task", "wait sCmd", 4)
                    time.sleep(0.5)
                if len(self.sCmd) > 0:
                    if platform.system() == 'Linux':
                        self.log("task", "sCmd: %s" % (" ".join(self.sCmd)))
                        # env = {"PYTHONUNBUFFERED": "1"}
                        self.child = subprocess.Popen(self.sCmd, shell=False,
                                                      bufsize=1,
                                                      universal_newlines=True,
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.STDOUT)
                                                    #   , env=env)
                        # need this to kill iperf3 procress
                        # atexit.register(self.kill_proc, self.child)
                        # if self.child is None:
                        #     self.signal_finished.emit(-1,
                        #                               "command error:%s" % self.sCmd)
                        #     return -1
                        # # following will not get realtime output!!
                        # for line in iter(self.child.stdout.readline, ''):
                        #     rs = line.rstrip()
                        #     if rs:
                        #         # output result
                        #         self._handel_dataline(tID, rs)
                        #         if "iperf Down." in rs:
                        #             # iperf3 finish running
                        #             self.signal_finished.emit(0, "iperf Down")
                        #     else:
                        #         rc = self.child.poll()
                        #         if rc is not None:
                        #             self.log("iperf returncode: %s" % self.child.returncode)
                        #             self.signal_finished.emit(0,
                        #                                       "program exit(%s)" % rc)
                        #     if self.stoped:
                        #         self.signal_finished.emit(1, "set stop!!")
                        #         break
                        #     QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                    elif platform.system() == 'Windows':
                        # TODO: windows how to output result with realtime!!
                        # PIPE is not working!!, iperf3 will buffer it
                        #os.environ["PYTHONUNBUFFERED"] = "1"
                        self.log("task", "sCmd: %s" % (" ".join(self.sCmd)))
                        self.child = subprocess.Popen(self.sCmd, shell=False,
                                                      bufsize=1,
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.STDOUT)
                        # need this to kill iperf3 procress
                        # atexit.register(self.kill_proc, self.child)
                        # if self.child is None:
                        #     self.signal_finished.emit(-1, "command error")
                        #     return -1

                        # for line in iter(self.child.stdout.readline, b''):
                        #     QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                        #     rs = line.rstrip().decode("utf-8")
                        #     if rs:
                        #         # output result
                        #         self._handel_dataline(tID, rs)
                        #         if "iperf Down." in rs:
                        #             # iperf3 finish running
                        #             self.signal_finished.emit(0, "iperf Down")
                        #     else:
                        #         rc = self.child.poll()
                        #         if rc is not None:
                        #             self.log("iperf returncode: %s" % self.child.returncode)
                        #             self.signal_finished.emit(0,
                        #                                       "program exit(%s)" % rc)
                        #     if self.stoped:
                        #         self.signal_finished.emit(1, "set stop!!%s" % tID)
                        #         break
                    else:
                        QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                        if self.stoped:
                            self.signal_finished.emit(2, "set stop!!%s" % tID)
                            break
                        pass
                    if self.child is None:
                            self.signal_finished.emit(-1, "command error")
                            return -1
                    for line in iter(self.child.stdout.readline, b''):
                        QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                        if type(line) == str:
                            rs = line.rstrip()
                        else:
                            rs = line.rstrip().decode("utf-8")
                        if rs:
                            # output result
                            self._handel_dataline(tID, rs)
                            if "iperf Down." in rs:
                                # iperf3 finish running
                                self.signal_finished.emit(0, "iperf Down")
                        else:
                            rc = self.child.poll()
                            if rc is not None:
                                self.log("task", "iperf returncode: %s" % self.child.returncode)
                                self.signal_finished.emit(0,
                                                            "program exit(%s)" % rc)
                        if self.stoped:
                            self.signal_finished.emit(1, "set stop!!%s" % tID)
                            break
                else:
                    QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                    if self.stoped:
                        self.signal_finished.emit(3, "set stop!!%s" % tID)
                        break
                    self.log('task', "wait for command!!")
                    continue
            except Exception as err:
                self.traceback("task:%s" % err)
                # raise
            finally:
                self.log('task', "proc end!!", 4)
                # atexit.unregister(self.kill_proc)
                self.sCmd.clear()
                self.exiting = True

            if self.stoped:
                self.signal_finished.emit(1, "signal_finished!!")
                break
            QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
        self.log("task", "task end!!", 4)
        self.signal_finished.emit(1, "task end!!")

    def _handel_dataline(self, tID, line):
        '''handle data output from iperf'''
        curDirection = "Tx"
        detail = line.strip()
        if len(detail) > 0:
            # recore every line except empty line
            if (detail=="\r") or (detail == "\r\n"):
                # do not record line contain only \r or \r\n
                pass
            else:
                self._detail.append(detail)
        if ("[" in line) and ("]" in line):
            # this suould be data we care
            if "local" in line:
                # record header data
                # print("HEADER: %s" % (line))
                self.log(tID, "HEADER: %s" % line, 4)
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
                    self.log(tID, "TODO(iperf v%s)line: %s" % (self.iperfver, line))
        elif ("failed" in line) or ("error" in line):
            # something wrong!
            eMsg = "error handle: %s" % line
            self.log(tID, eMsg)
            self.signal_finished.emit(0, eMsg)
            self.do_stop()
        else:
            self.log(tID, "IGNORE: %s" % (line))
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

    def kill_proc(self, proc):
        try:
            self.log("kill_proc", "kill_proc:%s" % proc)
            if platform.system() == 'Linux':
                # if not proc.terminate(force=True):
                #    print("%s not killed" % proc)
                subprocess.call(['sudo', 'kill', str(proc.pid)])
            else:
                # if platform.system() == 'Windows':
                proc.terminate()

        except Exception:
            self.traceback("kill_proc")
            pass

    def log(self, mType, msg, level=1):
        # mType: message type,
        # msg : message to log
        # level : debug level
        '''logging.INFO = 20'''
        if self._DEBUG > level:
            # print("Iperf log: (%s) %s" % (mType, msg))
            msg = "(%s) %s" % (mType, msg)
            # self.signal_debug.emit(self.__class__.__name__, msg)

    def traceback(self, err=None):
        exc_type, exc_obj, tb = sys.exc_info()
        # This function returns the current line number
        # set in the traceback object.
        lineno = tb.tb_lineno
        self.signal_debug.emit(self.__class__.__name__,
                               "%s - %s - Line: %s (%s)" % (exc_type,
                                                            exc_obj, lineno,
                                                            err))


class IperfServer(QObject):
    """ A network testing server that will start an iperf3 in QThread
    server on any given port."""
    # thread, int: type, str: message
    signal_result = pyqtSignal(int, int, str)
    signal_finished = pyqtSignal(int, str)
    signal_debug = pyqtSignal(str, str)  # class, msg

    # thread id, --parallel num, iperf live data output
    sig_data = pyqtSignal(int, str, str)

    def __init__(self, port=DEFAULT_IPERF3_PORT, iperfver=3, parent=None):
        super(IperfServer, self).__init__(parent)
        # super(IperfServer, self).__init__(port,
        #                                   iperfver=iperfver,
        #                                   parent=parent)
        self._DEBUG = 2
        # Tx: 5201
        self._o = {}  # store obj
        self._o["Iperf"] = Iperf(port=port, iperfver=iperfver)
        self._o["Iperf"].signal_debug.connect(self._on_debug)
        self._o["Iperf"].signal_error.connect(self.log)
        self._o["Iperf"].signal_result.connect(self._on_result)
        self._o["Iperf"].signal_finished.connect(self._on_finished)
        self._o["Iperf"].sig_data.connect(self._on_date)
        # self._o["iThread"] = IperfThread()
        self.log("0", "create Iperf server")
        self._o["iThread"] = QThread()
        self._o["Iperf"].moveToThread(self._o["iThread"])
        self._o["iThread"].started.connect(self._o["Iperf"].task)
        self._o["iThread"].start()

        self.setServerCmd()
    
    def getMaxWindowSize(self):
        rc = -1
        if self._o["Iperf"]:
            rc = self._o["Iperf"].getMaxWindowSize()
        return rc

    def setServerCmd(self):
        '''iperf server command'''
        self.log("0", "setServerCmd")
        sCmd = [self._o["Iperf"].iperf, '-s', '-p', str(self._o["Iperf"].port),
                "-i", "1", "--forceflush", "--one-off"]

        # self._o["Iperf"].sCmd = sCmd
        self._o["Iperf"].set_cmd(sCmd)

    def stop(self):
        if self._o["Iperf"]:
            self._o["Iperf"].do_stop()
        # if self.RxIperf:
        #     self.RxIperf.do_stop()

    @pyqtSlot(str, str)
    def _on_debug(self, sType, sMsg):
        # print(" _on_debug (%s) %s" % (sType, sMsg))
        self.signal_debug.emit(sType, "[%s]%s" % (self.__class__.__name__,
                                                  sMsg))

    @pyqtSlot(int, str, str)
    def _on_date(self, tid, ipall, data):
        '''iperf live data line'''
        # print("[_on_date]%s: %s" % (tid, data))
        self.sig_data.emit(tid, ipall, data)

    @pyqtSlot(int, int, str)
    def _on_result(self, tid, iType, msg):
        self.signal_result.emit(tid, iType, msg)  # output result

    # @pyqtSlot(str, str)
    # def log(self, mType, msg):
    #     print("[%s]%s: %s" % (self.__class__.__name__, mType, msg))

    @pyqtSlot(int, str)
    def _on_finished(self, iCode, msg):

        if self._o["iThread"] is not None:
            self.log('0', "try stop thread: %s - %s" % (iCode, msg))
            self._o["iThread"].quit()
        # if self.RxIperfTh is not None:
        #     self.RxIperfTh.quit()
        self.signal_finished.emit(iCode, msg)

    def get_port(self):
        return self._o["Iperf"].get_port()

    def isRunning(self):
        if self._o["iThread"]:
            return self._o["iThread"].isRunning()
        else:
            return False

    def log(self, mType, msg, level=1):
        '''logging.INFO = 20'''
        # show on stdout
        if self._DEBUG > level:
            # print("IperfServer log: (%s) %s" % (mType, msg))
            self.signal_debug.emit(self.__class__.__name__, msg)


class IperfClient(QObject):
    """ A network testing client that will start an iperf2/3 in QThread
    which will connect to specify iperf2/3 server."""
    # row, col, thread, iParallel, data
    signal_result = pyqtSignal(int, int, int, int, str) # excel row, excel col, thread id, iPall index, 
    signal_finished = pyqtSignal(int, str)
    # row, col, sType, sMsg
    signal_error = pyqtSignal(int, int, str, str)
    signal_debug = pyqtSignal(str, str)

    # thread id, --parallel num, iperf live data output
    sig_data = pyqtSignal(int, str, str)

    def __init__(self, port=5201, args=None,
                 iRow=0, iCol=0, iperfver=3, parent=None):
        super(IperfClient, self).__init__(parent)
        self._DEBUG = 2
        self._opt = {}
        # index for report ?
        self._opt["row"] = iRow
        self._opt["col"] = iCol
        self._opt["version"] = iperfver
        self._o = {}  # store obj
        self.server = ""
        self.port = port
        self.sCmd = ""
        self._opt["conTimeout"] = 5000  # iperf3 --connect-timeout (ms)

        self.isReverse = False
        self.log("0", "IperfClient ver:%s" % self._opt["version"], 3)

        self._o["Iperf"] = Iperf(port, iperfver=self._opt["version"])
        self._o["Iperf"].signal_debug.connect(self._on_debug)
        self._o["Iperf"].signal_error.connect(self.error)
        self._o["Iperf"].signal_result.connect(self._on_result)
        self._o["Iperf"].signal_finished.connect(self._on_finished)
        self._o["Iperf"].sig_data.connect(self._on_date)
        # most place there
        self.args = args
        self._parser_args(args)

        # self._o["iThread"] = IperfThread()
        self._o["iThread"] = QThread()
        self._o["Iperf"].moveToThread(self._o["iThread"])
        self._o["iThread"].started.connect(self._o["Iperf"].task)
        self._o["iThread"].finished.connect(self._o["iThread"].deleteLater)
        # self._o["iThread"].start()

    def getMaxWindowSize(self):
        rc = -1
        if self._o["Iperf"]:
            rc = self._o["Iperf"].getMaxWindowSize()
        return rc

    def get_cmd(self):
        '''get cmd '''
        return self.sCmd

    def setRowCol(self, Row, Col):
        self._opt["row"] = Row
        self._opt["col"] = Col

    @pyqtSlot(str, str)
    def error(self, sType, sMsg):
        print("No iperf command (%s) %s" % (sType, sMsg))
        self.signal_error.emit(self._opt["row"], self._opt["col"], sType, sMsg)

    @pyqtSlot(int, str, str)
    def _on_date(self, tid, ipall, data):
        '''iperf live data line'''
        # print("[%s]%s: %s" % (self.__class__.__name__, tid, data))
        self.sig_data.emit(tid, ipall, data)

    @pyqtSlot(str, str)
    def _on_debug(self, sType, sMsg):
        # print("IperfClient _on_debug (%s) %s" % (sType, sMsg))
        self.signal_debug.emit(sType, "DEBUG[%s]%s" % (self.__class__.__name__,
                                                       sMsg))

    @pyqtSlot(int, int, str)
    def _on_result(self, tid, iType, msg):
        # print("IperfClient _on_result (%s)%s: %s" % (tid, iType, msg))
        self.signal_result.emit(self._opt["row"], self._opt["col"],
                                tid, iType, msg)

    @pyqtSlot(int, str)
    def _on_finished(self, iCode, msg):
        if self._o["iThread"]:
            if self._o["iThread"].isRunning():
                self._o["iThread"].quit()
                self._o["iThread"].wait()
        self.signal_finished.emit(iCode, msg)

    def set_reverse(self, reverse):
        if reverse:
            # iperf v2.0.12 Linux not support this
            self.sCmd.append("-R")

    def _parser_args(self, args):
        '''after setting client cmd, the iperf will start running'''
        '''iperf client command'''
        # sFromat='M', isTCP=True, duration=10, parallel=1,
        # isReverse=False, iBitrate=0, sBitrateUnit='K',
        # iWindowSize=65535, sWindowSizeUnit=''
        # TODO: parser iperf v2 command
        if args is None:
            self.log("0", "No iperf client options")
            return

        # uncmpstr = zlib.decompress(args)
        # ds = ast.literal_eval(uncmpstr)
        if type(args) == str:
            ds = ast.literal_eval(args)
        else:
            self.log("-1", "unknown type of iperf args %s" % args)
            return

        self.server = ds.get("server")
        bind_client = ds.get("client", "")
        protocal = ds.get("protocal", 0)
        self._o["Iperf"].set_protocal(protocal)
        duration = ds.get("duration", 10)
        parallel = ds.get("parallel", 1)
        interval = ds.get("interval", 1)
        reverse = ds.get("reverse", 0)
        bidir = ds.get("bidir", 0)  # bi-direction
        if bidir==1:
            self._o["Iperf"].set_bidir(True)
        OldIperf3 = ds.get("OldIperf3", 0)  # OldIperf3 which not support --bidir
        tradeoff = ds.get("tradeoff", 0)
        bitrate = ds.get("bitrate", 0)
        unit_bitrate = ds.get("unit_bitrate")
        windowsize = ds.get("windowsize", 0)
        unit_windowsize = ds.get("unit_windowsize")
        dscp = ds.get("dscp", -1)
        maximum_segment_size = ds.get("maximum_segment_size", 0)
        fmtreport = ds.get("fmtreport", "m")
        omit = ds.get("omit", 0)
        self._opt["conTimeout"] = ds.get("conTimeout", 5000)

        if self.server:
            self.sCmd = [self._o["Iperf"].iperf, '-c', self.server,
                         '-p', "%s" % (self.port), '-i', '%s' % interval]
            if bind_client:
                self.sCmd.append("-B")
                self.sCmd.append("%s" % bind_client)
            if protocal == 0:
                pass
            else:
                self.sCmd.append("-u")

            if duration > 0:
                self.sCmd.append("-t")
                self.sCmd.append("%s" % duration)
                self._o["Iperf"].set_duration(duration)

            if parallel > 1:
                iPara = parallel
                self.sCmd.append("-P")
                if bitrate > 0 and protocal == 0:
                    iPara = 1
                    self.log("UDP with target bitrate %s %s, the parallel will force to %s" % (bitrate, unit_bitrate, iPara))
                self.sCmd.append("%s" % iPara)
                self._o["Iperf"].set_parallel(iPara)

            # run in reverse mode (server sends, client receives)
            self.set_reverse(reverse)

            if tradeoff == 1:
                # this will cause iperf2.0.5 server terminal when finish test!!
                self.sCmd.append("--tradeoff")  # --tradeoff
                self._o["Iperf"].set_tradeoff(tradeoff)
            else:
                if bidir == 1:
                    if self._opt["version"] == 3:
                        if not OldIperf3:
                            self.sCmd.append("--bidir")
                        else:
                            print("Not support --bidir on old iperf3 (<3.7)")
                    else:
                        self.sCmd.append("-d")  # --dualtest

            if bitrate > 0:
                self.sCmd.append("-b")
                self.sCmd.append("%s%s" % (bitrate, unit_bitrate))
            #     self.sCmd.append("%s%s" % (iBitrate, sBitrateUnit))

            if windowsize > 0:
                if 0:
                    # TODO: MaxWindowSize
                    if unit_windowsize in ["K", "M", "G"]:
                        iWs = windowsize
                        if unit_windowsize in ["G"]:
                            iWs = iWs * 1024
                        if unit_windowsize in ["M", "G"]:
                            iWs = iWs * 1024
                        if unit_windowsize in ["K", "M", "G"]:
                            iWs = iWs * 1024
                        # check cat /proc/sys/net/core/wmem_max
                        iMaxWS = self.getMaxWindowSize()
                        if iMaxWS >0:
                            if iWs > iMaxWS:
                                print("TCP Window Size over %s system allow Max Window size %s" %(iWs, iMaxWS))
                                windowsize = iMaxWS
                            else:
                                windowsize = iWs

                # if windowsize > 425984:
                #     self.log("0", "Max window size is %s" % 425984)
                #     windowsize = 425984
                self.sCmd.append("-w")
                # if unit_windowsize not in ["K", "M", "G"]:
                #     windowsize = "%sK" % windowsize
                # else:
                #     windowsize = "%s%s" % (windowsize, unit_windowsize)
                self.sCmd.append("%s%s" % (windowsize, unit_windowsize))

                
            # TODO: how to set dscp value/format tos?
            #if dscp >= 0:
            #    self.sCmd.append("--dscp %s" % dscp)

            if maximum_segment_size > 0:
                # set TCP/SCTP maximum segment size (MTU - 40 bytes)
                # -M, , --set-mss
                self.sCmd.append("--set-mss") 
                self.sCmd.append("%s" % maximum_segment_size)

            if omit > 0:
                if self._opt["version"] == 3:
                    self.sCmd.append("-O")
                    self.sCmd.append("%s" % omit)

            if fmtreport:
                self.sCmd.append("-f")
                self.sCmd.append(fmtreport)

            # --logfile f: log output to file
            if self._opt["version"] == 3:
                # --connect-timeout ms
                self.sCmd.append("--connect-timeout")
                self.sCmd.append('%s' % self._opt["conTimeout"])
                # force flush output
                self.sCmd.append("--forceflush")

            # TODO:  -l, --len #[KMG]
            # length of buffer to read or write
            # (default 128 KB for TCP, 8 KB for UDP)

            # TODO: -4, --version4            only use IPv4
            # TODO: -6, --version6            only use IPv6
            scmd = " ".join(self.sCmd)
            #print("cmd: %s" % scmd)
            self.log("_parser_args", "%s" % scmd)
        else:
            self.log("_parser_args", "ERROR: No target server in setting!!")

    def start(self):
        self._o["iThread"].start()
        if len(self.sCmd) <= 0:
            self.error("-1", "Not iperf cmd")
            return -1
        self._o["Iperf"].set_cmd(self.sCmd)
        # self._o["Iperf"].sCmd = self.sCmd

    def startTest(self):
        self._o["Iperf"].stoped = False
        self._o["iThread"].start()

    def get_server_ip(self):
        return self.server

    def get_port(self):
        return self._o["Iperf"].get_port()

    def get_packeterrorrate(self):
        '''get store iperf UDP packet error rate (PER) result'''
        rc = self._o["Iperf"].get_packeterrorrate()
        # self.log("get_packeterrorrate",  "%s" % rc)
        return rc

    def get_per_detail(self):
        '''get store iperf UDP packet error rate (PER) detail result'''
        # return lost/total/Packet error rate/throughput
        rc = self._o["Iperf"].get_per_detail()
        if len(rc) >= 4:
            return rc[0], rc[1], rc[2], rc[3]
        else:
            return "error get_per_detail: %s" % (rc,), "", "", ""

    def get_result(self):
        '''get store iperf average result'''
        return self._o["Iperf"].get_result()

    def get_resultunit(self):
        '''get store iperf average result unit'''
        return self._o["Iperf"].get_resultunit()

    def get_resultdetail(self):
        '''get store iperf all result'''
        rc = self._o["Iperf"].get_resultdetail()
        return rc

    def clear_resultdetail(self):
        self._o["Iperf"].clear_resultdetail()

    def isRunning(self):
        # st = self._o["iperf"].isRunning() and self._o["iThread"].isRunning()
        # print("client is running: %s" % (st))
        return self._o["iThread"].isRunning()

    def stop(self):
        if self._o["Iperf"]:
            self._o["Iperf"].do_stop()
            # wait thread stop
            iWait = 15
            while self._o["iThread"].isRunning():
                QCoreApplication.processEvents(QEventLoop.AllEvents, 1)
                time.sleep(1)
                if iWait > 0:
                    iWait = iWait - 1
                else:
                    # TODO: check force QThread to terminate
                    self._o["iThread"].terminate()
                    # self._o["iThread"].wait()
                    break

    def log(self, mType, msg, level=1):
        if self._DEBUG > level:
            m = "%s-%s" % (mType, msg)
            print(m)
            self.signal_debug.emit(self.__class__.__name__, m)
