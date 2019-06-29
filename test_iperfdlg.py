#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 29 23:34:01 2019

@author: coolshou
"""
import sys
import signal
try:
    from PyQt5.QtWidgets import (QApplication)
#    from PyQt5.QtCore import (QCoreApplication)
except ImportError:
    print("pip install PyQt5")
    raise SystemExit

from iperfdlg import IperfClientDlg


class Application(QApplication):
    """wrapper to the QApplication """

    def event(self, event_):
        """handle event """
        return QApplication.event(self, event_)


def signal_handler(signal_, frame):
    """signal handler"""
    print('You pressed Ctrl+C!')
    sys.exit(0)


if __name__ == "__main__":
    APP = Application(sys.argv)
    # Connect your cleanup function to signal.SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    # And start a timer to call Application.event repeatedly.
    # You can change the timer parameter as you like.
    APP.startTimer(200)
    #code
    dlg = IperfClientDlg()
    dlg.exec()

    sys.exit(APP.exec_())
