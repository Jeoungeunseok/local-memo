@echo off
chcp 65001 > nul
echo ========================================================
echo   스티커 메모 캘린더 (Sticky Note Calendar)
echo   Docker 컨테이너 실행 스크립트
echo ========================================================
echo.

echo [1/2] Docker 컨테이너 시작 중...
docker compose up -d

echo.
echo [2/2] 웹 브라우저 접속 준비 완료!
echo 접속 주소: http://localhost:8000
echo.
echo 브라우저를 자동으로 엽니다...
start http://localhost:8000

echo.
echo 컨테이너를 중지하려면 아래 명령을 실행하세요:
echo   docker compose down
echo.
pause
