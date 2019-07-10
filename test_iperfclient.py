#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 09:31:22 2019

@author: jimmy
"""


import sys
import signal
import time
import unittest
from Iperf import IperfClient, IPERFprotocal

try:
    # from PyQt5.QtWidgets import (QApplication)
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


def on_result(row, col, tid, iType, msg):
    print("on_result: %s,%s : (%s) %s => %s" % (row, col, tid, iType, msg))


def on_debug(tpy, msg):
    print("on_debug:(%s) %s" % (tpy, msg))


def on_error(row, col, sType, sMsg):
    print("on_error:(%s, %s) %s: %s" % (row, col, tpy, msg))

# def check_quit():
#     if ipc:
#         # print("check_quit")
#         if ipc.isRunning():
#             return 0
#     # if ipc2:
#     #     if ipc2.isRunning():
#     #         return 0
#     print("quit")
#     # TODO: can not actually quit!! why?
#     APP.quit()


class IperfClientTest(unittest.TestCase):
    '''    test case for IperfClient class '''

    def setUp(self):
        self.APP = Application(sys.argv)
        # Connect your cleanup function to signal.SIGINT
        signal.signal(signal.SIGINT, signal_handler)
        # And start a timer to call Application.event repeatedly.
        # You can change the timer parameter as you like.
        self.APP.startTimer(200)
        # test code
        # self.wl = Wlan()

    def test_get_packeterrorrate(self):
        '''get UDP packeterrorrate (PER)'''
        # MCS0
        # 'bitrate':4.23,
        # 'windowsize':64
        # MCS7
        # 'bitrate':42.25,

        # TCP
        #  ds = "{'mIPserver':'192.168.70.147', 'mIPclient':'192.168.70.11', \
        # 'server':'192.168.0.47', 'protocal':0, 'duration':10, \
        # 'parallel':5, 'reverse':1, 'bitrate':0, 'windowsize':-1, 'omit':2, \
        # 'fmtreport':'m'}"
        # UDP
        ds = "{'mIPserver':'192.168.70.147', 'mIPclient':'192.168.70.11', \
    'server':'192.168.0.47', 'protocal': %s, 'duration':20, \
    'parallel':1, 'reverse':1, 'bitrate':4.23, 'windowsize':64, 'omit':2, \
    'fmtreport':'m'}" % (IPERFprotocal.get("UDP"))

        port = 5201
        # ip = '192.168.70.147'
        ipcs = {}
        ipc = IperfClient(port, ds)
        port = ipc.get_port()
        print("ipc: %s" % port)
        ipc.signal_result.connect(on_result)
        ipc.signal_debug.connect(on_debug)
        ipc.signal_error.connect(on_error)
        # ipc.signal_finished.connect(check_quit)
        # time.sleep(1)
        ipcs[port] = ipc

        # ipc2 = IperfClient(port+1, ds)
        # port = ipc2.get_port()
        # print("ipc2: %s" % port)
        # ipc2.signal_result.connect(on_result)
        # ipc2.signal_debug.connect(on_debug)
        # ipc2.signal_finished.connect(check_quit)
        # ipcs[port] = ipc2

        for key in ipcs:
            ipc = ipcs[key]
            ipc.start()
            QCoreApplication.processEvents()

        wait = True
        while wait:
            for key in ipcs:
                ipc = ipcs[key]
                if ipc.isRunning():
                    # ip = ipc.get_server_ip()
                    # print("iperf running: %s: %s" % (ip, key))
                    continue
                time.sleep(0.5)
                QCoreApplication.processEvents()
                wait = False

            QCoreApplication.processEvents()
            time.sleep(0.5)
            # check_quit()
        # rs = ipc.get_resultdetail()
        rs = ipc.get_result()
        print("result:%s" % rs)
        rs = ipc.get_packeterrorrate()
        print("PER:%s" % rs)

    def tearDown(self):
        '''
        clean up when test finish
        '''
        del self.APP


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(IperfClientTest('test_get_packeterrorrate'))
    unittest.TextTestRunner(verbosity=2).run(suite)
