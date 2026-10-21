Bat@echo off
REM ============================================
REM WeatherCache refresh loop - every 15 minutes
REM ============================================

:loop
echo [%date% %time%] Clearing WeatherCache...

REM Delete all files in WeatherCache folder
REM /Q = quiet mode, /S = include subfolders, /F = force delete
if exist "%LOCALAPPDATA%\Temp\WeatherCache\" (
    del /Q /F /S "%LOCALAPPDATA%\Temp\WeatherCache\*"
)

REM Optional: remove empty subfolders
for /d %%D in ("%LOCALAPPDATA%\Temp\WeatherCache\*") do rd /S /Q "%%D"

echo [%date% %time%] Running Python application...

REM Run your Python script
::REM Ensure Python is installed and in PATH
python "C:\apps\weather_fetcher_X_platform.py"

echo [%date% %time%] Cycle complete. Waiting 15 minutes...

REM Wait 900 seconds (15 minutes)
timeout /t 900 /nobreak >nul

goto loop

