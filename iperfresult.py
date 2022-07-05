
# -*- coding: utf-8 -*-

import datetime
import traceback
import sys

class IperfResult():
    '''class to handle iperf throughput output line'''
    # TODO:
    iKb = 1024
    iMb = iKb * 1024
    iGb = iMb * 1024
    iTb = iGb * 1024
    iPb = iTb * 1024
    iEb = iPb * 1024
    iZb = iEb * 1024
    iYb = iZb * 1024

    def __init__(self, iParallel, result):
        self.error = False
        self.errorMsg = ""

        self.reportTime = ""
        self.idx = ""
        self.measureTimeStart = 0
        self.measureTimeEnd = 0
        self.measureTimeUnit = 'sec'
        self.totalSend = ""
        self.totalSendUnit = ""
        self.throughput = ""
        self.throughputUnit = ""

        #
        self.iParallel = iParallel
        try:
            if result is not None:
                self.reportTime = datetime.datetime.now()
                if ('sender' in result) or ('receiver' in result):
                    print("This is avg: %s" % result)
                    # return None
                    rs = result.strip().split(']')
                    self.idx = rs[0].replace('[', '').strip()

                    rs = rs[1].split(' ')
                    nrs = list(filter(None, rs))
                    self.measureTimeStart = nrs[0].split('-')[0]
                    self.measureTimeEnd = nrs[0].split('-')[1]
                    self.measureTimeUnit = nrs[1].strip()

                    self.totalSend = nrs[2].strip()
                    self.totalSendUnit = nrs[3].strip()

                    self.throughput = nrs[4].strip()
                    self.throughputUnit = nrs[5].strip()
                elif ('ID') in result:
                    print("This is header: %s" % result)
                    return None
                else:
                    rs = result.strip().split('   ')

                    # print(rs[0][1:4]), idx 1,2,3... or SUM
                    self.idx = rs[0][1:4].strip()
                    # print(rs[1].split('-')[0])
                    self.measureTimeStart = rs[1].split('-')[0]
                    self.measureTimeEnd = rs[1].split('-')[1]
                    # print(rs[2])
                    self.measureTimeUnit = rs[2].strip()
                    # print(rs[3])
                    v, u = rs[3].split(" ")
                    self.totalSend = v
                    self.totalSendUnit = u
                    # print(rs[4])
                    v, u = rs[4].split(" ")
                    self.throughput = v
                    self.throughputUnit = u
                # print(rs[5].strip())
                # print(rs[6].strip())
        except Exception as err:
            print("IperfResult init: %s" % err)
            self.error = True
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            return None
            # traceback.print_exc(file=sys.stdout)

    def convertReportTime(self, sTime):
        '''convert string sTime (20170813164651) to datetime format'''
        # print(sTime[:4]) #year
        # print(sTime[4:6]) #month
        # print(sTime[6:8]) #day
        # print(sTime[8:10]) #hr
        # print(sTime[10:12]) #min
        # print(sTime[12:14]) #sec
        d = datetime.datetime(year=int(sTime[:4]),
                              month=int(sTime[4:6]),
                              day=int(sTime[6:8]),
                              hour=int(sTime[8:10]),
                              minute=int(sTime[10:12]),
                              second=int(sTime[12:14]))
        return d

    def convert_bytes(self, bytes):
        bytes = float(bytes)
        # YB: yottabyte = zettabyte * 1024
        if bytes >= self.iYb:  # 1024*1024*1024*1024*1024*1024*1024*1024
            yottabyte = bytes / self.iYb
            size = '%.2f Y' % yottabyte
        if bytes >= self.iZb:  # 1024*1024*1024*1024*1024*1024*1024
            zettabyte = bytes / self.iZb
            size = '%.2f Z' % zettabyte
        elif bytes >= self.iEb:  # 1024*1024*1024*1024*1024*1024
            exabyte = bytes / self.iEb
            size = '%.2f E' % exabyte
        elif bytes >= self.iPb:  # 1024*1024*1024*1024*1024
            petabytes = bytes / self.iPb
            size = '%.2f P' % petabytes
        elif bytes >= self.iTb:  # 1024*1024*1024*1024
            terabytes = bytes / self.iTb
            size = '%.2f T' % terabytes
        elif bytes >= self.iGb:  # 1024*1024*1024
            gigabytes = bytes / self.iGb
            size = '%.2f G' % gigabytes
        elif bytes >= self.iMb:  # 1024*1024
            megabytes = bytes / self.iMb
            size = '%.2f M' % megabytes
        elif bytes >= self.iKb:
            kilobytes = bytes / self.iKb
            size = '%.2f K' % kilobytes
        else:
            size = '%.2f byte' % bytes
        return size.split(" ")