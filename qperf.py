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
try:
    from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot, QSettings,
                              QMutex, Qt, QFileInfo)
    from PyQt5.QtWidgets import (QApplication, QMainWindow,
                                 QMessageBox, QAbstractItemView,
                                 QTableWidgetItem, QFileDialog, QDialog,
                                 QRadioButton)
    from PyQt5.QtGui import (QIcon)
    from PyQt5.uic import loadUi
except ImportError:
    print("pip install PyQt5")
    raise SystemExit

import logging
import serial
import serial.tools.list_ports as list_ports
# import re

from Iperf import IperfServer, IperfClient, IperfResult
from dlgConfig import Ui_Dialog as dlgConfig


class QtHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        record = self.format(record)
        if record:
            XStream.stdout().write('%s\n' % record)
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

    def flush(self):
        pass

    def fileno(self):
        return -1

    def write(self, msg):
        if (not self.signalsBlocked()):
            self.messageWritten.emit(msg)

    @staticmethod
    def stdout():
        if (not XStream._stdout):
            XStream._stdout = XStream()
            sys.stdout = XStream._stdout
        return XStream._stdout

    @staticmethod
    def stderr():
        if (not XStream._stderr):
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr


locker = QMutex()


class columnResult(Enum):
    colDate = 0
    colPlace = colDate + 1
    colDegree = colPlace + 1
    colTx = colDegree + 1
    colRx = colTx + 1


