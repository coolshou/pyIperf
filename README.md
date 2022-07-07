# pyIperf

PyQt5 control iperf3

Require python modules

1. PyQt5
2. pyserial
3. psutil

# ui modify

pyuic5 dlgConfig.ui -o dlgConfig.py

# iperf3

 https://github.com/esnet/iperf

Notice:

```
# allow testing with buffers up to 64MB 
sudo sysctl -w net.core.rmem_max=67108864
sudo sysctl -w net.core.wmem_max=67108864
sudo sysctl -p
```

```
# increase Linux autotuning TCP buffer limit to 32MB
sudo sysctl -w net.ipv4.tcp_rmem=4096 87380 33554432
sudo sysctl -w net.ipv4.tcp_wmem=4096 87380 33554432
```
