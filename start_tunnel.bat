@echo off
echo ====================================================
echo  Aura Support - Instant Backend Public Tunnel
echo  Forwarding local backend (http://127.0.0.1:8000)
echo ====================================================
set PATH=C:\Users\VICTUS\AppData\Local\NodeJS;%PATH%
npx --yes localtunnel --port 8000
pause