class MainWindow(QMainWindow):
    __VERSION__ = "20180907"
    signal_debug = pyqtSignal(str, str)

    def __init__(self):
        super(MainWindow, self).__init__()
        if getattr(sys, 'frozen', False):
            # we are running in a |PyInstaller| bundle
            basedir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            basedir = os.path.dirname(__file__)

        self.settings = QSettings('qperf.ini', QSettings.IniFormat)
        self.settings.setFallbacksEnabled(False)

        self.preventSystemShutdown = False  # when result is not saved!!
        self.stoped = False

        self.logFilePath = os.path.join(basedir, 'log')
        if not os.path.isdir(self.logFilePath):
            os.mkdir(self.logFilePath)

        icon_main = os.path.join(basedir, 'images', 'qperf.png')
        # load UI
        loadUi(os.path.join(basedir, 'qperf.ui'), self)
        self.setWindowTitle("%s(%s) - %s" % ("qperf", "pyIperf",
                                             self.__VERSION__))
        self.setWindowIcon(QIcon(icon_main))
        # TODO: tabChart (current hide)
        # self.twResult.setTabEnabled(0,False) #enable/disable the tab

        # comport
        ls_comports = self.list_comports()
        self.comboComPort.addItems(ls_comports)
        ls_baudrates = self.list_baudrates()
        self.comboBaulRate.addItems(ls_baudrates)
        # setting
        self.loadSetting()

        self.rbIperf2.toggled.connect(lambda:
                                      self.setIperfVersion(self.rbIperf2))
        self.rbIperf3.toggled.connect(lambda:
                                      self.setIperfVersion(self.rbIperf3))

        self.pbStart.clicked.connect(self.startClient)
        self.pbStop.clicked.connect(self.stopClient)
        # self.pbSave.clicked.connect(self.saveResult)
        self.pbSave.clicked.connect(self.actionSave.trigger)
        self.pbClear.clicked.connect(self.clearResult)
        # action
        self.actionAbout.triggered.connect(self.showAbout)
        self.actionSave.triggered.connect(self.saveResult)
        self.actionSave.changed.connect(self.setResultChange)
        self.actionConfig.triggered.connect(self.showConfig)
        self.tableResult.cellChanged.connect(self.tableResultChanged)
        # indexOfChecked = [self.gbProtocal.buttons()[x].isChecked() for x in range(len(self.gbProtocal.buttons()))].index(True)
        # print(indexOfChecked)
        # load setting
        self.s = None
        self.txC = None
        self.rxC = None

    def __del__(self):
        ''' destructure     '''
        if self.s:
            if self.s.isRunning():
                self.s.stop()

    @pyqtSlot(QRadioButton)
    def setIperfVersion(self, b):
        if b.text() == "iperf 2":
            port = 5001
        elif b.text() == "iperf 3":
            port = 5201

        self.sbPort.setValue(port)
        # self.gbAPConsole.setEnabled(bStat)
        # self.gbAPTelnet.setEnabled(not bStat)

    @pyqtSlot()
    def showConfig(self):
        # show config
        dialog = QDialog()
        dialog.ui = dlgConfig()
        dialog.ui.setupUi(dialog)
        dialog.exec_()
        dialog.show()  # show module, wait use apply setting?

    @pyqtSlot()
    def showAbout(self):
        # print("showAbout")
        sVer = "Version: %s\n" % self.__VERSION__
        # if self.worker:
        # sVer = sVer + " bitcomit.py version: %s" % bitcomit.__version__

        QMessageBox.information(self, "About - %s" % self.windowTitle(),
                                sVer, QMessageBox.Ok)

    @pyqtSlot(int, int)
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

    def loadSetting(self):
        ver = self.settings.value('IperfVersion', 3, type=int)
        if ver == 2:
            self.rbIperf2.setChecked(True)
        if ver == 3:
            self.rbIperf3.setChecked(True)

        self.leHost.setText(self.settings.value('Host', "127.0.0.1"))
        self.sbPort.setValue(int(self.settings.value('Port', 5201)))
        idx = self.comboBoxFormat.findText(self.settings.value('Format', 'M'),
                                           Qt.MatchFixedString)
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
        wsunit = self.settings.value('WindowSizeUnit', 'K')
        idx = self.comboWindowSizeUnit.findText(wsunit, Qt.MatchFixedString)
        self.comboWindowSizeUnit.setCurrentIndex(idx)
        self.sbMTU.setValue(int(self.settings.value('MTU', 0)))
        self.sbBitrate.setValue(int(self.settings.value('Bitrate', 0)))
        brunit = self.settings.value('BitrateUnit', 'K')
        idx = self.comboBitrateUnit.findText(brunit, Qt.MatchFixedString)
        self.comboBitrateUnit.setCurrentIndex(idx)
        # TurnTable
        chk = self.settings.value('TurnTable', 0)
        if chk == 2:
            self.cbTurnTable.setChecked(True)
        else:
            self.cbTurnTable.setChecked(False)

        idx = self.comboComPort.findText(self.settings.value('ComPort',
                                                             'com1'),
                                         Qt.MatchFixedString)
        self.comboComPort.setCurrentIndex(idx)
        idx = self.comboBaulRate.findText(self.settings.value('BaulRate',
                                                              str(115200)),
                                          Qt.MatchFixedString)
        self.comboBaulRate.setCurrentIndex(idx)
        self.ttStart.setValue(int(self.settings.value('TurnTableStart', 0)))
        self.ttEnd.setValue(int(self.settings.value('TurnTableEnd', 360)))
        self.ttStep.setValue(int(self.settings.value('TurnTableStep', 30)))

        # test
        self.lePlace.setText(self.settings.value('Place', "New place"))
        self.cbTx.setCheckState(int(self.settings.value('Tx', 2)))
        self.cbRx.setCheckState(int(self.settings.value('Rx', 0)))
        self.cbTxRx.setCheckState(int(self.settings.value('TxRx', 0)))

    def saveSetting(self):

        if self.rbIperf2.isChecked():
            ver = 2
        elif self.rbIperf3.isChecked():
            ver = 3
        self.settings.setValue('IperfVersion', ver)

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
        # self.gbProtocal.
        self.settings.setValue('WindowSize', self.sbWindowSize.text())
        self.settings.setValue('WindowSizeUnit',
                               self.comboWindowSizeUnit.currentText())
        self.settings.setValue('MTU', self.sbMTU.text())
        self.settings.setValue('Bitrate', self.sbBitrate.text())
        self.settings.setValue('BitrateUnit',
                               self.comboBitrateUnit.currentText())
        # TurnTable
        self.settings.setValue('TurnTable', self.cbTurnTable.checkState())
        self.settings.setValue('ComPort', self.comboComPort.currentText())
        self.settings.setValue('BaulRate', self.comboBaulRate.currentText())
        self.settings.setValue('TurnTableStart', self.ttStart.text())
        self.settings.setValue('TurnTableEnd', self.ttEnd.text())
        self.settings.setValue('TurnTableStep', self.ttStep.text())

        # test
        self.settings.setValue('Place', self.lePlace.text())
        self.settings.setValue('Tx', self.cbTx.checkState())
        self.settings.setValue('Rx', self.cbRx.checkState())
        self.settings.setValue('TxRx', self.cbTxRx.checkState())

    @pyqtSlot()
    def stopServer(self):
        if self.s.isRunning():
            self.s.stop()
        # v= self.s.version()
        # self.log('0', v)

    def setStop(self, bState):
        print("setStop: %s" % bState)
        self.stoped = bState

    @pyqtSlot(int, str)
    def parserServerReult(self, iType, msg):
        self.log(str(iType),
                 "#TODO: parserServerReult: %s, %s" % (iType, msg))
        pass

    def updateData(self, row, col, val):
        '''update throughput value to tableResult '''
        # print("%s , %s - %s" % (row, col, val))
        self.tableResult.setRowCount(row+1)
        self.tableResult.setItem(row, col, QTableWidgetItem(val))
        itm = self.tableResult.item(row, col)
        if itm:
            self.tableResult.scrollToItem(itm,
                                          QAbstractItemView.PositionAtCenter)
        pass

    @pyqtSlot(int, int, int, str)
    def parserReult(self, iRow, iCol, iType, msg):
        print("parserReult: %s, %s, %s, %s" % (iRow, iCol, iType, msg))
        if self.rbIperf3.isChecked():
            # iperf v3 format
            if ((("sender" in msg) and (iCol == columnResult.colTx.value)) or
                (('receiver' in msg) and (iCol == columnResult.colRx.value))):
                print("parserReult iType: %s" % iType)
                rs = IperfResult(iType, msg)
                self.logToFile("%s %s" % (rs.throughput, rs.throughputUnit))
                if iType > 1 and rs.idx == 'SUM':
                    self.updateData(iRow, iCol,
                                    "%s (%s)" % (rs.throughput,
                                                 rs.throughputUnit))
                else:
                    self.updateData(iRow, iCol,
                                    "%s (%s)" % (rs.throughput,
                                                 rs.throughputUnit))
        elif self.rbIperf2.isChecked():
            # iperf v2 format
            # [  3]  0.0-10.0 sec  1126 MBytes   945 Mbits/sec
            duration = self.sbDuration.value()
            r = msg.split(" ")
            r = list(filter(None, r))  # fastest
            if len(r) == 8:
                f = r[2].split("-")
                # print("%s %s" %(f[0],f[1]))
                if float(f[0]) == 0.0 and float(f[1]) >= float(duration):
                    # print("%s %s" % (r[6], r[7]))
                    self.updateData(iRow, iCol, "%s (%s)" % (r[6], r[7]))
        else:
            print("#TODO: unknown iperf version!!")
            pass

    @pyqtSlot(int, str)
    def finish(self, iCode, msg):
        self.log(str(iCode), "finish: %s %s" % (iCode, msg))
        self.setRunning(False)
        pass
        # if self.txC:
        #    self.txC.stop()
        # locker.lock()
        # self.stoped = True
        # locker.unlock()

    def getCurrentTime(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")

    @pyqtSlot(str, str)
    def log(self, sType, sMsg):
        # print("log: %s = %s" % (sType, sMsg))
        if self.teLog is not None:
            self.teLog.append(sMsg)

    def logToFile(self, msg):
        if self.logFileName:
            f = open(self.logFileName, 'a')
            # f.writelines(msg)
            f.write(msg)
            f.close()

    @pyqtSlot(str, str)
    def debug(self, sType, sMsg):
        print("debug: %s = %s" % (sType, sMsg))
        if self.teLog is not None:
            self.teLog.append(sMsg)

    @pyqtSlot(int, int, str, str)
    def error(self, iRow, iCol, sType, sMsg):
        print("error: %s = %s" % (sType, sMsg))
        if self.teLog is not None:
            self.teLog.append(sMsg)
        self.updateData(iRow, iCol, "%s" % (sMsg))
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
                # self.stoped = True #crash!!
        if self.rxC:
            if self.rxC.isRunning():
                self.rxC.stop()

    @pyqtSlot(bool)
    def startClient(self, isCheck):
        self.setRunning(True)
        # print("TODO: startClient")
        if self.rbIperf3.isChecked():
            ver = 3
        elif self.rbIperf2.isChecked():
            ver = 2
        host = self.leHost.text()
        # print("leHost: %s" % host)
        port = self.sbPort.value()
        sFormat = self.comboBoxFormat.currentText()
        # print("sbPort: %s" % port)
        duration = self.sbDuration.value()
        self.progressBar.setMaximum(duration+3)
        # print("sbDuration: %s" % duration)
        parallel = self.spParallel.value()
        # print("spParallel: %s" % parallel)
        bReverse = self.cbReverse.isChecked()
        # print("cbReverse: %s" % bReverse)
        if self.rbTCP.isChecked():
            isTCP = True
        else:
            isTCP = False
        #
        # print("TODO: sbWindowSize: %s" % self.sbWindowSize.value())
        iWindowSize = self.sbWindowSize.value()
        sWindowSizeUnit = self.comboWindowSizeUnit.currentText()
        iMTU = self.sbMTU.value()

        iBitrate = self.sbBitrate.value()
        sBitrateUnit = self.comboBitrateUnit.currentText()

        print("TODO: TurnTable")
        # print("cbTx: %s" % self.cbTx.isChecked())
        # print("cbRx: %s" % self.cbRx.isChecked())
        # print("cbTxRx: %s" % self.cbTxRx.isChecked())
        self.logFileName = os.path.join(self.logFilePath,
                                        "%s.log" % self.getCurrentTime())
        self.logToFile("datetime, place, degree, Tx, Rx, TxRx\n")

        # TODO: iperf server? or other place
        ds = "{'mIPserver':'192.168.70.147', 'mIPclient':'192.168.70.11', \
    'server':'%s', 'protocal': %s, 'duration':20, \
    'parallel':1, 'reverse':0, \
    'bitrate':4.23, 'unit_bitrate':'M', \
    'windowsize':64, 'omit':2, \
    'fmtreport':'m'}" % (host)

        self.s = IperfServer(port=port, iperfver=ver)
        self.s.signal_result.connect(self.parserServerReult)
        self.s.signal_debug.connect(self.log)

        # twResult  alweady have data, append new data.
        iRow = self.tableResult.rowCount()
        # test Tx
        # self.txC = Client(host, port, iRow, columnResult.colTx.value)
        if not self.txC:
            print("txC: %s" % ver)
            self.txC = IperfClient(port, ds, iperfver=ver)
            self.txC.signal_result.connect(self.parserReult)
            self.txC.signal_finished.connect(self.finish)
            self.txC.signal_error.connect(self.error)
            self.txC.signal_debug.connect(self.debug)
        if not self.txC.isRunning():
            print("tx : %s" % self.txC.isRunning())
            self.txC.startTest()
            print("check tx : %s" % self.txC.isRunning())

        if not self.rxC:
            print("rxC: %s" % ver)
            self.rxC = IperfClient(port, ds, iperfver=ver)
            self.rxC.signal_result.connect(self.parserReult)
            self.rxC.signal_finished.connect(self.finish)
            self.rxC.signal_error.connect(self.error)
            self.rxC.signal_debug.connect(self.debug)
        if not self.rxC.isRunning():
            print("rx : %s" % self.rxC.isRunning())
            self.rxC.startTest()
            print("check rx : %s" % self.rxC.isRunning())

        # cmd = []
        for degree in range(self.ttStart.value(), self.ttEnd.value(),
                            self.ttStep.value()):
            print("TODO: TurnTable control!! %s" % degree)
            # print("Client is running: %s" % self.txC.isRunning())
            # date
            testTime = self.getCurrentTime()
            self.updateData(iRow, columnResult.colDate.value, testTime)
            # place
            self.updateData(iRow, columnResult.colPlace.value,
                            self.lePlace.text())
            # degree
            self.updateData(iRow, columnResult.colDegree.value, str(degree))
            self.logToFile("%s, %s, %s" % (testTime,
                                           self.lePlace.text(), str(degree)))

            if self.cbTx.isChecked():  # Tx
                iWait = 0
                try:
                    self.txC.setRowCol(iRow, columnResult.colTx.value)
                    self.txC.setTartgetHost(host, port)
                    self.txC.setClientCmd(sFormat, isTCP, duration, parallel,
                                          bReverse, iBitrate, sBitrateUnit,
                                          iWindowSize, sWindowSizeUnit,
                                          iMTU)
                    while iWait < duration + 3:
                        self.progressBar.setValue(iWait)
                        time.sleep(1)
                        QApplication.processEvents()
                        iWait = iWait + 1
                        if self.stoped or self.errorStoped:
                            break
                except Exception as e:
                    print("something error!!!!!!!!!!!!!! %s" % e)
                    self.traceback()
            if self.stoped or self.errorStoped:
                break
            if self.cbRx.isChecked():  # Rx
                iWait = 0
                try:
                    self.rxC.setRowCol(iRow, columnResult.colRx.value)
                    self.rxC.setTartgetHost(host, port)
                    self.rxC.setClientCmd(sFormat, isTCP, duration, parallel,
                                          not bReverse, iBitrate, sBitrateUnit,
                                          iWindowSize, sWindowSizeUnit,
                                          iMTU)

                    while iWait < duration + 3:
                        self.progressBar.setValue(iWait)
                        time.sleep(1)
                        QApplication.processEvents()
                        iWait = iWait + 1
                        if self.stoped or self.errorStoped:
                            break
                except Exception as e:
                    print("something error!!!!!!!!!!!!!! %s" % e)
                    self.traceback()
            if self.stoped or self.errorStoped:
                break
            if self.cbTxRx.isChecked():  # TxRx
                iWait = 0
                try:
                    print("TODO TxRx Bi-direction")

                    while iWait < duration + 3:
                        self.progressBar.setValue(iWait)
                        time.sleep(1)
                        QApplication.processEvents()
                        iWait = iWait + 1
                        if self.stoped or self.errorStoped:
                            break
                except Exception as e:
                    print("something error!!!!!!!!!!!!!! %s" % e)
                    self.traceback()

            self.logToFile("\n")
            iRow = iRow + 1
            if self.stoped or self.errorStoped:
                break

        print("finish")
        self.progressBar.setValue(0)
        self.setRunning(False)
        # self.setRunning(False)

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
        filename, ext = QFileDialog.getSaveFileName(
                    self, 'Save File', '', 'CSV(*.csv)')
        if filename:
            if not QFileInfo(filename).suffix():
                filename += ".csv"

            with open(filename, 'w') as stream:
                writer = csv.writer(stream)
                # header
                colHeaderdata = []
                for col in range(self.tableResult.columnCount()):
                    item = self.tableResult.horizontalHeaderItem(col)
                    if item is not None:
                        print(item.text())
                        colHeaderdata.append(item.text())
                    else:
                        colHeaderdata.append('')
                writer.writerow(colHeaderdata)
                # result
                for row in range(self.tableResult.rowCount()):
                    rowdata = []
                    for column in range(self.tableResult.columnCount()):
                        item = self.tableResult.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                        else:
                            rowdata.append('')
                    print("rowdata: %s" % rowdata)
                    writer.writeronotw(rowdata)
            stream.close()

    def closeEvent(self, event):
        # self.stoped = True
        self.setStop(True)
        if self.s:
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
        # This function returns the current line number
        # set in the traceback object.
        lineno = tb.tb_lineno
        self.signal_debug.emit(self.__class__.__name__,
                               "%s - %s - Line: %s" % (exc_type,
                                                       exc_obj, lineno))


# main
if __name__ == '__main__':
    app = QApplication(sys.argv)

    app.setOrganizationName("coolshou")
    app.setOrganizationDomain("coolshou.idv.tw")
    app.setApplicationName("qperf")
    # AppUserModelID
    if platform.system() == "Windows":
        import ctypes
        myappid = u'qperf.coolshou.idv.tw'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    MAINWIN = MainWindow()
    MAINWIN.show()

    sys.exit(app.exec_())
