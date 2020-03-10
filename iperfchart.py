#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 16:27:27 2020

@author: jimmy
"""
import sys
import os
try:
    from PyQt5.QtCore import (pyqtSlot, pyqtSignal, QObject)
    from PyQt5.QtWidgets import (QWidget)
    from PyQt5.uic import loadUi
except ImportError as e:
    print("pip install PyQt5")
    print("%s" % e)
    raise SystemExit

class IperfChart(QWidget):
    '''UI to show iperf throughput chart '''

    def __init__(self, cfg=None, parent=None):
        super(IperfChart, self).__init__(parent)
        if getattr(sys, 'frozen', False):
            # we are running in a |PyInstaller| bundle
            self._basedir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            self._basedir = os.path.dirname(__file__)
        ui = os.path.join(self._basedir, "iperfchart.ui")
        loadUi(ui, self)

        self.buttonBox.accepted.connect(self.on_accepted)
        self.buttonBox.rejected.connect(self.on_rejected)

    def on_accepted(self):
        print("on_accepted")

    def on_rejected(self):
        print("on_rejected")

if __name__ == "__main__":
    pass
