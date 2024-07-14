@echo off
mitmweb --web-port 8000 --web-host 127.0.0.1 --ssl-insecure -s proxy.py -q
pause