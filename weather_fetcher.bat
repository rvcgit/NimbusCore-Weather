@echo off
:: --- CONFIGURATION ---
SET "APPS_DIR=C:\apps"
SET "TARGET_FOLDER=%LOCALAPPDATA%\Temp\WeatherCache"
SET "SCRIPT_NAME=weather_fetcher_X_platform.py"
:: ---------------------

:: 1. Force the script to execute out of the correct directory
cd /d "%APPS_DIR%" || (
    echo [ERROR] Could not find the apps folder at %APPS_DIR%
    pause
    exit /b
)

:loop
echo [%date% %time%] Starting automated cleanup and fetch cycle...

:: 2. Clear out the Open-Meteo cache files safely without locking
if exist "%TARGET_FOLDER%" (
    del /f /q /s "%TARGET_FOLDER%\*" >nul 2>&1
    for /d %%p in ("%TARGET_FOLDER%\*") do rmdir /s /q "%%p" >nul 2>&1
)

:: 3. Execute the Python weather script and wait for it to finish gracefully
echo [%date% %time%] Running %SCRIPT_NAME%...
python "%SCRIPT_NAME%"

:: 4. Check if Python threw an internal execution error
if %errorlevel% neq 0 (
    echo [%date% %time%] WARNING: Python script exited with error code %errorlevel%
)

:: 5. Sleep for exactly 15 minutes (900 seconds) before repeating
echo [%date% %time%] Cycle complete. Sleeping for 15 minutes...
timeout /t 900 /nobreak >nul

goto loop
