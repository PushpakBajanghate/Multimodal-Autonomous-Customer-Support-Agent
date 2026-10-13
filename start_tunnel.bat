@echo off
echo ====================================================
echo  Aura Support - Instant Backend Public Tunnel
echo  Forwarding local backend (http://127.0.0.1:8000)
echo ====================================================
.\infra\cloudflared.exe tunnel --url http://127.0.0.1:8000
pause
