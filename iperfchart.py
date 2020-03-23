#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 16:27:27 2020

@author: jimmy
"""
import sys
import os
try:
    from PyQt5.QtCore import (pyqtSlot, pyqtSignal, QObject, QPointF)
    from PyQt5.QtWidgets import (QWidget)
    from PyQt5.uic import loadUi
    from PyQt5.QtChart import QChart, QLineSeries, QValueAxis
except ImportError as e:
    print("pip install PyQt5")
    print("%s" % e)
    raise SystemExit

class IperfChart(QWidget):
    '''UI to show iperf throughput chart '''
    # idx str, Interval-s, intetval-end, Transfer, Bitrate, Bitrate unit, Retr, Cwnd, Cwnd unit
    sig_data = pyqtSignal(str, float, float, float, float, str, int, float, str)

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

        #chart setup
        self.opt = {}
        self.opt["chart"] = self.cv_iperf.chart()
        self.opt["chart"].setAnimationOptions(QChart.SeriesAnimations);
        self.opt["x_aix"] = QValueAxis()  # 定義x軸，實例化
        self.opt["x_aix"].setRange(0.00,60.00) #設置量程
        self.opt["x_aix"].setLabelFormat("%0.2f")  #設置坐標軸坐標顯示方式，精確到小數點後兩位
        #self.opt["x_aix"].setLabelFormat("%d")  #設置坐標軸坐標顯示方式，精確到小數點後兩位
        self.opt["x_aix"].setTickCount(6)  #設置x軸有幾個量程
        self.opt["x_aix"].setMinorTickCount(0)  #設置每個單元格有幾個小的分級

        self.opt["y_aix"] = QValueAxis()  # 定義y軸，實例化
        self.opt["y_aix"].setRange(0.00,10.00) #設置量程
        self.opt["y_aix"].setLabelFormat("%0.1f")  #設置坐標軸坐標顯示方式，精確到小數點後兩位
        self.opt["y_aix"].setTickCount(6)  #設置x軸有幾個量程
        self.opt["y_aix"].setMinorTickCount(0)  #設置每個單元格有幾個小的分級

        # self.charView.chart().addSeries(self.series_1)  #添加折線
        self.opt["chart"].setAxisX(self.opt["x_aix"])
        self.opt["chart"].setAxisY(self.opt["y_aix"])
        # self.opt["chart"].createDefaultAxes() #使用默認坐標系
        #self.opt["chart"].setTitleBrush(QBrush(Qt.cyan))  # 設置標題筆刷
        self.opt["chart"].setTitle("throughput") #設置標題

        self.series = {}  # serials

        self.buttonBox.accepted.connect(self.on_accepted)
        self.buttonBox.rejected.connect(self.on_rejected)

        self.sig_data.connect(self.on_data)

    @pyqtSlot(str, float, float, float, float, str, int, float, str)
    def on_data(self, iPall, interval_s, interval_e,
                transfer, bitrate, bitrate_unit,
                Retr, Cwnd, Cwnd_unit):
        self.append_data(iPall, interval_e, bitrate)

    def append_data(self, idx, x, y):
        '''append data to serial '''
        ser = self.series.get(idx)
        if not ser:
            #serial not exist
            self.series[idx] = QLineSeries()
            self.series[idx].setName("%s" % idx)
            self.opt["chart"].addSeries(self.series[idx])  # add new serial to chart
            ser = self.series[idx]
        #ls = [QPointF(x,y)]
        print("ser:%s (%s:%s,%s)" % (ser, idx, x, y))
        # update y_aix
        if y > self.opt["y_aix"].max():
            self.opt["y_aix"].setMax(y+200)
            self.opt["y_aix"].applyNiceNumbers()
        ser.append(x, y)
        # update x_aix
        if (ser.count()> 60):
            self.opt["x_aix"].setMin(ser.count()-60);



    def on_accepted(self):
        print("on_accepted")

    def on_rejected(self):
        print("on_rejected")

    def import_data(self, filename):
        '''import iperf3 result from filename'''
        if os.path.exists(filename):
            #read file line by line
            f = open("%s" % filename, "r")
            for line in f:
                    self.parser_data(line.rstrip())
            f.close()

        else:
            print("file not exist: %s" % filename)

    def parser_data(self, line):
        if ("[" in line) and ("]" in line):
            # this suould be data we care
            if "local" in line:
                # record header data
                # print("HEADER: %s" % (line))
                #self.log("0", "HEADER: %s" % line, 4)
                pass
            elif "Interval" in line:
                # ignore header line
                #time.sleep(0.5)
                pass
            elif "sender" in line or "receiver" in line:
                #TODO average data
                pass
            else:
                # --parallel index
                # may be "SUM" or num
                iPalls = line[1:4].split()
                if type(iPalls) == list:
                    iPall = iPalls[0]
                # print("iPall: %s (%s)" % (iPall, type(iPall)))

                data = line[5:].strip()
                if "SUM" in iPall:
                    # TODO: SUM, len(5)
                    pass
                else:
                    # len 6
                    ds = data.split(" ")
                    new_ds = [x for x in ds if x]
                    if len(new_ds) == 9:
                        #print("%s: %s" % (iPall, new_ds))
                        try:
                            interval = new_ds[0]
                            tmp_ds = interval.split("-")
                            interval_s = float(tmp_ds[0])
                            interval_e = float(tmp_ds[1])
                            transfer = float(new_ds[2])
                            bitrate =  float(new_ds[4])
                            bitrate_unit =  new_ds[5]
                            Retr  = int(new_ds[6])
                            Cwnd =  float(new_ds[7])
                            Cwnd_unit =  new_ds[8]
                            #print("%s %s %s , %s %s %s, %s %s %s" % (iPall, interval_s, interval_e,
                            #                  transfer, bitrate, bitrate_unit,
                            #                   Retr, Cwnd, Cwnd_unit))
                            self.sig_data.emit(iPall, interval_s, interval_e,
                                               transfer, bitrate, bitrate_unit,
                                               Retr, Cwnd, Cwnd_unit)
                        except Exception as e:
                            print("parser_data: %s" % e)
                    else:
                        self.log("unknown format: %s" % new_ds)

                # data = "%s %s" % (curDirection, data)
                # if "SUM" != iPall:
                #     pass
                    # just notice result when iperf is running for later User
                    # eg: throughput chart
                    #self.signal_result.emit(tID, int(iPall), data)
        #         if self._parallel > 1:
        #             # TODO: handle each pair of data
        #             if "SUM" == iPall:
        #                 # only procress data when --parallel > 1
        #                 pass
        #             else:
        #                 return
        # # iperf3
        # self.parser_v3(line)
        # TODO: iperf v2

    def parser_v3(self, line):

        pass


    def log(self, msg, lv=1):
        print("%s: %s" % (self.__class__.__name__, msg))

