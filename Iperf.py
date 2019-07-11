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
import datetime
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
                              pyqtSlot, pyqtSignal, QObject, QMutex)
    # from PyQt5.QtWidgets import (QApplication)
except ImportError:
    print("pip install PyQt5")
    raise SystemExit


if platform.system() == 'Windows':
    import atexit
if platform.system() == 'Linux':
    import pexpect


def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()


class iperfResult():
    '''class to handle iperf throughput output line'''
    # TODO:
    iKb = 1024
    iMb = iKb * 1024
    iGb = iMb * 1024
    iTb = iGb * 1024
    iPb = iTb * 1024
    iEb = iPb * 1024
    iZb = iEb * 1024
    iYb = iZb * 1024

    def __init__(self, iParallel, result):
        self.error = False
        self.errorMsg = ""

        self.reportTime = ""
        self.idx = ""
        self.measureTimeStart = 0
        self.measureTimeEnd = 0
        self.measureTimeUnit = 'sec'
        self.totalSend = ""
        self.totalSendUnit = ""
        self.throughput = ""
        self.throughputUnit = ""
        # TODO: send -> server
# [  9]   9.00-10.00  sec   292 MBytes  2.46 Gbits/sec    0   1.31 MBytes
# [ 11]   9.00-10.00  sec   292 MBytes  2.46 Gbits/sec    0   2.00 MBytes
# [ 17]   9.00-10.00  sec   292 MBytes  2.46 Gbits/sec    0   1.31 MBytes
# [SUM]   9.00-10.00  sec  1.43 GBytes  12.3 Gbits/sec    0
# - - - - - - - - - - - - - - - - - - - - - - - - -
# [ ID] Interval           Transfer     Bitrate         Retr
# [  5]   0.00-10.00  sec  2.96 GBytes  2.54 Gbits/sec    0             sender
# [  5]   0.00-10.00  sec  2.97 GBytes  2.55 Gbits/sec                  receiver
# [  7]   0.00-10.00  sec  2.96 GBytes  2.54 Gbits/sec    0             sender
# [  7]   0.00-10.00  sec  2.97 GBytes  2.55 Gbits/sec                  receiver
# [  9]   0.00-10.00  sec  2.96 GBytes  2.54 Gbits/sec    0             sender

        #  -R mode, have different output format
