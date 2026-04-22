@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

call :run_proxy %*
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="75" (
    echo .env geaendert - starte Proxy mit neuer Konfiguration neu...
    goto :restart
)

exit /b %EXITCODE%

:restart
call :run_proxy %*
set "EXITCODE=%ERRORLEVEL%"
if "%EXITCODE%"=="75" goto :restart
exit /b %EXITCODE%

:run_proxy
setlocal EnableExtensions
if exist ".env" (
    for /f "usebackq tokens=* delims=" %%L in (".env") do call :set_env "%%L"
)

set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo Python in .venv wurde nicht gefunden. Erwartet: %PYTHON_EXE%
    exit /b 1
)

"%PYTHON_EXE%" ".\mqtt-proxy.py" %*
set "EXITCODE=%ERRORLEVEL%"
endlocal & exit /b %EXITCODE%

:set_env
set "LINE=%~1"
if not defined LINE goto :eof
if "%LINE:~0,1%"=="#" goto :eof

for /f "tokens=1* delims==" %%A in ("%LINE%") do (
    set "ENV_NAME=%%~A"
    set "ENV_VALUE=%%~B"
)

if not defined ENV_NAME goto :eof
set "%ENV_NAME%=%ENV_VALUE%"
goto :eof
