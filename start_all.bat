@echo off
chcp 65001 > nul

cd /d "%~dp0"

echo ========================================
echo BinanceBot 실행
echo ========================================
echo.

echo [1] 가상매매 봇 실행
start "BinanceBot Runner" cmd /k py -u runner.py

timeout /t 3 /nobreak > nul

echo [2] 대시보드 실행
start "BinanceBot Dashboard" cmd /k py -m streamlit run dashboard.py

echo.
echo 봇과 대시보드를 실행했습니다.
echo 이 창은 닫아도 됩니다.
echo.

pause