@echo off
:: --- CONFIGURATION ---
SET "TARGET_FOLDER=%LOCALAPPDATA%\Temp\WeatherCache"
SET "PROGRAM_TO_RUN=python C:\apps\weather_fetcher_X_platform.py"
:: ---------------------

:loop
echo [%date% %time%] Cleaning up processes...

:: 1. Kill any running Python script instances that are locking the files
taskkill /f /im "python.exe" >nul 2>&1

:: 2. Wait 2 seconds for Windows to completely release the file handles
timeout /t 2 /nobreak >nul

:: 3. Wipe the folder now that the lock is gone
dir /b /a "%TARGET_FOLDER%" 2>nul | findstr "." >nul
if %errorlevel%==0 (
    del /f /q /s "%TARGET_FOLDER%\*" >nul 2>&1
    for /d %%p in ("%TARGET_FOLDER%\*") do rmdir /s /q "%%p" >nul 2>&1
)

:: 4. Run the program to repopulate the files
start /wait "" %PROGRAM_TO_RUN%

:: 5. Wait 15 minutes before repeating
timeout /t 900 /nobreak >nul

goto loop