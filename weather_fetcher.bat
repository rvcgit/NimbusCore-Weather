@echo off
REM ============================================
REM WeatherCache refresh loop - every 15 minutes
REM Optimized for Elevated Background Task Execution
REM ============================================

:loop
REM Clear data quietly. >nul 2>&1 completely squashes background stream logging.
if exist "%LOCALAPPDATA%\Temp\WeatherCache\" (
    del /Q /F /S "%LOCALAPPDATA%\Temp\WeatherCache\*" >nul 2>&1
)

REM Run your lightweight python collector script
python "C:\apps\weather_air_engine.py" >nul 2>&1
:: edit path above for alternative py scripts you use

REM Sleep for 900 seconds quietly inside the loop session
timeout /t 900 /nobreak >nul

goto loop
