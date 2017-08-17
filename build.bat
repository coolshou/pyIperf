@ECHO OFF
echo "python x86 must install at C:\Python35-32"
echo "python x64 must install at C:\Python35"
echo "require python x86/x64 module PyInstaller, PyQt5"
pause

echo "Build x64"
del /Q /S build
del dist\qperf_x64.exe 
C:\Python35\python.exe -m PyInstaller qperf.spec
ren dist\qperf.exe qperf_x64.exe

echo "Build x86"
del /Q /S build
del dist\qperf.exe 
C:\Python35-32\python.exe -m PyInstaller qperf.spec