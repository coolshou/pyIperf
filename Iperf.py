#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 13:45:15 2017

@author: jimmy
"""
'''
    subprocrss base iperf3 python class
'''
__version__ = "20180731"

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
#import atexit
if platform.system() == 'Linux':
    import pexpect
  
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

'''
class IperfThread(QThread):
    def run(self):
        self.exec_()
'''
locker = QMutex()

class Iperf(QObject):
    '''python of iperf2/iperf3 class'''
    __VERSION__ = '20180726'
    
    signal_result = pyqtSignal(int, str)
    signal_finished = pyqtSignal(int, str)
    signal_error = pyqtSignal(str, str)
    signal_debug = pyqtSignal(str, str)
      
    default_port = 5201
    
    def __init__(self, host='', port=5201, isServer=True, iperfver=3, bTcp=True, parent=None):
        super(Iperf, self).__init__(parent)
        #iperf binary
        if platform.machine() in ['i386','i486','i586', 'i686']:
            arch='x86'
        else:
            arch=platform.machine()

        print("iperf: %s" % iperfver)
        if iperfver==3:
            iperfname="iperf3"
        else:
            iperfname="iperf"
            
        self.iperf = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  'bin', platform.system())
        if platform.system() == 'Linux':
            self.iperf = os.path.join(self.iperf, arch, '%s' % iperfname)
            
        if platform.system() == 'Windows':
            self.iperf = os.path.join(self.iperf, '%s.exe' % iperfname)
            #self.iperf = self.iperf + '.exe'
        
        #print("use iperf: %s" % self.iperf)
        if host:
            self.host = host
        self.port = port
        if bTcp:
            self.protocal=""
        else:
            self.protocal="-u"
            
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

    def setTartgetHost(self, host, port):
        self.host = host
        self.port = port    

    def enqueue_output(self, out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        print("enqueue_output:" )
        #out.close()
    
    def setServerCmd(self):
        '''iperf server command'''
        #self.sCmd = [self.iperf, '-s', '-D', 
        self.sCmd = [self.iperf, '-s', '-p', str(self.port), self.protocal]
       
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
        if platform.system() == 'Linux':
            if self.child:
                self.child.terminate(force=True)
        elif platform.system() == 'Windows':
            if self.child:
                self.child.terminate()
        self.sCmd.clear()
        locker.unlock()

    @pyqtSlot()
    def task(self):
        #pexpect way to run program, !!!!not work on windows!!!!
        # Note: This is never called directly. It is called by Qt once the
        # thread environment has been set up.
        #exec by QThread.start()
        
        self.stoped = False        
        self.exiting = False
        self.log('0',"start task")      
        self.child = None
        while not self.exiting:
            try:
                if len(self.sCmd)>0:
                    if platform.system() == 'Linux':
                        print("sCmd: %s" % (" ".join(self.sCmd)))
                        self.child = pexpect.spawn(" ".join(self.sCmd))
                        #atexit.register(self.kill_proc, self.child) #need this to kill iperf3 procress
                        while self.child.isalive():
                            QApplication.processEvents() 
                            try:
                                line = self.child.readline() #non-blocking readline
                                if line == 0:
                                    time.sleep(0.1)
                                else:
                                    #for line in child: #time out problem
                                    rs = line.rstrip().decode("utf-8")
                                    if rs:
                                        #print("signal_result: %s" % (rs))
                                        self.signal_result.emit(self.iParallel, rs) #output result
                                if self.stoped:
                                    self.signal_finished.emit(1, "signal_finished!!")
                                    break
                            except pexpect.TIMEOUT:
                                pass            
                    elif platform.system() == 'Windows':
                        #TODO: windows how to output result with realtime!!
                        # PIPE is not working!!, iperf3 will buffer it
                        print("sCmd: %s" % (" ".join(self.sCmd)))
                        #following will have extra shell to launch app
                        #self.proc = subprocess.Popen(' '.join(self.sCmd), shell=True,
                        #
                        self.child = subprocess.Popen(self.sCmd, shell=False,
                                                     bufsize=1, 
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                        #atexit.register(self.kill_proc, self.child) #need this to kill iperf3 procress
                        
                        if self.child is None:
                            #self.signal_debug.emit(self.__class__.__name__, "command error")
                            self.signal_finished.emit(-1, "command error") 
                            return -1

                        #following will block
                        #do task, wait procress finish
                        for line in iter(self.child.stdout.readline, b''):
                            QApplication.processEvents() 
                            rs = line.rstrip().decode("utf-8")
                            if rs:
                                #print("%s rs: %s" % (datetime.datetime.now(), len(rs)))
                                #print("iParallel: %s" % self.iParallel)
                                self.signal_result.emit(self.iParallel, rs) #output result
                                QApplication.processEvents() 
                            if self.stoped:
                                self.signal_finished.emit(1, "signal_finished!!")
                                break
                    else:
                        QApplication.processEvents() 
                        if self.stoped:
                            self.signal_finished.emit(1, "signal_finished!!")
                            break
                        pass
                else:
                    QApplication.processEvents() 
                    if self.stoped:
                        self.signal_finished.emit(1, "signal_finished!!")
                        break
                    self.log('0',"wait for command!!")
                    pass
            except:
                self.traceback()
                #raise
            finally:
                #self.signal_finished.emit(-1, "proc end!!") 
                #if child:
                #    if child.isalive():
                #        child.kill(1)
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
            print("kill_proc:%s" % proc)
            #if not proc.terminate(force=True):
            #    print("%s not killed" % proc)
            subprocess.call(['sudo', 'kill', str(proc.pid)])
            
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

       
class IperfServer(Iperf):
    """ A network testing server that can start an iperf3 
    server on any given port."""
    #int: type, str: message
    signal_result = pyqtSignal(int, str)
    signal_finished = pyqtSignal(int, str)
    
    def __init__(self, host='127.0.0.1', port=5201, iperfver=3, bTcp=True, parent=None):
        super(IperfServer, self).__init__(host, port, isServer=True, iperfver=iperfver, bTcp=bTcp, parent=parent)
        
        self.host = host
        self.port = port
        print("IperfServer ver: %s"%iperfver)
        self.iperfver = iperfver
        #Tx: 5201
        self.TxIperf = Iperf(port=self.port , iperfver=self.iperfver, bTcp=bTcp)
        self.TxIperf.signal_debug.connect(self.log)
        self.TxIperf.signal_error.connect(self.log)
        self.TxIperf.signal_result.connect(self.result)
        self.TxIperf.signal_finished.connect(self.finished)
        #self.TxIperf.signal_scanning.connect(self.doScanning)
        #self.TxIperf.signal_scanResult.connect(self.updateScanResult)
        #self.TxIperfTh = IperfThread()
        print("create TxIperfTh")
        self.TxIperfTh = QThread()
        self.TxIperf.moveToThread(self.TxIperfTh)
        self.TxIperfTh.started.connect(self.TxIperf.task)
        self.TxIperfTh.start()
        
        #Rx: 5202
        self.RxIperf = Iperf(port=self.port+1, iperfver=self.iperfver, bTcp=bTcp)
        self.RxIperf.signal_debug.connect(self.log)
        self.RxIperf.signal_error.connect(self.log)
        self.RxIperf.signal_result.connect(self.result)
        self.RxIperf.signal_finished.connect(self.finished)
        #self.RxIperf.signal_scanning.connect(self.doScanning)
        #self.RxIperf.signal_scanResult.connect(self.updateScanResult)
        #self.RxIperfTh = IperfThread()
        print("create RxIperfTh")
        self.RxIperfTh = QThread()
        self.RxIperf.moveToThread(self.RxIperfTh)
        self.RxIperfTh.started.connect(self.RxIperf.task)
        self.RxIperfTh.start()
        
    def stop(self):
        if self.TxIperf:
            self.TxIperf.do_stop()
        if self.RxIperf:
            self.RxIperf.do_stop()

    def getTxPort(self):
        if self.TxIperf:
            return self.TxIperf.port
        else:
            return -1
    
    def getRxPort(self):
        if self.RxIperf:
            return self.RxIperf.port    
        else:
            return -1
        
    @pyqtSlot(int,str)
    def result(self, iType, msg):
        self.signal_result.emit(iType, msg) #output result
        
    @pyqtSlot(str,str)
    def log(self, mType, msg):
        print("%s: %s" % (mType, msg))
        
    @pyqtSlot(int, str)
    def finished(self, iCode, msg):
        #self.log('0', "finished: %s - %s" % (iCode, msg))
        if not self.TxIperfTh is None:
            self.TxIperfTh.quit()
        if not self.RxIperfTh is None:
            self.RxIperfTh.quit()
        self.signal_finished.emit(iCode, msg) 
        
    def isTxRunning(self):
        if self.TxIperfTh:
            return self.TxIperfTh.isRunning()
        else:
            return False
    def isRxRunning(self):
        if self.RxIperfTh:
            return self.RxIperfTh.isRunning()
        else:
            return False
    def isRunning(self):
        return self.isTxRunning() or self.isRxRunning()

    
        
class IperfClient(Iperf):

    signal_result = pyqtSignal(int, int, int, str)
    signal_finished = pyqtSignal(int, str)
    signal_error = pyqtSignal(int, int, str, str)
    signal_debug = pyqtSignal(str, str)

    def __init__(self, host='127.0.0.1', port=5201,
                 iRow=0, iCol=0, iperfver=3, bTcp=True, parent=None):
        super(IperfClient, self).__init__( host, port, isServer=False, iperfver=iperfver, bTcp=bTcp, parent=parent)
        #index for report
        self.row = iRow
        self.col = iCol
        #
        self.host = host
        self.port = port
        self.isReverse = False
        #self.p = []
        print("IperfClient ver:%s" % iperfver)
        self.iperfver=iperfver
        
        self.tIperf = Iperf(port=self.port, isServer=False, iperfver=self.iperfver, bTcp=bTcp)
        self.tIperf.signal_debug.connect(self.debug)
        self.tIperf.signal_error.connect(self.error)
        self.tIperf.signal_result.connect(self.result)
        self.tIperf.signal_finished.connect(self.finished)
        #self.TxIperf.signal_scanning.connect(self.doScanning)
        #self.TxIperf.signal_scanResult.connect(self.updateScanResult)
        #self.IperfTh = IperfThread()
        self.IperfTh = QThread()
        self.tIperf.moveToThread(self.IperfTh)
        self.IperfTh.started.connect(self.tIperf.task)
        self.IperfTh.start()
        
    def setRowCol(self, Row, Col):
        self.row = Row
        self.col = Col
    
    @pyqtSlot(str,str)
    def error(self, sType, sMsg):
        self.signal_error.emit(self.row, self.col, sType, sMsg)
        
    @pyqtSlot(str,str)
    def debug(self, sType, sMsg):
        self.signal_debug.emit(sType, sMsg)
        
    @pyqtSlot(int,str)
    def result(self, iType, msg):
        self.signal_result.emit(self.row, self.col, iType, msg) #output result

    @pyqtSlot(int, str)
    def finished(self, iCode, msg):
        self.signal_finished.emit(iCode, msg)
        
    def setClientCmd(self, sFromat='M', isTCP=True, duration=10, parallel=1, 
                     isReverse=False, iBitrate=0, sBitrateUnit='K',
                     iWindowSize=65535, sWindowSizeUnit='K', iMTU=40):
        '''iperf client command'''
        self.sCmd = [self.iperf, '-c', self.host,
                     '-p', str(self.port), '-i', '1']
        if sFromat:
            self.sCmd.append('-f')
            self.sCmd.append(sFromat)
        if not isTCP:
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
            self.sCmd.append(str(iMTU))
            
        #TODO: -4, --version4            only use IPv4
        #TODO: -6, --version6            only use IPv6

        #print(self.sCmd)
        self.tIperf.sCmd = self.sCmd
        
    def startTest(self):
        #self.setClientCmd()
        self.tIperf.stoped = False
        self.IperfTh.start()
        pass

    def isRunning(self):
        st = self.tIperf.isRunning() and self.IperfTh.isRunning()
        #print("client is running: %s" % (st))
        return st
    
    def stop(self):
        #self.log(self.__class__.__name__, self.RxIperf.getPID())
        self.tIperf.do_stop()
        
# main
if __name__ == "__main__":
    a = IperfServer('127.0.0.1')
    print("Tx port: %s" % a.getTxPort)
    print("Rx port: %s" % a.getRxPort)
    
    #
    TxC = IperfClient('127.0.0.1')
    #TxC.start(10)

    RxC = IperfClient('127.0.0.1', port=5202)
    #RxC.start(10, True)
    
    #TODO: wait thread finish