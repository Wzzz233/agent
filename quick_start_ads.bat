@echo off
REM Quick Start Script for ADS Agent Testing
REM This script helps you start all necessary components

echo ========================================
echo ADS Agent Quick Start
echo ========================================
echo.

echo Step 1: Check if ADS Socket Server is running...
echo.
echo Please make sure you have run this in ADS Python Console:
echo   exec(open("C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/boot_standalone.py").read())
echo.
pause

echo.
echo Step 2: Starting Agent...
echo.
start "ADS Agent" cmd /k "cd /d %~dp0 && python start_agent.py"

timeout /t 5

echo.
echo Step 3: Agent should be running at http://localhost:8000
echo.
echo You can now:
echo   1. Run test script: python test_agent_ads.py
echo   2. Open web UI: http://localhost:3000 (if frontend is running)
echo   3. Send requests to API: http://localhost:8000/api/v1/agent/chat
echo.
echo ========================================
echo Quick Start Complete!
echo ========================================
echo.
pause
