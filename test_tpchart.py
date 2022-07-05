#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

try:
    from PyQt5.QtWidgets import QApplication
    # from PyQt5.QtChart import QChartView
    # from PyQt5.QtGui import QPainter
except ImportError as err:
    raise SystemExit("pip install PyQt5\n%s" % err)

from tpchart import TPChart

pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    tc = TPChart()
    tc.load()
    tc.setGeometry(100,100,1500,600)
    # cv = QChartView()
    # cv.setChart(tc)
    # cv.setRenderHint(QPainter.Antialiasing)
    # cv.setGeometry(100,100,1500,600)
    #chartDemo = MyChart()
    #chartDemo.show()
    # cv.show()
    sys.exit(app.exec_())