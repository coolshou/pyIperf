require:
	libssl-dev (openssl)
	libsctp-dev

iperf3 build with static
./configure CFLAGS="-static" CXXFLAGS="-static" LDFLAGS="-static" --enable-static --disable-shared

#build x86 on x86_64
#require x86 openssl & libsctp-dev
./configure  CC=i686-linux-gnu-gcc-7 CFLAGS="-m32 -static" CXXFLAGS="-m32 -static" LDFLAGS="-L/media/SOFT/sdc1/linux/mySystem/network/iperf/3.6/lksctp-tools-1.0.17+dfsg/src/lib/ -L/usr/lib/i386-linux-gnu -static" \
	--host=i686-linux-gnu \
	--enable-static --disable-shared

#require (add -lsctp to src/Makefile LIBS=....)
#lksctp-tools-1.0.17+dfsg
./configure  CC=i686-linux-gnu-gcc-7 \
--host=i686-linux-gnu \
--enable-static


To build iperf3 statically after running configure replace
in src/Makefile on lines 155-157 (add -all-static)

iperf3_LINK = $(LIBTOOL) $(AM_V_lt) --tag=CC $(AM_LIBTOOLFLAGS) \
        $(LIBTOOLFLAGS) --mode=link $(CCLD) $(iperf3_CFLAGS) $(CFLAGS) \
        $(iperf3_LDFLAGS) $(LDFLAGS) -o $@

with

iperf3_LINK = $(LIBTOOL) $(AM_V_lt) --tag=CC $(AM_LIBTOOLFLAGS) \
        $(LIBTOOLFLAGS) --mode=link $(CCLD) -all-static $(iperf3_CFLAGS) $(CFLAGS) \
        $(iperf3_LDFLAGS) $(LDFLAGS) -o $@

# arm-uclibc
# require: x-tools/arm-linux-uclibcgnueabi-gcc
# require libssl/libcrypto
# openssl_1.1.1f
./config --prefix=/home/jimmy/x-tools/arm-linux-uclibcgnueabi/arm-linux-uclibcgnueabi/sysroot --cross-compile-prefix=arm-linux-uclibcgnueabi- no-shared no-asm no-async
# edit Makefile, remove -m64

# config iperf3
./configure --host=arm-linux-uclibcgnueabi CFLAGS="-static" CXXFLAGS="-static" LDFLAGS="-static" --enable-static --disable-shared --enable-static-bin




#build win32 on x86_64

#build win64 on x86_64
=============================================================================



iperf2
#x64
./configure --build=x86_64-linux-gnu \
	CFLAGS=-static CXXFLAGS=-static
#build x86 on x86_64
./configure --build=i686-linux-gnu \
	CFLAGS="-m32 -static" CXXFLAGS="-m32 -static"

#build win32 on x86_64 (gcc-mingw-w64-i686)
./configure --host=i686-w64-mingw32 \
	CFLAGS="-static" CXXFLAGS="-static"

#build win64 on x86_64 (gcc-mingw-w64-x86-64)
./configure --host=x86_64-w64-mingw32 \
	CFLAGS="-static" CXXFLAGS="-static"

#arm
/configure --without-openssl --host=arm-none-linux-gnueabi CC=arm-linux-gnueabi-gcc LD=arm-linux-gnueabi-ld CXX=arm-linux-gnueabi-g++ CFLAGS=-static CXXFLAGS=-static --enable-static --disable-shared --prefix=/home/doru/Desktop/iperf3/output



######
# qiperf-1.0.apk
#
android app to run iperf2/3 in server mode

