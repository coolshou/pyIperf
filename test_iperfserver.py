#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 08:58:43 2019

@author: jimmy
"""
import sys
import signal
import time
from Iperf import IperfServer

try:
    from PyQt5.QtWidgets import (QApplication)
    from PyQt5.QtCore import (QCoreApplication)
except ImportError:
    print("pip install PyQt5")
    raise SystemExit


class Application(QCoreApplication):
    """wrapper to the QApplication """

    def event(self, event_):
        """handle event """
        return QCoreApplication.event(self, event_)


def signal_handler(signal_, frame):
    """signal handler"""
    print('You pressed Ctrl+C!')
    sys.exit(0)


def check_quit():
    if not ips.isRunning() and not ips2.isRunning():
        APP.quit()


if __name__ == '__main__':
    APP = Application(sys.argv)
    # Connect your cleanup function to signal.SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    # And start a timer to call Application.event repeatedly.
    # You can change the timer parameter as you like.
    APP.startTimer(200)

    ips = IperfServer()  # default port 5201 for iperf3
    port = ips.get_port()
    ips2 = IperfServer(port=port+1, bTcp=False)
    # ips = IperfServer(port=60000)
    ips.signal_finished.connect(check_quit)
    if ips.isRunning():
        print("iperf runs on port %s" % ips.get_port())
    if ips2.isRunning():
        print("iperf runs on port %s" % ips2.get_port())
    # time.sleep(10)
    # ips.stop()
    sys.exit(APP.exec_())
