#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 13:45:15 2017

@author: jimmy
"""
'''
    subprocrss base iperf3 python class
'''
__version__ = "20170718"

import time
import sys
import traceback
import datetime
import subprocess
import os
import platform
from PyQt5.QtCore import (QThread, pyqtSlot, pyqtSignal, QObject, QMutex)
from PyQt5.QtWidgets import (QApplication)
import logging
import psutil
import atexit
#from nonblock import nonblock_read
#import io
#from threading  import Thread
#from queue import Queue, Empty  # python 3.x


  
def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

class iperfResult():
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

        self.iParallel=iParallel
        try:
            if not result is None:
                self.reportTime = datetime.datetime.now()
                if ('sender' in result) or ('receiver' in result):
                    print("This is avg: %s" % result)
                    #-P 2 TODO: should get SUM
                    #[  5]   0.00-10.03  sec   562 MBytes   470 Mbits/sec                  sender
                    #[  7]   0.00-10.03  sec   561 MBytes   469 Mbits/sec                  sender
                    #[SUM]   0.00-10.03  sec  1.10 GBytes   939 Mbits/sec                  sender
                    #-P 1
                    #[  5]   0.00-10.00  sec  15.5 GBytes  13.3 Gbits/sec    0             sender
                    #[  5]   0.00-10.00  sec  1.09 GBytes   937 Mbits/sec    0             sender
                    #return None
                    rs = result.strip().split(']')
                    self.idx = rs[0].replace('[','').strip()

                    rs = rs[1].split(' ')
                    nrs =list(filter(None, rs))
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
                    
                    #print(rs[0][1:4]), idx 1,2,3... or SUM
                    self.idx = rs[0][1:4].strip()
                    #print(rs[1].split('-')[0])
                    self.measureTimeStart = rs[1].split('-')[0]
                    self.measureTimeEnd = rs[1].split('-')[1]
                    #print(rs[2])
                    self.measureTimeUnit = rs[2].strip()
                    #print(rs[3])
                    v, u =rs[3].split(" ")
                    self.totalSend = v
                    self.totalSendUnit = u
                    #print(rs[4])
                    v, u =rs[4].split(" ")
                    self.throughput = v
                    self.throughputUnit = u
                #print(rs[5].strip())
                #print(rs[6].strip())
        except:
            self.error=True
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            return None
            #traceback.print_exc(file=sys.stdout)
            
    def convertReportTime(self, sTime):
        '''convert string sTime (20170813164651) to datetime format'''
        #print(sTime[:4]) #year
        #print(sTime[4:6]) #month
        #print(sTime[6:8]) #day
        #print(sTime[8:10]) #hr
        #print(sTime[10:12]) #min
        #print(sTime[12:14]) #sec
        d = datetime.datetime(year=int(sTime[:4]),month=int(sTime[4:6]),day=int(sTime[6:8]),
                          hour=int(sTime[8:10]),minute=int(sTime[10:12]),second=int(sTime[12:14]))
        return d
    
    def convert_bytes(self, bytes):
        bytes = float(bytes)
        #YB: yottabyte = zettabyte * 1024
        if bytes >= self.iYb: #1024*1024*1024*1024*1024*1024*1024*1024
            yottabyte = bytes / self.iYb
            size = '%.2f Y' % yottabyte
        if bytes >= self.iZb: #1024*1024*1024*1024*1024*1024*1024
            zettabyte = bytes / self.iZb
            size = '%.2f Z' % zettabyte
        elif bytes >= self.iEb: #1024*1024*1024*1024*1024*1024
            exabyte = bytes / self.iEb
            size = '%.2f E' % exabyte
        elif bytes >= self.iPb: #1024*1024*1024*1024*1024
            petabytes = bytes / self.iPb
            size = '%.2f P' % petabytes
        elif bytes >= self.iTb: #1024*1024*1024*1024
            terabytes = bytes / self.iTb
            size = '%.2f T' % terabytes
        elif bytes >= self.iGb: #1024*1024*1024
            gigabytes = bytes / self.iGb
            size = '%.2f G' % gigabytes
        elif bytes >= self.iMb: #1024*1024
            megabytes = bytes / self.iMb
            size = '%.2f M' % megabytes
        elif bytes >= self.iKb:
            kilobytes = bytes / self.iKb
            size = '%.2f K' % kilobytes
        else:
            size = '%.2f byte' % bytes
        return size.split(" ")


class iperfThread(QThread):
    def run(self):
        self.exec_()

locker = QMutex()
ON_POSIX = 'posix' in sys.builtin_module_names

class iperf3(QObject):
    '''python of iperf3 class'''
    __VERSION__ = '20170816'
    
    signal_result = pyqtSignal(int, str)
    signal_finished = pyqtSignal(int, str)
    signal_error = pyqtSignal(str, str)
    signal_debug = pyqtSignal(str, str)
      
    default_port = 5201
    
    def __init__(self, host='', port=5201, isServer=True, parent=None):
        super(iperf3, self).__init__(None)
        #iperf binary
        if platform.machine() in ['i386','i486','i586', 'i686']:
            arch='x86'
        else:
            arch=platform.machine()

        self.iperf = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  'bin', platform.system())
        if platform.system() == 'Linux':
            self.iperf = os.path.join(self.iperf, arch, 'iperf3')
            
        if platform.system() == 'Windows':
            self.iperf = os.path.join(self.iperf, 'iperf3.exe')
            #self.iperf = self.iperf + '.exe'
        
        #print("use iperf: %s" % self.iperf)
        if host:
            self.host = host
        self.port = port
        self.stoped = False #user stop
        
        self.sCmd= []
        if isServer:
            self.setServerCmd()

        self.iParallel = 0 # for report result use
        #self.q = Queue()
        
    def __del__(self):
        #if self.proc:
        #self.log(0, 'kill')
        #self.kill(self.proc.pid)
        pass
    
    def enqueue_output(self, out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()
    
    def setServerCmd(self):
        '''iperf server command'''
        #self.sCmd = [self.iperf, '-s', '-D', 
        self.sCmd = [self.iperf, '-s', '-p', str(self.port)]
       
    def execCmd(self, sCmd):
        '''exec sCmd and return subprocess.Popen'''
        self.proc=None
        try:
            #cmd = "%s %s" % (self.cmd, "ei")
            cmd = sCmd
            self.log("exec cmd: %s" % cmd)
            self.proc = subprocess.Popen( cmd, shell=False, bufsize=1000,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        except:
            self.traceback()
            return None
        
        return self.proc
    
    def version(self):
        '''get iperf version, return version number'''
        cmd = "%s %s" % (self.iperf, "-v")
        proc= self.execCmd(cmd)
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
        print("stoped: %s" % self.stoped)
        return not self.stoped
        
    @pyqtSlot()
    def do_stop(self):
        ''' stop the thread  '''
        locker.lock()
        self.stoped = True
        self.sCmd.clear()
        locker.unlock()

    @pyqtSlot()
    def task(self):
        '''
        # Note: This is never called directly. It is called by Qt once the
        # thread environment has been set up.
        #exec by QThread.start()
        '''
        self.stoped = False        
        self.exiting = False
        self.log('0',"start task")      
        while not self.exiting:
            try:
                if len(self.sCmd)>0:
                    print("sCmd: %s" % (" ".join(self.sCmd)))
                    #following will have extra shell to launch app
                    #self.proc = subprocess.Popen(' '.join(self.sCmd), shell=True,
                    #
                    self.proc = subprocess.Popen(self.sCmd, shell=False,
                                                 bufsize=1, 
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
                    atexit.register(self.kill_proc, self.proc) #need this to kill iperf3 procress
                    
                    if self.proc is None:
                        #self.signal_debug.emit(self.__class__.__name__, "command error")
                        self.signal_finished.emit(-1, "command error") 
                        return -1
                    
                    #do task, wait procress finish
                    for line in iter(self.proc.stdout.readline, b''):
                        rs = line.rstrip().decode("utf-8")
                        if rs:
                            #print("%s rs: %s" % (datetime.datetime.now(), len(rs)))
                            #print("iParallel: %s" % self.iParallel)
                            self.signal_result.emit(self.iParallel, rs) #output result
                            QApplication.processEvents() 
                            
                    #self.proc.wait()
                else:
                    self.log('0',"wait for command!!")
                    pass
            except:
                self.traceback()
                raise
            finally:
                #self.signal_finished.emit(-1, "proc end!!") 
                self.log('0',"proc end!!")
                #atexit.unregister(self.kill_proc)
                self.sCmd.clear()
                
            if self.stoped:
                self.signal_finished.emit(1, "signal_finished!!")
                break
            
            QApplication.processEvents() 
            time.sleep(2)
            #self.log(0,"task running...")
        
        self.log(0,"task end!!")
        self.signal_finished.emit(1, "task end!!")

    def kill_proc(self, proc):
        try:
            proc.terminate()
        except Exception:
            self.traceback();
            pass
        
    def log(self, mType, msg, level=logging.INFO):
        #show on stdout
        if mType =='1':
            self.signal_error.emit(mType, msg)
        else:
            #self.signal_debug.emit(self.__class__.__name__, msg)
            pass
        #print(msg)
        
    def traceback(self, err=None):
        exc_type, exc_obj, tb = sys.exc_info()
        # This function returns the current line number set in the traceback object.  
        lineno = tb.tb_lineno  
        self.signal_debug.emit(self.__class__.__name__, 
                               "%s - %s - Line: %s" % (exc_type, exc_obj, lineno))

       
class Server(iperf3):
    """ A network testing server that can start an iperf3 
    server on any given port."""
    #int: type, str: message
    signal_result = pyqtSignal(int, str)
    signal_finished = pyqtSignal(int, str)
    
    def __init__(self, host='127.0.0.1', port=5201):
        super(Server, self).__init__()
        
        self.host = host
        self.port = port
        #print(self.iperf)
        
        #Tx: 5201
        self.TxIperf = iperf3(port=self.port)
        self.TxIperf.signal_debug.connect(self.log)
        self.TxIperf.signal_error.connect(self.log)
        self.TxIperf.signal_result.connect(self.result)
        self.TxIperf.signal_finished.connect(self.finished)
        #self.TxIperf.signal_scanning.connect(self.doScanning)
        #self.TxIperf.signal_scanResult.connect(self.updateScanResult)
        self.TxIperfTh = iperfThread()
        self.TxIperf.moveToThread(self.TxIperfTh)
        self.TxIperfTh.started.connect(self.TxIperf.task)
        self.TxIperfTh.start()
        
        #Rx: 5202
        self.RxIperf = iperf3(port=self.port+1)
        self.RxIperf.signal_debug.connect(self.log)
        self.RxIperf.signal_error.connect(self.log)
        self.RxIperf.signal_result.connect(self.result)
        self.RxIperf.signal_finished.connect(self.finished)
        #self.RxIperf.signal_scanning.connect(self.doScanning)
        #self.RxIperf.signal_scanResult.connect(self.updateScanResult)
        self.RxIperfTh = iperfThread()
        self.RxIperf.moveToThread(self.RxIperfTh)
        self.RxIperfTh.started.connect(self.RxIperf.task)
        self.RxIperfTh.start()
        
    def __del__(self):
        #self.stop()
        pass
    
    def stop(self):
        #self.log(self.__class__.__name__, self.RxIperf.getPID())
        self.TxIperf.do_stop()
        self.RxIperf.do_stop()
        #self.RxIperfTh.exit(0)

    def getTxPort(self):
        return self.TxIperf.port
    
    def getRxPort(self):
        return self.RxIperf.port    
        
    @pyqtSlot(int,str)
    def result(self, iType, msg):
        self.signal_result.emit(iType, msg) #output result
        
    @pyqtSlot(str,str)
    def log(self, mType, msg):
        print("%s: %s" % (mType, msg))
        
    @pyqtSlot(int, str)
    def finished(self, iCode, msg):
        #self.log('0', "finished: %s - %s" % (iCode, msg))
        if not self.RxIperfTh is None:
            self.RxIperfTh.quit()
        self.signal_finished.emit(iCode, msg) 
        
    def isRunning(self):
        #TODO: Tx!!Rx!!
        return self.RxIperfTh.isRunning()

    
        
class Client(iperf3):

    signal_result = pyqtSignal(int, int, int, str)
    signal_finished = pyqtSignal(int, str)
    signal_error = pyqtSignal(str, str)
    signal_debug = pyqtSignal(str, str)

    def __init__(self, host='127.0.0.1', port=5201, iRow=0, iCol=0):
        super(Client, self).__init__()
        #index for report
        self.row = iRow
        self.col = iCol
        #
        self.host = host
        self.port = port
        self.isReverse = False
        #self.p = []
        
        self.tIperf = iperf3(port=self.port, isServer=False)
        self.tIperf.signal_debug.connect(self.debug)
        self.tIperf.signal_error.connect(self.error)
        self.tIperf.signal_result.connect(self.result)
        self.tIperf.signal_finished.connect(self.finished)
        #self.TxIperf.signal_scanning.connect(self.doScanning)
        #self.TxIperf.signal_scanResult.connect(self.updateScanResult)
        self.IperfTh = iperfThread()
        self.tIperf.moveToThread(self.IperfTh)
        self.IperfTh.started.connect(self.tIperf.task)
        self.IperfTh.start()
        
    def setRowCol(self, Row, Col):
        self.row = Row
        self.col = Col
    
    @pyqtSlot(str,str)
    def error(self, sType, sMsg):
        self.signal_error.emit(sType, sMsg)
        
    @pyqtSlot(str,str)
    def debug(self, sType, sMsg):
        self.signal_debug.emit(sType, sMsg)
        
    @pyqtSlot(int,str)
    def result(self, iType, msg):
        self.signal_result.emit(self.row, self.col, iType, msg) #output result

    @pyqtSlot(int, str)
    def finished(self, iCode, msg):
        self.signal_finished.emit(iCode, msg)
        
    def setClientCmd(self, sFromat='M', isUDP=False, duration=10, parallel=1, 
                     isReverse=False, iBitrate=0, sBitrateUnit='K',
                     iWindowSize=65535, sWindowSizeUnit='K', iMTU=40):
        '''iperf client command'''
        self.sCmd = [self.iperf, '-c', self.host,
                     '-p', str(self.port), '-i', '1']
        if sFromat:
            self.sCmd.append('-f')
            self.sCmd.append(sFromat)
        if isUDP:
            self.sCmd.append('-u')
            
        if duration:
            self.sCmd.append('-t')
            self.sCmd.append(str(duration))
        #TODO:  -l, --len       #[KMG]    length of buffer to read or write (default 128 KB for TCP, 8 KB for UDP)
        if parallel:
            self.sCmd.append('-P')
            self.sCmd.append(str(parallel))
            self.tIperf.iParallel = parallel
            
        if isReverse:
            self.sCmd.append('-R') #run in reverse mode (server sends, client receives)
        
        
        self.sCmd.append('-b')
        if int(iBitrate) <=0:
            self.sCmd.append(str(iBitrate))
        else:
            self.sCmd.append("%s%s" % (iBitrate, sBitrateUnit))
            
        if iWindowSize:
            self.sCmd.append('-w')
            self.sCmd.append("%s%s" % (str(iWindowSize), sWindowSizeUnit))

        if iMTU:
            self.sCmd.append('-M')
            self.sCmd.append(str(iWindowSize))
            
        #TODO: -4, --version4            only use IPv4
        #TODO: -6, --version6            only use IPv6

        #print(self.sCmd)
        self.tIperf.sCmd = self.sCmd
        #print("tIperf.sCmd: %s " % self.tIperf.sCmd)
        
    def startTest(self):
        #self.setClientCmd()
        self.tIperf.stoped = False
        self.IperfTh.start()
        pass
    '''
    #following will block main thread
    def start(self, interval=1, bReverse=False):
        command = [self.iperf, '-c', self.host,
                   '-p', str(self.port)]
        
        if interval:
            command.append('-i' + str(interval))
        if bReverse:
            command.append('-R')
            
        pipe = subprocess.Popen(command, shell=False, bufsize=1, universal_newlines=True,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        
        while True:
            data = nonblock_read(pipe.stdout)
            if data is None:
                # All data has been processed and subprocess closed stream
                pipe.wait()
                break
            elif data:
                # Some data has been read, process it
                #processData(data)
                print("data: %s" % data)
            else:
                # No data is on buffer, but subprocess has not closed stream
                #idleTask()       
                #print("wait output")
                pass
    '''
    def isRunning(self):
        st = self.tIperf.isRunning() and self.IperfTh.isRunning()
        #print("client is running: %s" % (st))
        return st
    
    def stop(self):
        #self.log(self.__class__.__name__, self.RxIperf.getPID())
        self.tIperf.do_stop()
        
# main
if __name__ == "__main__":
    a = Server('127.0.0.1')
    print("Tx port: %s" % a.getTxPort)
    print("Rx port: %s" % a.getRxPort)
    
    #
    TxC = Client('127.0.0.1')
    #TxC.start(10)

    RxC = Client('127.0.0.1', port=5202)
    #RxC.start(10, True)
    
    