# [  9]   9.00-10.00  sec   310 MBytes  2.60 Gbits/sec
# [ 11]   9.00-10.00  sec   310 MBytes  2.60 Gbits/sec
# [ 17]   9.00-10.00  sec   310 MBytes  2.60 Gbits/sec
# [SUM]   9.00-10.00  sec  1.51 GBytes  13.0 Gbits/sec
# - - - - - - - - - - - - - - - - - - - - - - - - -
# [ ID] Interval           Transfer     Bitrate         Retr
# [  5]   0.00-9.99   sec  2.87 GBytes  2.47 Gbits/sec    0             sender
# [  5]   0.00-10.00  sec  2.87 GBytes  2.46 Gbits/sec                  receiver
# [  7]   0.00-9.99   sec  2.87 GBytes  2.47 Gbits/sec    0             sender

        #
        self.iParallel = iParallel
        try:
            if result is not None:
                self.reportTime = datetime.datetime.now()
                if ('sender' in result) or ('receiver' in result):
                    print("This is avg: %s" % result)
                    # -P 2 TODO: should get SUM
                    # [  5]   0.00-10.03  sec   562 MBytes   470 Mbits/sec                  sender
                    # [  7]   0.00-10.03  sec   561 MBytes   469 Mbits/sec                  sender
                    # [SUM]   0.00-10.03  sec  1.10 GBytes   939 Mbits/sec                  sender
                    # -P 1
                    # [  5]   0.00-10.00  sec  15.5 GBytes  13.3 Gbits/sec    0             sender
                    # [  5]   0.00-10.00  sec  1.09 GBytes   937 Mbits/sec    0             sender
                    # return None
                    rs = result.strip().split(']')
                    self.idx = rs[0].replace('[', '').strip()

                    rs = rs[1].split(' ')
                    nrs = list(filter(None, rs))
                    self.measureTimeStart = nrs[0].split('-')[0]
                    self.measureTimeEnd = nrs[0].split('-')[1]
                    self.measureTimeUnit = nrs[1].strip()

                    self.totalSend = nrs[2].strip()
                    self.totalSendUnit = nrs[3].strip()

                    self.throughput = nrs[4].strip()
                    self.throughputUnit = nrs[5].strip()

                    '''
                    rs = result.strip().split(' ')
                    #nrs = [x for x in rs if x] # remove empty string (slow?)
                    nrs =list(filter(None, rs)) # remove empty string
                    self.idx = nrs[1][0:1].strip()
                    #nrs = rs[1].split('  ')
                    self.measureTimeStart = nrs[2].split('-')[0]
                    self.measureTimeEnd = nrs[2].split('-')[1]

                    self.measureTimeUnit = nrs[3].strip()

                    #v, u =nrs[2].split(" ")
                    self.totalSend = nrs[4].strip()
                    self.totalSendUnit = nrs[5].strip()

                    #v, u =nrs[3].split(" ")
                    self.throughput = nrs[6].strip()
                    self.throughputUnit = nrs[7].strip()
                    '''

                elif ('ID') in result:
                    print("This is header: %s" % result)
                    return None
                else:
                    rs = result.strip().split('   ')

                    # print(rs[0][1:4]), idx 1,2,3... or SUM
                    self.idx = rs[0][1:4].strip()
                    # print(rs[1].split('-')[0])
                    self.measureTimeStart = rs[1].split('-')[0]
                    self.measureTimeEnd = rs[1].split('-')[1]
                    # print(rs[2])
                    self.measureTimeUnit = rs[2].strip()
                    # print(rs[3])
                    v, u = rs[3].split(" ")
                    self.totalSend = v
                    self.totalSendUnit = u
                    # print(rs[4])
                    v, u = rs[4].split(" ")
                    self.throughput = v
                    self.throughputUnit = u
                # print(rs[5].strip())
                # print(rs[6].strip())
        except:
            self.error = True
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            return None
            # traceback.print_exc(file=sys.stdout)

    def convertReportTime(self, sTime):
        '''convert string sTime (20170813164651) to datetime format'''
        # print(sTime[:4]) #year
        # print(sTime[4:6]) #month
        # print(sTime[6:8]) #day
        # print(sTime[8:10]) #hr
        # print(sTime[10:12]) #min
        # print(sTime[12:14]) #sec
        d = datetime.datetime(year=int(sTime[:4]),
                              month=int(sTime[4:6]),
                              day=int(sTime[6:8]),
                              hour=int(sTime[8:10]),
                              minute=int(sTime[10:12]),
                              second=int(sTime[12:14]))
        return d

    def convert_bytes(self, bytes):
        bytes = float(bytes)
        # YB: yottabyte = zettabyte * 1024
        if bytes >= self.iYb:  # 1024*1024*1024*1024*1024*1024*1024*1024
            yottabyte = bytes / self.iYb
            size = '%.2f Y' % yottabyte
        if bytes >= self.iZb:  # 1024*1024*1024*1024*1024*1024*1024
            zettabyte = bytes / self.iZb
            size = '%.2f Z' % zettabyte
        elif bytes >= self.iEb:  # 1024*1024*1024*1024*1024*1024
            exabyte = bytes / self.iEb
            size = '%.2f E' % exabyte
        elif bytes >= self.iPb:  # 1024*1024*1024*1024*1024
            petabytes = bytes / self.iPb
            size = '%.2f P' % petabytes
        elif bytes >= self.iTb:  # 1024*1024*1024*1024
            terabytes = bytes / self.iTb
            size = '%.2f T' % terabytes
        elif bytes >= self.iGb:  # 1024*1024*1024
            gigabytes = bytes / self.iGb
            size = '%.2f G' % gigabytes
        elif bytes >= self.iMb:  # 1024*1024
            megabytes = bytes / self.iMb
            size = '%.2f M' % megabytes
        elif bytes >= self.iKb:
            kilobytes = bytes / self.iKb
            size = '%.2f K' % kilobytes
        else:
            size = '%.2f byte' % bytes
        return size.split(" ")


