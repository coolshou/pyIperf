#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 19 13:39:53 2017

@author: jimmy
"""

import platform
import sys
import csv
import os
import time
import datetime
from enum import Enum
import concurrent.futures
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot, QSettings,
                          QMutex, Qt, QFileInfo, QThread)
from PyQt5.QtWidgets import (QApplication, QMainWindow,  QSystemTrayIcon,
                             QErrorMessage, QMessageBox, QAbstractItemView,
                             QTableWidgetItem, QFileDialog, QDialog,
                             QTreeWidgetItem)
from PyQt5.QtGui import (QIcon, QStandardItemModel )
from PyQt5.uic import loadUi
import random #just for test

import logging
import serial
import serial.tools.list_ports as list_ports

from pyIperf import Server, Client, iperfResult
from dlgConfig import Ui_Dialog as dlgConfig


class QtHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
    def emit(self, record):
        record = self.format(record)
        if record: XStream.stdout().write('%s\n'%record)
        # originally: XStream.stdout().write("{}\n".format(record))


logger = logging.getLogger(__name__)
handler = QtHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class XStream(QObject):
    _stdout = None
    _stderr = None
    messageWritten = pyqtSignal(str)
    def flush( self ):
        pass
    def fileno( self ):
        return -1
    def write( self, msg ):
        if ( not self.signalsBlocked() ):
            self.messageWritten.emit(msg)
    @staticmethod
    def stdout():
        if ( not XStream._stdout ):
            XStream._stdout = XStream()
            sys.stdout = XStream._stdout
        return XStream._stdout
    @staticmethod
    def stderr():
        if ( not XStream._stderr ):
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr

locker = QMutex()

class columnResult(Enum):
    colDate=0
    colPlace=colDate+1
    colDegree=colPlace+1
    colTx=colDegree+1
    colRx=colTx+1

class iperfColumn(Enum):
    colName=0
    colDirection=colName+1
    colHost=colDirection+1
    colCmd=colHost+1
    colAvg=colCmd+1
    
#a iperf worker thread to handle each running iperf
class WorkerThread(QThread):
    progressUpdated = pyqtSignal(int)
    msgUpdated = pyqtSignal(str,str)
    finished = pyqtSignal(int,str)
    updateData = pyqtSignal(int, int, str)
    
    def __init__(self, cmds, workers=1):
        QThread.__init__(self)
        self.moveToThread(self)
        self.value = 0
        self.cmds = cmds
        self.workers = workers

    def long_task(self, cmds):
        #print(cmds)
        cmd = cmds.split(",")
        row = int(cmd[0])
        #col = int(cmds[1])
        cmd = cmd[1]
        #row =r
        #col =c
        #cmd=cmds
        print("TODO %s, typ %s,  wait %s" % (row,type(row), cmd))
        time.sleep(10)
        #TODO: real iperf task
        val = random.randint(10, 1000)
        self.updateData.emit(row, 0 , str(val) )     
        return "%s" % (val)
        
    def run(self):
        #TODO TODO!!!
        # We can use a with statement to ensure threads are cleaned up promptly
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Start the load operations and mark each future with its cmd
            future_to_url = {executor.submit(self.long_task, cmd): cmd for cmd in self.cmds}
            self.msgUpdated.emit('0',"%s" % (future_to_url))
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                self.msgUpdated.emit('0',"%s: url= %s" % (datetime.datetime.now(), url))
                try:
                    data = future.result()
                except Exception as exc:
                    #self.msgUpdated.emit('1','%r generated an exception: %s' % ( url, exc))
                    self.finished.emit(-1 , '%r generated an exception: %s' % ( url, exc))
                else:
                    if data:
                        self.msgUpdated.emit('0','%r page is %d bytes' % (url, len(data)))
                        self.value += 1
                        self.progressUpdated.emit(self.value)

        self.progressUpdated.emit(100)
        self.finished.emit(0, "")
        
class MainWindow(QMainWindow):
    __VERSION__ = "20170825"
    
    def __init__(self):
        super(MainWindow, self).__init__()
        self.settings = QSettings('qperf.ini', QSettings.IniFormat)
        self.settings.setFallbacksEnabled(False)
        
        self.preventSystemShutdown = False; #when result is not saved!!
        self.stoped = False
        
        if getattr( sys, 'frozen', False ) :
            # running in a bundle
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir =''
        
        self.logFilePath = os.path.join(bundle_dir, 'log')
        if not os.path.isdir(self.logFilePath):
            os.mkdir(self.logFilePath)
            
        ui_main = os.path.join(bundle_dir, 'qperf.ui') #load UI
        self.ui_config = os.path.join(bundle_dir, 'dlgConfig.ui') #load UI
        icon_main = os.path.join(bundle_dir, 'images', 'qperf.png')
        loadUi(ui_main,self)
        self.setWindowTitle("%s(%s) - %s" % ("qperf", "pyIperf", self.__VERSION__))        
        self.setWindowIcon(QIcon(icon_main))
        #TODO: tabChart (current hide)
        #self.twResult.setTabEnabled(0,False) #enable/disable the tab
        
        #TODO: turntable: comport
        '''
        ls_comports = self.list_comports()
        self.comboComPort.addItems(ls_comports)
        ls_baudrates = self.list_baudrates()
        self.comboBaulRate.addItems(ls_baudrates)
        '''
        #setting
        self.cfgDialog = QDialog(self)
        self.cfgDialog.ui = dlgConfig()
        self.cfgDialog.ui.setupUi(self.cfgDialog)
        self.loadCfgSetting(self.cfgDialog.ui)
        self.loadSetting()        
        
        #TODO: detect current running iperf3.exe and delete it
        #init server
        self.s = Server()
        self.s.signal_result.connect(self.parserServerReult)
        self.s.signal_debug.connect(self.log)
        
        self.pbDoJobs.clicked.connect(self.doJobs)
        
        self.pbStart.clicked.connect(self.startClient)
        self.pbStop.clicked.connect(self.stopClient)
        #self.pbSave.clicked.connect(self.saveResult)
        self.pbSave.clicked.connect(self.actionSave.trigger)
        self.pbClear.clicked.connect(self.clearResult)
        #action
        self.actionAbout.triggered.connect(self.showAbout)
        self.actionSave.triggered.connect(self.saveResult)
        self.actionSave.changed.connect(self.setResultChange)
        self.actionConfig.triggered.connect(self.showConfig)
        self.tableResult.cellChanged.connect(self.tableResultChanged)
        #indexOfChecked = [self.gbProtocal.buttons()[x].isChecked() for x in range(len(self.gbProtocal.buttons()))].index(True)
        #print(indexOfChecked)
        #load setting
        self.txC = None
        self.rxC = None
        
        #dataChanged
        #self.twIperfs.dataChanged.connect(self.dataChanged)
        
    def __del__(self):
        ''' destructure     '''
        if self.s.isRunning():
            self.s.stop()
        pass

    def doJobs(self):
        #create command
        cmds=[]
        for idx in range(self.getIperfCount()):
            root = self.twIperfs.invisibleRootItem() 
            itm = root.child(idx)
            #n = itm.text(iperfColumn.colName.value)
            cmd = itm.text(iperfColumn.colCmd.value)
            #print("%s - %s" %(idx, cmd))
            cmds.append("%s , %s" %(idx, cmd))

        print(cmds)

        self.pbDoJobs.setEnabled(False)
        self.work = WorkerThread(cmds)
        #TODO: signal handle
        self.work.progressUpdated.connect(self.progressbar_change)
        self.work.msgUpdated.connect(self.log)
        self.work.updateData.connect(self.updateTWData)
        self.work.finished.connect(self.finish)
        self.work.start()

    @pyqtSlot(int)
    def progressbar_change(self, val):
        self.progressBar.setValue(val)    
        
    @pyqtSlot(int, int, str)
    def updateTWData(self, row, iType, val):
        print("%s , %s - %s" % (row, iType, val))
        #self.tableWidget.setRowCount(row+1)
        if iType==0:
            root = self.twIperfs.invisibleRootItem() 
            print("row: %s" %row)
            itm = root.child(row)
            if itm:
                itm.setText(iperfColumn.colAvg.value, val) 
            #self.tableWidget.setItem(row, iperfColumn.colAvg.value, QTableWidgetItem(val))
        else:
            print("#TODO: other type of result")
            #self.tableWidget.setItem(row, iperfColumn.colAvg.value, QTableWidgetItem(val))
            
        pass
    
    #def dataChanged(self):
        #if self.pbDoJobs.is:
            
    def getIperfCount(self):
        root = self.twIperfs.invisibleRootItem()
        child_count = root.childCount()
        #print(child_count)
        return child_count
    
    def createIperfCmd(self):
        #print("TODO: startClient")
        host = self.cfgDialog.ui.leHost.text()
        #print("leHost: %s" % host)
        port = self.cfgDialog.ui.sbPort.value()
        sFormat = self.cfgDialog.ui.comboBoxFormat.currentText()
        #print("sbPort: %s" % port)
        duration = self.cfgDialog.ui.sbDuration.value()
        #self.progressBar.setMaximum(duration+3)
        #print("sbDuration: %s" % duration)
        parallel = self.cfgDialog.ui.spParallel.value()
        #print("spParallel: %s" % parallel)
        bReverse = self.cfgDialog.ui.cbReverse.isChecked()
        #print("cbReverse: %s" % bReverse)
        if self.cfgDialog.ui.rbTCP.isChecked():
            isUDP = False
        else:
            isUDP = True
        #
        #print("TODO: sbWindowSize: %s" % self.sbWindowSize.value())
        iWindowSize = self.cfgDialog.ui.sbWindowSize.value()
        sWindowSizeUnit = self.cfgDialog.ui.comboWindowSizeUnit.currentText()
        iMTU = self.cfgDialog.ui.sbMTU.value()
        
        iBitrate = self.cfgDialog.ui.sbBitrate.value()
        sBitrateUnit = self.cfgDialog.ui.comboBitrateUnit.currentText()
        
        return "%s %s %s %s %s %s %s %s %s %s %s %s" % (host, port, sFormat, isUDP, duration, parallel, 
                bReverse, iBitrate, sBitrateUnit, iWindowSize, sWindowSizeUnit, iMTU)
    
    @pyqtSlot()
    def showConfig(self):
        #show config
        self.loadCfgSetting(self.cfgDialog.ui)
        rs = self.cfgDialog.exec_() #show module, wait use apply setting?
        if rs:
            self.pbDoJobs.setEnabled(True)
            print("OK")
            self.saveCfgSetting(self.cfgDialog.ui)
            #add a iperf item
            treeItem = QTreeWidgetItem()
            treeItem.setText(iperfColumn.colName.value, str(self.getIperfCount())) 
            if self.cfgDialog.ui.cbReverse.isChecked():
                d = "<---"
            else:
                d = "--->"
            treeItem.setText(iperfColumn.colDirection.value, d) 
            treeItem.setText(iperfColumn.colHost.value, self.cfgDialog.ui.leHost.text()) 
            #create command
            cmd = self.createIperfCmd()            
            #TODO:real iperf command!!
            treeItem.setText(iperfColumn.colCmd.value, cmd) 
            #treeItem.setText(iperfColumn.colAvg.value, self.getIperfCount()) 
            self.twIperfs.addTopLevelItem(treeItem)
        #if rs == QDialog.OK:
        #   
        #dialog.show() 
        
    @pyqtSlot()
    def showAbout(self):
        #print("showAbout")
        sVer = "Version: %s\n" % self.__VERSION__
        #if self.worker:
        #sVer = sVer + " bitcomit.py version: %s" % bitcomit.__version__
        
        QMessageBox.information(self, "About - %s" % self.windowTitle(), 
                                sVer, QMessageBox.Ok)
    
    @pyqtSlot(int,int)
    def tableResultChanged(self, iRow, iCol):
        if not self.actionSave.isEnabled():
            self.actionSave.setEnabled(True)

        if not self.pbClear.isEnabled():
            self.pbClear.setEnabled(True)
                
    @pyqtSlot()            
    def setResultChange(self):
        state = self.actionSave.isEnabled()
        self.pbSave.setEnabled(state)
        self.pbClear.setEnabled(state)
        self.preventSystemShutdown = state

    
    def list_comports(self):
        ''' return system's all serial port name in list'''
        lst = []
        for n, (portname, desc, hwid) in enumerate(sorted(list_ports.comports())):
            lst.append(portname)
            # print("portname: %s" % portname)
            # print("desc: %s" % desc)
            # print("hwid: %s" % hwid)
        return lst
    
    def list_baudrates(self):
        ''' return baudrates (9600~115200) in list'''
        lst = []
        for baudrate in serial.Serial.BAUDRATES:
            if baudrate > 4800 and baudrate < 230400:
                lst.append(str(baudrate))
                # print(baudrate)
        return lst

    def loadCfgSetting(self, dlg):
        dlg.leHost.setText(self.settings.value('Host', "127.0.0.1"))
        dlg.sbPort.setValue(int(self.settings.value('Port', 5201)))
        idx = dlg.comboBoxFormat.findText(self.settings.value('Format', 'M') , Qt.MatchFixedString)
        dlg.comboBoxFormat.setCurrentIndex(idx)
        dlg.sbDuration.setValue(int(self.settings.value('Duration', 10)))
        dlg.spParallel.setValue(int(self.settings.value('Parallel', 1)))
        dlg.cbReverse.setCheckState(int(self.settings.value('Reverse', 0)))
        
        protocal = self.settings.value('Protocal', 'TCP')
        if protocal in 'TCP':
            dlg.rbTCP.setChecked(True)
        else:
            dlg.rbUDP.setChecked(True)
        dlg.sbWindowSize.setValue(int(self.settings.value('WindowSize', 0)))
        idx = dlg.comboWindowSizeUnit.findText(self.settings.value('WindowSizeUnit', 'K') , Qt.MatchFixedString)
        dlg.comboWindowSizeUnit.setCurrentIndex(idx)
        dlg.sbMTU.setValue(int(self.settings.value('MTU', 0)))
        dlg.sbBitrate.setValue(int(self.settings.value('Bitrate', 0)))
        idx = dlg.comboBitrateUnit.findText(self.settings.value('BitrateUnit', 'K') , Qt.MatchFixedString)
        dlg.comboBitrateUnit.setCurrentIndex(idx)
        #TurnTable
        chk = self.settings.value('TurnTable', 0)
        if chk == 2:
            dlg.cbTurnTable.setChecked(True)
        else:
            dlg.cbTurnTable.setChecked(False)
        
        idx = dlg.comboComPort.findText(self.settings.value('ComPort', 'com1') , Qt.MatchFixedString)
        dlg.comboComPort.setCurrentIndex(idx)
        idx = dlg.comboBaulRate.findText(self.settings.value('BaulRate', str(115200)) , Qt.MatchFixedString)
        dlg.comboBaulRate.setCurrentIndex(idx)
        dlg.ttStart.setValue(int(self.settings.value('TurnTableStart', 0)))
        dlg.ttEnd.setValue(int(self.settings.value('TurnTableEnd', 360)))
        dlg.ttStep.setValue(int(self.settings.value('TurnTableStep', 30)))
        
        #test       
        #dlg.lePlace.setText(self.settings.value('Place', "New place"))
        #dlg.cbTx.setCheckState(int(self.settings.value('Tx', 2)))
        #dlg.cbRx.setCheckState(int(self.settings.value('Rx', 0)))
        #dlg.cbTxRx.setCheckState(int(self.settings.value('TxRx', 0)))

    def saveCfgSetting(self, dlg):
        self.settings.setValue('Host', dlg.leHost.text())
        self.settings.setValue('Port', dlg.sbPort.text())
        self.settings.setValue('Format', dlg.comboBoxFormat.currentText())
        self.settings.setValue('Duration', dlg.sbDuration.text())
        self.settings.setValue('Parallel', dlg.spParallel.text())
        self.settings.setValue('Reverse', dlg.cbReverse.checkState())
        if dlg.rbTCP.isChecked():
            protocal = 'TCP'
        else:
            protocal = 'UDP'
        self.settings.setValue('Protocal', protocal)
        #self.gbProtocal.
        self.settings.setValue('WindowSize', dlg.sbWindowSize.text())
        self.settings.setValue('WindowSizeUnit', dlg.comboWindowSizeUnit.currentText())
        self.settings.setValue('MTU', dlg.sbMTU.text())
        self.settings.setValue('Bitrate', dlg.sbBitrate.text())
        self.settings.setValue('BitrateUnit', dlg.comboBitrateUnit.currentText())
        #TurnTable
        self.settings.setValue('TurnTable', dlg.cbTurnTable.checkState())
        self.settings.setValue('ComPort', dlg.comboComPort.currentText())
        self.settings.setValue('BaulRate', dlg.comboBaulRate.currentText())
        self.settings.setValue('TurnTableStart', dlg.ttStart.text())
        self.settings.setValue('TurnTableEnd', dlg.ttEnd.text())
        self.settings.setValue('TurnTableStep', dlg.ttStep.text())
        
        #test
        #self.settings.setValue('Place', self.lePlace.text())
        #self.settings.setValue('Tx', self.cbTx.checkState())
        #self.settings.setValue('Rx', self.cbRx.checkState())
        #self.settings.setValue('TxRx', self.cbTxRx.checkState())        
    
    def loadSetting(self):
        '''
        self.leHost.setText(self.settings.value('Host', "127.0.0.1"))
        self.sbPort.setValue(int(self.settings.value('Port', 5201)))
        idx = self.comboBoxFormat.findText(self.settings.value('Format', 'M') , Qt.MatchFixedString)
        self.comboBoxFormat.setCurrentIndex(idx)
        self.sbDuration.setValue(int(self.settings.value('Duration', 10)))
        self.spParallel.setValue(int(self.settings.value('Parallel', 1)))
        self.cbReverse.setCheckState(int(self.settings.value('Reverse', 0)))
        
        protocal = self.settings.value('Protocal', 'TCP')
        if protocal in 'TCP':
            self.rbTCP.setChecked(True)
        else:
            self.rbUDP.setChecked(True)
        self.sbWindowSize.setValue(int(self.settings.value('WindowSize', 0)))
        idx = self.comboWindowSizeUnit.findText(self.settings.value('WindowSizeUnit', 'K') , Qt.MatchFixedString)
        self.comboWindowSizeUnit.setCurrentIndex(idx)
        self.sbMTU.setValue(int(self.settings.value('MTU', 0)))
        self.sbBitrate.setValue(int(self.settings.value('Bitrate', 0)))
        idx = self.comboBitrateUnit.findText(self.settings.value('BitrateUnit', 'K') , Qt.MatchFixedString)
        self.comboBitrateUnit.setCurrentIndex(idx)
        #TurnTable
        chk = self.settings.value('TurnTable', 0)
        if chk == 2:
            self.cbTurnTable.setChecked(True)
        else:
            self.cbTurnTable.setChecked(False)
        
        idx = self.comboComPort.findText(self.settings.value('ComPort', 'com1') , Qt.MatchFixedString)
        self.comboComPort.setCurrentIndex(idx)
        idx = self.comboBaulRate.findText(self.settings.value('BaulRate', str(115200)) , Qt.MatchFixedString)
        self.comboBaulRate.setCurrentIndex(idx)
        self.ttStart.setValue(int(self.settings.value('TurnTableStart', 0)))
        self.ttEnd.setValue(int(self.settings.value('TurnTableEnd', 360)))
        self.ttStep.setValue(int(self.settings.value('TurnTableStep', 30)))
        '''
        #test       
        self.lePlace.setText(self.settings.value('Place', "New place"))
        self.cbTx.setCheckState(int(self.settings.value('Tx', 2)))
        self.cbRx.setCheckState(int(self.settings.value('Rx', 0)))
        self.cbTxRx.setCheckState(int(self.settings.value('TxRx', 0)))
    
    def saveSetting(self):
        '''
        self.settings.setValue('Host', self.leHost.text())
        self.settings.setValue('Port', self.sbPort.text())
        self.settings.setValue('Format', self.comboBoxFormat.currentText())
        self.settings.setValue('Duration', self.sbDuration.text())
        self.settings.setValue('Parallel', self.spParallel.text())
        self.settings.setValue('Reverse', self.cbReverse.checkState())
        if self.rbTCP.isChecked():
            protocal = 'TCP'
        else:
            protocal = 'UDP'
        self.settings.setValue('Protocal', protocal)
        #self.gbProtocal.
        self.settings.setValue('WindowSize', self.sbWindowSize.text())
        self.settings.setValue('WindowSizeUnit', self.comboWindowSizeUnit.currentText())
        self.settings.setValue('MTU', self.sbMTU.text())
        self.settings.setValue('Bitrate', self.sbBitrate.text())
        self.settings.setValue('BitrateUnit', self.comboBitrateUnit.currentText())
        #TurnTable
        self.settings.setValue('TurnTable', self.cbTurnTable.checkState())
        self.settings.setValue('ComPort', self.comboComPort.currentText())
        self.settings.setValue('BaulRate', self.comboBaulRate.currentText())
        self.settings.setValue('TurnTableStart', self.ttStart.text())
        self.settings.setValue('TurnTableEnd', self.ttEnd.text())
        self.settings.setValue('TurnTableStep', self.ttStep.text())
        '''
        #test
        self.settings.setValue('Place', self.lePlace.text())
        self.settings.setValue('Tx', self.cbTx.checkState())
        self.settings.setValue('Rx', self.cbRx.checkState())
        self.settings.setValue('TxRx', self.cbTxRx.checkState())

    @pyqtSlot()
    def stopServer(self):
        if self.s.isRunning():
            self.s.stop()
        #v= self.s.version()
        #self.log('0', v)

    def setStop(self, bState):
        print("setStop: %s" % bState )
        self.stoped = bState
        
    @pyqtSlot(int, str)
    def parserServerReult(self, iType, msg):
        self.log(str(iType), "#TODO: parserServerReult: %s, %s" %( iType, msg))
        pass

    def updateData(self, row, col, val):
        '''update throughput value to tableResult '''
        #print("%s , %s - %s" % (row, col, val))
        self.tableResult.setRowCount(row+1)
        self.tableResult.setItem(row, col, QTableWidgetItem(val))
        itm = self.tableResult.item(row, col)
        if itm:
            self.tableResult.scrollToItem(itm, QAbstractItemView.PositionAtCenter)
        pass 
           
    @pyqtSlot(int, int, int, str)
    def parserReult(self, iRow, iCol, iType, msg):
        if ((("sender" in msg) and (iCol == columnResult.colTx.value)) or  
            (('receiver' in msg) and (iCol == columnResult.colRx.value))):
            #self.log(str(iType), "parserReult: (%s,%s) %s = %s" % (iRow, iCol, iType, msg))
            print("parserReult iType: %s" % iType)
            rs = iperfResult(iType, msg)
            self.logToFile("%s %s" %(rs.throughput , rs.throughputUnit))
            if iType>1 and rs.idx == 'SUM':
                self.updateData( iRow, iCol, "%s (%s)" % (rs.throughput , rs.throughputUnit))
            else:
                self.updateData( iRow, iCol, "%s (%s)" % (rs.throughput , rs.throughputUnit))
            
        #self.log(str(iType), "parserReult: (%s,%s) %s = %s" % (iRow, iCol, iType, msg))

    @pyqtSlot(int, str)
    def finish(self, iCode, msg):
        self.log(str(iCode), "finish: %s %s" % (iCode, msg))
        self.setRunning(False)
        pass
        #if self.txC:
        #    self.txC.stop()
        #locker.lock()
        #self.stoped = True
        #locker.unlock()
    
    def getCurrentTime(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    @pyqtSlot(str,str)
    def log(self, sType, sMsg):
        #print("log: %s = %s" % (sType, sMsg))
        if not self.teLog is None:
            self.teLog.append(sMsg)
    
    def logToFile(self, msg):
        if self.logFileName:
            f = open(self.logFileName, 'a')
            #f.writelines(msg)
            f.write(msg)
            f.close()
            
    @pyqtSlot(str,str)
    def debug(self, sType, sMsg):
        print("debug: %s = %s" % (sType, sMsg))
        if not self.teLog is None:
            self.teLog.append(sMsg)
            
    @pyqtSlot(int, int, str,str)
    def error(self, iRow, iCol, sType, sMsg):
        print("error: %s = %s" % (sType, sMsg))
        if not self.teLog is None:
            self.teLog.append(sMsg)
        self.updateData( iRow, iCol, "%s" % (sMsg))
        self.errorStoped = True
        
    def setRunning(self, bStatus):
        self.pbStart.setEnabled(not bStatus)
        self.pbStop.setEnabled(bStatus)
        self.setStop(not bStatus)
        self.actionConfig.setEnabled(not bStatus)
        self.errorStoped = not bStatus

    @pyqtSlot(bool)    
    def stopClient(self, isCheck):
        if self.txC:
            if self.txC.isRunning():
               self.txC.stop() 
               #self.stoped = True #crash!!
        if self.rxC:
            if self.rxC.isRunning():
               self.rxC.stop() 
    
    @pyqtSlot(bool)
    def startClient(self, isCheck):
        self.setRunning(True)
        #print("TODO: startClient")
        host = self.leHost.text()
        #print("leHost: %s" % host)
        port = self.sbPort.value()
        sFormat = self.comboBoxFormat.currentText()
        #print("sbPort: %s" % port)
        duration = self.sbDuration.value()
        self.progressBar.setMaximum(duration+3)
        #print("sbDuration: %s" % duration)
        parallel = self.spParallel.value()
        #print("spParallel: %s" % parallel)
        bReverse = self.cbReverse.isChecked()
        #print("cbReverse: %s" % bReverse)
        if self.rbTCP.isChecked():
            isUDP = False
        else:
            isUDP = True
        #
        #print("TODO: sbWindowSize: %s" % self.sbWindowSize.value())
        iWindowSize = self.sbWindowSize.value()
        sWindowSizeUnit = self.comboWindowSizeUnit.currentText()
        iMTU = self.sbMTU.value()
        
        iBitrate = self.sbBitrate.value()
        sBitrateUnit = self.comboBitrateUnit.currentText()

        print("TODO: TurnTable")        
        #print("cbTx: %s" % self.cbTx.isChecked())
        #print("cbRx: %s" % self.cbRx.isChecked())
        #print("cbTxRx: %s" % self.cbTxRx.isChecked())
        self.logFileName = os.path.join(self.logFilePath, "%s.log" % self.getCurrentTime())
        self.logToFile("datetime, place, degree, Tx, Rx, TxRx\n")
        
        #twResult  alweady have data, append new data.
        iRow= self.tableResult.rowCount()
        #test Tx
        #self.txC = Client(host, port, iRow, columnResult.colTx.value)
        if not self.txC:
            self.txC = Client(host, port)
            self.txC.signal_result.connect(self.parserReult)
            self.txC.signal_finished.connect(self.finish)
            self.txC.signal_error.connect(self.error)
            self.txC.signal_debug.connect(self.debug)

        if not self.txC.isRunning():
            print("tx : %s" % self.txC.isRunning())
            self.txC.startTest()
            print("check tx : %s" % self.txC.isRunning())
            
        if not self.rxC:
            self.rxC = Client(host, port)
            self.rxC.signal_result.connect(self.parserReult)
            self.rxC.signal_finished.connect(self.finish)
            self.rxC.signal_error.connect(self.error)
            self.rxC.signal_debug.connect(self.debug)
        if not self.rxC.isRunning():
            print("rx : %s" % self.rxC.isRunning())
            self.rxC.startTest()
            print("check rx : %s" % self.rxC.isRunning())
    
        #cmd = []
        for degree in range(self.ttStart.value(),self.ttEnd.value(), self.ttStep.value()):
            print("TODO: TurnTable control!! %s" % degree)
            #print("Client is running: %s" % self.txC.isRunning())
            #date
            testTime = self.getCurrentTime()
            self.updateData(iRow, columnResult.colDate.value, testTime)
            #place
            self.updateData(iRow, columnResult.colPlace.value, self.lePlace.text())
            #degree
            self.updateData(iRow, columnResult.colDegree.value, str(degree))
            self.logToFile("%s, %s, %s" %(testTime, self.lePlace.text(), str(degree)))

            if self.cbTx.isChecked(): #Tx
                iWait = 0
                try:
                    self.txC.setRowCol(iRow, columnResult.colTx.value)
                    self.txC.setTartgetHost(host, port)
                    self.txC.setClientCmd(sFormat, isUDP, duration, parallel, 
                                          bReverse, iBitrate, sBitrateUnit,
                                          iWindowSize, sWindowSizeUnit,
                                          iMTU)
                    #cmd.append([degree, iRow, columnResult.colTx.value, self.txC.sCmd])
                    
                    while iWait < duration+3 : 
                        self.progressBar.setValue(iWait)
                        time.sleep(1)
                        QApplication.processEvents() 
                        iWait = iWait + 1
                        if self.stoped or self.errorStoped:
                            break
                except:
                    print("something error!!!!!!!!!!!!!! ")
                    self.traceback()
            if self.stoped or self.errorStoped:
                break
            if self.cbRx.isChecked(): #Rx
                iWait = 0
                try:
                    self.rxC.setRowCol(iRow, columnResult.colRx.value)
                    self.rxC.setTartgetHost(host, port)
                    self.rxC.setClientCmd(sFormat, isUDP, duration, parallel,
                                          not bReverse, iBitrate, sBitrateUnit,
                                          iWindowSize, sWindowSizeUnit,
                                          iMTU)
                    #cmd.append([degree, iRow, columnResult.colTx.value, self.txC.sCmd])
                    
                    while iWait < duration+3 : 
                        self.progressBar.setValue(iWait)
                        time.sleep(1)
                        QApplication.processEvents() 
                        iWait = iWait + 1
                        if self.stoped or self.errorStoped:
                            break
                except:
                    print("something error!!!!!!!!!!!!!! ")
                    self.traceback()
            if self.stoped or self.errorStoped:
                break
            if self.cbTxRx.isChecked(): #TxRx
                iWait = 0
                try:
                    print("TODO TxRx Bi-direction")
                    
                    while iWait < duration+3 : 
                        self.progressBar.setValue(iWait)
                        time.sleep(1)
                        QApplication.processEvents() 
                        iWait = iWait + 1
                        if self.stoped or self.errorStoped:
                            break
                except:
                    print("something error!!!!!!!!!!!!!! ")
                    self.traceback()
                    
            self.logToFile("\n")
            iRow= iRow + 1
            if self.stoped or self.errorStoped:
                break
            
        print("finish")
        self.progressBar.setValue(0)
        self.setRunning(False)
        #self.setRunning(False)
    
    def clearResult(self):
        msgBox = QMessageBox()
        msgBox.setText("Warning all test result will be delete")
        msgBox.setInformativeText("Do you really want to clear all result?")
        msgBox.addButton(QMessageBox.Yes)
        msgBox.addButton(QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.No)
        ret = msgBox.exec_()
        if ret == QMessageBox.Yes:
            for i in reversed(range(self.tableResult.rowCount())):
                self.tableResult.removeRow(i)
            self.actionSave.setEnabled(False)
            
    def saveResult(self):
        filename,ext = QFileDialog.getSaveFileName(
                self, 'Save File', '', 'CSV(*.csv)')
        if filename:
            if not QFileInfo(filename).suffix():
                filename += ".csv"
            
            with open(filename, 'w') as stream:
                writer = csv.writer(stream)
                #header
                colHeaderdata = []
                for col in range(self.tableResult.columnCount()):
                    item = self.tableResult.horizontalHeaderItem(col)
                    if item is not None:
                        print(item.text())
                        colHeaderdata.append(item.text())
                    else:
                        colHeaderdata.append('')
                writer.writerow(colHeaderdata)
                #result
                for row in range(self.tableResult.rowCount()):
                    rowdata = []
                    for column in range(self.tableResult.columnCount()):
                        item = self.tableResult.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                        else:
                            rowdata.append('')
                    print("rowdata: %s" % rowdata)
                    writer.writerow(rowdata)
            stream.close()         

    def closeEvent(self, event):
        #self.stoped = True
        self.setStop(True)
        if self.s.isRunning():
            print('server still running, stop it')
            self.s.stop()
        if self.txC:
            if self.txC.isRunning():
                print('Tx client still running, stop it')
                self.txC.stop()
        if self.rxC:
            if self.rxC.isRunning():
                print('Rx client still running, stop it')
                self.rxC.stop()            
        
        self.saveSetting()            

    def traceback(self, err=None):
        exc_type, exc_obj, tb = sys.exc_info()
        # This function returns the current line number set in the traceback object.  
        lineno = tb.tb_lineno  
        self.signal_debug.emit(self.__class__.__name__, 
                               "%s - %s - Line: %s" % (exc_type, exc_obj, lineno))

# main
if __name__ == '__main__':
    app = QApplication(sys.argv)

    app.setOrganizationName("coolshou")
    app.setOrganizationDomain("coolshou.idv.tw");
    app.setApplicationName("qperf")
    #AppUserModelID
    if platform.system() == "Windows":
        import ctypes
        myappid = u'qperf.coolshou.idv.tw' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    MAINWIN = MainWindow()
    MAINWIN.show()


    sys.exit(app.exec_())