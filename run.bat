@echo off
REM Accommodation Scraper - Windows launcher
REM Usage: run.bat search "hotels in Buenos Aires"
REM        run.bat fields
REM        run.bat preview "hostels in Mendoza"

chcp 65001 >nul 2>&1

IF "%1"=="" (
    echo Accommodation Scraper - Google Places API
    echo.
    echo Uso:
    echo   run.bat search "hotels in Buenos Aires"
    echo   run.bat search "hostels in Mendoza" --min-rating 4.0
    echo   run.bat fields
    echo   run.bat preview "hotels in Cordoba"
    echo.
    echo Para mas opciones: run.bat search --help
    exit /b 0
)

REM Try Poetry first, fallback to direct Python
where poetry >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    poetry run scraper %*
) ELSE (
    python -m scraper.cli %*
)
