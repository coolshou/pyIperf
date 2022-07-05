# -*- coding: utf-8 -*-
import traceback
import os
try:
    # from PyQt5.QtChart import QChart, QChartView, QLineSeries, QCategoryAxis, QValueAxis
    from PyQt5.Qt import QPen
    from PyQt5.QtCore import QPoint, Qt
    from PyQt5.QtGui import QColor
except ImportError as err:
    traceback.print_tb(err.__traceback__)
    raise SystemExit("pip install \n %s" % err)

try:
    from QCustomPlot2 import QCustomPlot, QCP
except ImportError as err:
    raise SystemExit("pip install QCustomPlot2\n%s" % err)

from iperfresult import IperfResult
from iperfparser import IperfParser

class SColor:
    T1 = QColor(100,100,100)  # dark gray
    Blue = QColor(0,0,255)
    Green = Qt.green

# class TPChart(QChart):
class TPChart(QCustomPlot):
    def __init__(self, parent=None):
        super(TPChart, self).__init__(parent)
        # legend
        #self.legend().hide()
        self._range=120 #TODO: show x range 120 sec
        # linux not compile with DEFINES += QCUSTOMPLOT_USE_OPENGL
        # print("opengl:%s" % self.openGl())
        # self.setOpenGl(True)
        # rc = self.setupOpenGl()
        # print("opengl init :%s" % rc)

        self.o_series = {}

        self.xAxis.setLabel("Time(sec)")
        self.xAxis.setRange(0.0, 120.0)
        self.yAxis.setLabel("Throughput(MBps)")
        self.yAxis.setRange(0.0, 1000.0)
        self.legend.setVisible(True) 
        ply = self.plotLayout()
        ply.insertColumn(ply.columnCount())
        ply.addElement(0,1, self.legend)
        ply.setColumnStretchFactor(1, 0.01)
        # ply.setMinimumSize(800,600)
        
            

        # auto set axes scale & label
        self.rescaleAxes()
        # set some interactive function, drag, zoom, select curve
        self.setInteractions(QCP.Interactions(QCP.iRangeDrag|QCP.iRangeZoom|QCP.iSelectPlottables))
        # customPlot.setInteraction(QCP.iRangeZoom)
        # customPlot.setInteraction(QCP.iSelectPlottables)
        # TODO: test data
        data = [
            [0, 6],
            [9, 4],
            [15, 20],
            [18, 12],
            [28, 250]
        ]
        self.add_seriesdata("Tx 0", data)

        self.show()


    def load(self, filename=None):
        # load Iperf's output file and show in chart
        f_tx = "/mnt/SOFT/pyWAT/plugins/Iperf/log/2022-06-29_111147/2022-06-29_111501_iperf_192.168.0.11←192.168.0.111.log"
        f_rx = "/mnt/SOFT/pyWAT/plugins/Iperf/log/2022-06-29_111147/2022-06-29_111759_iperf_192.168.0.11→192.168.0.111.log"
        f_tr = "/mnt/SOFT/pyWAT/plugins/Iperf/log/2022-06-29_111147/2022-06-29_112100_iperf_192.168.0.11↔192.168.0.111.log"
        if os.path.exists(f_tx):
            with open(f_tx, "r") as f:
                datas = f.readlines()
            f.close()
            iparser = IperfParser(datas)
            # for line in datas:
            #     line = line.rstrip("\n")
            #     if len(line)>0:
            #         pass
            #         # print("line: %s" % line)
            #         # rs = IperfResult(iType, line)

    def add_seriesdata(self, idx, datas):
        # idx: 
        # datas: list of QPoint(x,y)
        series = self.o_series.get(idx)
        if not series:
            series = self.addGraph()
            pen = QPen(SColor.Green)
            pen.setWidth(2)
            series.setPen (pen)
            #	setBrush()
            series.setName("%s" % idx)
            self.o_series[idx] = series
        if len(datas)>0:
            x, y = [], []
            for p in datas:
                # x.append(p.x())
                # y.append(p.y())
                x.append(p[0])
                y.append(p[1])
            series.addData(x,y)


    def clear(self):
        # remove all series
        self.removeAllSeries()