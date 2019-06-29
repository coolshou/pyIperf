#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 29 23:01:33 2019

@author: coolshou
"""
import sys
import os
try:
    from PyQt5.QtCore import (pyqtSlot, pyqtSignal, QObject)
    from PyQt5.QtWidgets import (QWidget, QDialog)
    from PyQt5.uic import loadUi
except ImportError:
    print("pip install PyQt5")
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
        loadUi(ui, self)
        # TODO cfg parser
        self._parser_cfg(cfg)

        self.pb_ok.clicked.connect(self.slot_ok)
        self.pb_cancel.clicked.connect(self.slot_cancel)

    def _parser_cfg(self, cfg):
        '''dict iperf cfg to show on UI'''

    @pyqtSlot()
    def slot_ok(self):
        # TODO
        self.accept()

    @pyqtSlot()
    def slot_cancel(self):
        self.reject()
