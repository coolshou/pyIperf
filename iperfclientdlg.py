#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 29 23:01:33 2019

@author: coolshou
"""
import sys
import os
try:
    from PyQt5.QtCore import (pyqtSlot, QSettings)
    from PyQt5.QtWidgets import (QDialog)
    from PyQt5.QtGui import (QIcon)
    from PyQt5.uic import loadUi
except ImportError as e:
    print("pip install PyQt5")
    print("%s" % e)
    raise SystemExit


# class IperfDlg(QWidget):
class IperfClientDlg(QDialog):
    '''UI to set iperf parameter'''

    def __init__(self, cfg=None, parent=None):
        super(IperfClientDlg, self).__init__(parent)
        if getattr(sys, 'frozen', False):
            # we are running in a |PyInstaller| bundle
            self._basedir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            self._basedir = os.path.dirname(__file__)
        ui = os.path.join(self._basedir, "iperfclientdlg.ui")
        ico = os.path.join(self._basedir, "images", "qperf.png")
        loadUi(ui, self)
        self.settings = cfg
        # TODO cfg parser
        self.load_cfg( self.settings)

        self.pb_ok.clicked.connect(self.slot_ok)
        self.pb_cancel.clicked.connect(self.slot_cancel)
        self.setWindowIcon(QIcon(ico))


    def load_cfg(self, cfg):
        '''dict iperf cfg to show on UI'''
        if type(cfg) == QSettings:
            self.settings.beginGroup("iperf")
            #iper ver self._iperf["ver"]
            ver = self.settings.value('ver', 3, type=int)
            idx = self.cbVer.findText("%s" % ver)
            if idx:
                self.cbVer.setCurrentIndex(idx)
            self.sbPort.setValue(self.settings.value('port', 5201, type=int))
            sformat = self.settings.value('format', "m")
            idx = self.cbFormat.findText(sformat)
            if idx:
                self.cbFormat.setCurrentIndex(idx)
            self.sbInterval.setValue(self.settings.value('interval', 1, type=int))
            self.leHost.setText(self.settings.value('server', "192.168.1.1"))
            self.cbReverse.setChecked(self.settings.value('reverse', False, type=bool))
            self.cbBidir.setChecked(self.settings.value('bidir', False, type=bool))
            self.cbOldIperf3.setChecked(self.settings.value('OldIperf3', False, type=bool))

            self.sbDuration.setValue(self.settings.value('duration', 90, type=int))
            protocal = self.settings.value('protocal', "TCP")
            if protocal == "TCP":
                self.rbTCP.setChecked(True)
            else:
                self.rbTCP.setChecked(False)
            self.sbParallel.setValue(self.settings.value('parallel', 1, type=int))
            self.sbWindowSize.setValue(self.settings.value('windowSize', 64, type=int))
            windowSizeUnit = self.settings.value('windowSizeUnit', "K")
            idx = self.cbWindowSizeUnit.findText(windowSizeUnit)
            if idx:
                self.cbWindowSizeUnit.setCurrentIndex(idx)
            self.sbBitrate.setValue(self.settings.value('bitrate', 0, type=int))
            bitrateUnit = self.settings.value('bitrateUnit', "K")
            idx = self.cbBitrateUnit.findText(bitrateUnit)
            if idx:
                self.cbBitrateUnit.setCurrentIndex(idx)
            self.sbMTU.setValue(self.settings.value('MTU', 1460, type=int))
            # manager server/client
            mServer = self.settings.value('mServer', False, type=bool)
            self.gb_server.setChecked(mServer)
            managerServer = self.settings.value('managerServer', "192.168.110.10")
            idx = self.cb_managerServer.findText(managerServer)
            if idx:
                self.cb_managerServer.setCurrentIndex(idx)
            managerClient = self.settings.value('managerClient', "192.168.110.20")
            idx = self.cb_managerClient.findText(managerClient)
            if idx:
                self.cb_managerClient.setCurrentIndex(idx)
            self.settings.endGroup()

    def save_cfg(self):
        if type(self.settings) == QSettings:
            self.settings.beginGroup("iperf")
            self.settings.setValue('ver', int(self.cbVer.currentText()))
            self.settings.setValue('port', self.sbPort.value())
            self.settings.setValue('format', self.cbFormat.currentText())
            self.settings.setValue('interval', self.sbInterval.value())
            self.settings.setValue('server', self.leHost.text())
            self.settings.setValue('reverse', self.cbReverse.isChecked())
            self.settings.setValue('bidir', self.cbBidir.isChecked())
            self.settings.setValue('OldIperf3', self.cbOldIperf3.isChecked())
            self.settings.setValue('duration', self.sbDuration.value())
            if self.rbTCP.isChecked():
                protocal = "TCP"
            else:
                protocal = "UDP"
            self.settings.setValue('protocal', protocal)
            self.settings.setValue('parallel', self.sbParallel.value())
            self.settings.setValue('windowSize', self.sbWindowSize.value())
            self.settings.setValue('windowSizeUnit', self.cbWindowSizeUnit.currentText())
            self.settings.setValue('bitrate', self.sbBitrate.value())
            self.settings.setValue('bitrateUnit', self.cbBitrateUnit.currentText())
            self.settings.setValue('MTU', self.sbMTU.value())
            # manager server/client
            self.settings.setValue('mServer', self.gb_server.isChecked())
            self.settings.setValue('managerServer', self.cb_managerServer.currentText())
            self.settings.setValue('managerClient', self.cb_managerClient.currentText())
            self.settings.endGroup()

    @pyqtSlot()
    def slot_ok(self):
        # TODO
        self.accept()

    @pyqtSlot()
    def slot_cancel(self):
        self.reject()
