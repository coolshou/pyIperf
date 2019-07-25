#!/bin/sh


ARCH=`uname -m`

echo "Build $ARCH"
if [ -e build ]; then
    rm -rf build
fi
if [ -e dist/qperf_$ARCH ];then
    rm dist/qperf_$ARCH
fi
pyuic5 dlgConfig.ui -o dlgConfig.py

python3 -m PyInstaller qperf.spec
mv dist/qperf dist/qperf_$ARCH

#echo "Build x86"
#rm -rf build
#rm dist/qperf
#python3 -m PyInstaller qperf.spec