IPERFprotocal = {
    'TCP': 0,  # TCP
    'UDP': 1,   # UDP
}

'''
class IperfThread(QThread):
    def run(self):
        self.exec_()
'''
locker = QMutex()

DEFAULT_IPERF3_PORT = 5201
DEFAULT_IPERF2_PORT = 5001


class Iperf(QObject):
    '''python of iperf2/iperf3 class'''
    __VERSION__ = '20190711'

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

        # print("iperf: %s" % iperfver)
        if iperfver == 3:
            iperfname = "iperf3"
        else:
            iperfname = "iperf"

        self.iperf = os.path.join(self._basedir, 'bin', platform.system())
        if platform.system() == 'Linux':
            self.iperf = os.path.join(self.iperf, arch, '%s' % iperfname)

        if platform.system() == 'Windows':
            self.iperf = os.path.join(self.iperf, arch, '%s.exe' % iperfname)
            # self.iperf = self.iperf + '.exe'

        # print("use iperf: %s" % self.iperf)
        # if host:
        #     self.host = host
        self.port = port
        self._tcp = IPERFprotocal.get("TCP")  # 0: TCP, 1: UDP,...

        # self.mutex = QMutex()
        # self.mutex.lock()
        self.stoped = False  # user stop
        # self.mutex.unlock()
        self.sCmd = []

        self._parallel = 1  # for report result use

        # store result
        self._result = ""  # store final sum
        self._resultunit = ""  # store final sum unit
        self._detail = []  # store every line of data
        '''store iperf UDP packet error rate (PER) result'''
        self._per = ""

    def set_protocal(self, protocal):
        if protocal in [0, "0"]:
            self._tcp = IPERFprotocal.get("TCP")
        elif protocal in [1, "1"]:
            self._tcp = IPERFprotocal.get("UDP")
        else:
            print("Unknown protocal:%s" % protocal)

    def enqueue_output(self, out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        self.log("0", "enqueue_output: %s" % line)

    def execCmd(self, sCmd):
        '''exec sCmd and return subprocess.Popen'''
        self.proc = None
        try:
            # cmd = "%s %s" % (self.cmd, "ei")
            cmd = sCmd
            self.log("0", "exec cmd: %s" % cmd)
            self.proc = subprocess.Popen(cmd, shell=False, bufsize=1000,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        except:
            self.traceback()
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
        if self.proc:
            return self.proc.pid
        else:
            return -1

    def isRunning(self):
        self.log("0", "stoped: %s" % self.stoped)
        return not self.stoped

    @pyqtSlot()
    def do_stop(self):
        ''' stop the thread  '''
        locker.lock()
        self.stoped = True
        if platform.system() == 'Linux':
            if self.child:
                self.child.terminate(force=True)
        elif platform.system() == 'Windows':
            if self.child:
                self.child.terminate()
        self.sCmd.clear()
        locker.unlock()

    def get_port(self):
        return self.port

    def get_packeterrorrate(self):
        '''get store iperf UDP packet error rate (PER) result'''
        return str(self._per)

    def get_result(self):
        '''get store iperf average result'''
        # print("get_result: %s" % self._result)
        return str(self._result)

    def get_resultunit(self):
        '''get store iperf average result'''
        # print("get_resultunit: %s" % self._result)
        return str(self._resultunit)

    def get_resultdetail(self):
        '''get store iperf all result'''
        return str(self._detail)

    def set_cmd(self, cmd):
        locker.lock()
        self.sCmd = cmd
        locker.unlock()

    def set_parallel(self, parallel):
        '''set parallel to get correct result'''
        if parallel <= 0:
            parallel = 1
        self._parallel = parallel

    @pyqtSlot()
    def task(self):
        # pexpect way to run program, !!!!not work on windows!!!!
        # Note: This is never called directly. It is called by Qt once the
        # thread environment has been set up.
        # exec by QThread.start()
        # tID = QThread.currentThread()
        tID = QThread.currentThreadId()

        self.stoped = False
        self.exiting = False
        self.log('0', "start task", 4)
        self.child = None
        while not self.exiting:
            try:
                while len(self.sCmd) <= 0:
                    QCoreApplication.processEvents()
                    self.log("0", "wait sCmd", 4)
                    time.sleep(0.5)
                if len(self.sCmd) > 0:
                    if platform.system() == 'Linux':
                        self.log("1", "sCmd: %s" % (" ".join(self.sCmd)))
                        self.child = pexpect.spawn(" ".join(self.sCmd),
                                                   encoding='utf-8')
                        # need this to kill iperf3 procress
                        # atexit.register(self.kill_proc, self.child)
                        # while self.child.isalive():
                        while not self.child.eof():
                            QCoreApplication.processEvents()
                            try:
                                # non-blocking readline
                                line = self.child.readline()
                                # print("line: %s" % line)
                                if len(line) == 0:
                                    time.sleep(0.5)
                                    QCoreApplication.processEvents(QEventLoop.AllEvents, 0.5)
                                else:
                                    rs = line.rstrip()
                                    if rs:
                                        if type(rs) == list:
                                            for val in rs:
                                                # handle line by line
                                                self._handel_dataline(tID, val)
                                                QCoreApplication.processEvents(QEventLoop.AllEvents, 0.5)
                                        else:
                                            self._handel_dataline(tID, rs)
                                if self.stoped:
                                    self.signal_finished.emit(1,
                                                              "signal_finished!!")
                                    break
                            except pexpect.TIMEOUT:
                                pass
                    elif platform.system() == 'Windows':
                        # TODO: windows how to output result with realtime!!
                        # PIPE is not working!!, iperf3 will buffer it
                        self.log("1", "sCmd: %s" % (" ".join(self.sCmd)))
                        # following will have extra shell to launch app
                        # self.proc = subprocess.Popen(' '.join(self.sCmd), shell=True,
                        #
                        self.child = subprocess.Popen(self.sCmd, shell=False,
                                                      bufsize=1,
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.STDOUT)
                        # need this to kill iperf3 procress
                        atexit.register(self.kill_proc, self.child)

                        if self.child is None:
                            self.signal_finished.emit(-1, "command error")
                            return -1

                        # following will block
                        # do task, wait procress finish
                        for line in iter(self.child.stdout.readline, b''):
                            QCoreApplication.processEvents()
                            rs = line.rstrip().decode("utf-8")
                            if rs:
                                #output result
                                self._handel_dataline(tID, rs)
                            if self.stoped:
                                self.signal_finished.emit(1, "set stop!!")
                                break
                    else:
                        QCoreApplication.processEvents()
                        if self.stoped:
                            self.signal_finished.emit(1, "set stop!!")
                            break
                        pass
                else:
                    QCoreApplication.processEvents()
                    if self.stoped:
                        self.signal_finished.emit(1, "set stop!!")
                        break
                    self.log('0', "wait for command!!")
                    continue
            except:
                self.traceback()
                # raise
            finally:
                self.log('0', "proc end!!", 4)
                # atexit.unregister(self.kill_proc)
                self.sCmd.clear()
                self.exiting = True

            if self.stoped:
                self.signal_finished.emit(1, "signal_finished!!")
                break

            QCoreApplication.processEvents()
            # time.sleep(2)

        self.log(0, "task end!!", 4)
        self.signal_finished.emit(1, "task end!!")

    def _handel_dataline(self, tID, line):
        if ("[" in line) and ("]" in line):
            # this suould be data we care
            if "local" in line:
                # record header data
                # print("HEADER: %s" % (line))
                self.log("0", "HEADER: %s" % line, 4)
            elif "Interval" in line:
                # ignore header line
                pass
            else:
                # record
                # [SUM]   0.00-20.00  sec  7.04 MBytes  2.95 Mbits/sec  24.607 ms  16/5115 (0.17%)  receiver
                # [  5]   0.00-20.00  sec  7.04 MBytes  2.95 Mbits/sec  24.607 ms  16/5115 (0.17%)  receiver

                self._detail.append(line.strip())  # recore every line
                # --parallel index
                # may be "SUM" or num
                iPall = line[1:4].split()
                if type(iPall) == list:
                    iPall = iPall[0]
                # result data
                data = line[6:].strip()

                # TODO: progress send line data
                if "(omitted)" in line:
                    pass
                # elif "[SUM]" in line:  # When -P 1, there will be no [SUM]
                #     # print("parser: %s" % (line))
                #     pass
                elif "sender" in line:
                    pass
                elif "receiver" in line:
                    # real data need to parser
                    self.log(tID, "parser: %s" % (data))
                    self.signal_result.emit(tID, 0, data)  # TODO:
                    if self._parallel > 1:
                        if "SUM" == iPall:
                            #only procress data when --parallel > 1
                            pass
                        else:
                            return
                    b = data.split()
                    if len(b) >= 7:
                        # print("FOUND RESULT: %s (%s)" % (b[5], b[6]))
                        self._result = b[4]
                        self._resultunit = b[5]
                        if self._tcp == IPERFprotocal.get("UDP"):
                            # ds = re.findall("\d+", b[10])
                            per = b[9]
                            per = per[1:-2]  # remove ( and %)
                            # print("Get UDP PER: %s" % per)
                            self._per = per
                    else:
                        print("wrong format:%s" % b)
                else:
                    # print("%s:%s" % (iPall, data))
                    self.sig_data.emit(tID, iPall, data)

        else:
            # print("IGNORE: %s" % (line))
            pass

    def kill_proc(self, proc):
        try:
            self.log("0", "kill_proc:%s" % proc)
            if platform.system() == 'Linux':
                # if not proc.terminate(force=True):
                #    print("%s not killed" % proc)
                subprocess.call(['sudo', 'kill', str(proc.pid)])
            else:
                # if platform.system() == 'Windows':
                proc.terminate()

        except Exception:
            self.traceback()
            pass

    # def log(self, mType, msg, level=logging.INFO):
    def log(self, mType, msg, level=1):
        '''logging.INFO = 20'''
        if self._DEBUG > level:
            # print("Iperf log: (%s) %s" % (mType, msg))
            msg = "(%s) %s" % (mType, msg)
            self.signal_debug.emit(self.__class__.__name__, msg)

    def traceback(self, err=None):
        exc_type, exc_obj, tb = sys.exc_info()
        # This function returns the current line number
        # set in the traceback object.
        lineno = tb.tb_lineno
        self.signal_debug.emit(self.__class__.__name__,
                               "%s - %s - Line: %s" % (exc_type,
                                                       exc_obj, lineno))


# class IperfServer(Iperf):
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

    def setServerCmd(self):
        '''iperf server command'''
        self.log("0", "setServerCmd")
        sCmd = [self._o["Iperf"].iperf, '-s', '-p', str(self._o["Iperf"].port),
                "-i", "1", "--forceflush"]

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


# class IperfClient(Iperf):
class IperfClient(QObject):
    # row, col, thread, iParallel, data
    signal_result = pyqtSignal(int, int, int, int, str)
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
        # super(IperfClient, self).__init__(port,
        #                                   iperfver=iperfver,
        #                                   parent=parent)
        self._opt = {}
        # index for report ?
        self._opt["row"] = iRow
        self._opt["col"] = iCol
        self._o = {}  # store obj
        self.server = ""
        self.port = port
        self.sCmd = ""
        self._opt["conTimeout"] = 5000  # iperf3 --connect-timeout (ms)

        self.isReverse = False
        self.log("0", "IperfClient ver:%s" % iperfver, 3)

        self._o["Iperf"] = Iperf(port, iperfver=iperfver)
        self._o["Iperf"].signal_debug.connect(self._on_debug)
        self._o["Iperf"].signal_error.connect(self.error)
        self._o["Iperf"].signal_result.connect(self._on_result)
        self._o["Iperf"].signal_finished.connect(self._on_finished)
        self._o["Iperf"].sig_data.connect(self._on_date)
        # most place there
        self._parser_args(args)

        # self._o["iThread"] = IperfThread()
        self._o["iThread"] = QThread()
        self._o["Iperf"].moveToThread(self._o["iThread"])
        self._o["iThread"].started.connect(self._o["Iperf"].task)
        self._o["iThread"].start()

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
        self.signal_debug.emit(sType, "[%s]%s" % (self.__class__.__name__,
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

    def _parser_args(self, args):
        '''after setting client cmd, the iperf will start running'''
        '''iperf client command'''
        # sFromat='M', isTCP=True, duration=10, parallel=1,
        # isReverse=False, iBitrate=0, sBitrateUnit='K',
        # iWindowSize=65535, sWindowSizeUnit=''
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
        protocal = ds.get("protocal")
        self._o["Iperf"].set_protocal(protocal)
        duration = ds.get("duration")
        parallel = ds.get("parallel")
        reverse = ds.get("reverse")
        bitrate = ds.get("bitrate")
        unit_bitrate = ds.get("unit_bitrate")
        windowsize = ds.get("windowsize")
        fmtreport = ds.get("fmtreport")
        omit = ds.get("omit")

        self.sCmd = [self._o["Iperf"].iperf, '-c', self.server,
                     '-p', "%s" % (self.port), '-i', '1']
        if protocal == 0:
            pass
        else:
            self.sCmd.append('-u')

        if duration > 0:
            self.sCmd.append('-t')
            self.sCmd.append("%s" % duration)

        if parallel > 1:
            self.sCmd.append('-P')
            self.sCmd.append("%s" % parallel)
            # self._o["iperf"].iParallel = parallel
            self._o["Iperf"].set_parallel(parallel)

        # run in reverse mode (server sends, client receives)
        if reverse == 1:
            self.sCmd.append('-R')

        if bitrate > 0:
            self.sCmd.append('-b')
            self.sCmd.append("%s%s" % (bitrate, unit_bitrate))
        #     self.sCmd.append("%s%s" % (iBitrate, sBitrateUnit))

        if windowsize > 0:
            # Linux Max = 425984
            if windowsize > 425984:
                self.log("0", "Max window size is %s" % 425984)
                windowsize = 425984
            self.sCmd.append('-w')
            self.sCmd.append("%s" % windowsize)

        if omit > 0:
            self.sCmd.append('-O')
            self.sCmd.append("%s" % omit)

        if fmtreport:
            self.sCmd.append('-f')
            self.sCmd.append(fmtreport)

        # --logfile f: log output to file
        # --connect-timeout ms
        self.sCmd.append('--connect-timeout')
        self.sCmd.append('%s' % self._opt["conTimeout"])
        # force flush output
        # self.sCmd.append('--forceflush')

        # if sFromat:

        # TODO:  -l, --len #[KMG]
        # length of buffer to read or write
        # (default 128 KB for TCP, 8 KB for UDP)

        # TODO: -M, --set-mss
        # # set TCP/SCTP maximum segment size (MTU - 40 bytes)
        # if iMTU:
        #     self.sCmd.append('-M')
        #     self.sCmd.append(str(iMTU))

        # TODO: -4, --version4            only use IPv4
        # TODO: -6, --version6            only use IPv6

        self.log("_parser_args", "%s" % " ".join(self.sCmd))

    def start(self):
        if len(self.sCmd) <= 0:
            self.error("-1", "Not iperf cmd")
            return -1
        self._o["Iperf"].set_cmd(self.sCmd)
        # self._o["Iperf"].sCmd = self.sCmd

    def startTest(self):
        # self.setClientCmd()
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

    def get_result(self):
        '''get store iperf average result'''
        return self._o["Iperf"].get_result()

    def get_resultunit(self):
        '''get store iperf average result unit'''
        return self._o["Iperf"].get_resultunit()

    def get_resultdetail(self):
        '''get store iperf all result'''
        rc = self._o["Iperf"].get_resultdetail()
        self.log("get_resultdetail", "%s" % rc)
        return rc

    def isRunning(self):
        # st = self._o["iperf"].isRunning() and self._o["iThread"].isRunning()
        # print("client is running: %s" % (st))
        return self._o["iThread"].isRunning()

    def stop(self):
        # self.log(self.__class__.__name__, self.RxIperf.getPID())
        self._o["Iperf"].do_stop()

    def log(self, mType, msg, level=1):
        '''logging.INFO = 20'''
        # show on stdout
        if self._DEBUG > level:
            print("IperfClient log: (%s) %s" % (mType, msg))
            # if mType == '1':
            # self.signal_error.emit(mType, msg)
            # else:
            self.signal_debug.emit(self.__class__.__name__, msg)
