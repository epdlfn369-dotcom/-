@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================================
echo BinanceBot v1.0 실행 준비
echo ============================================================
echo.

python bot_healthcheck.py

if errorlevel 1 (
    echo.
    echo 자동 점검 실패로 봇 실행을 중단했습니다.
    echo 위 FAIL 항목을 확인하세요.
    echo.
    pause
    exit /b 1
)

echo.
echo 자동 점검 통과. 봇을 시작합니다.
echo 종료하려면 Ctrl+C 를 누르세요.
echo.

python paper_supervisor.py

echo.
echo BinanceBot 실행이 종료되었습니다.
pause
