@echo off
cd /d "%~dp0"
title Sticky Note Calendar - Docker Launcher

echo ========================================================
echo   Sticky Note Calendar - Docker Launcher
echo ========================================================
echo.
echo [1/2] Starting Docker container...
docker compose up -d

echo.
echo [2/2] Opening web browser at http://localhost:8080 ...
ping 127.0.0.1 -n 3 > nul
start http://localhost:8080

echo.
echo ========================================================
echo   Server is running at: http://localhost:8080
echo   To stop the container, run: docker compose down
echo ========================================================
echo.
pause
