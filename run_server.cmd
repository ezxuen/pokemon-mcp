@echo off
setlocal enabledelayedexpansion

rem === go to repo dir
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

rem === optional: set env 
set "DATABASE_PATH=%SCRIPT_DIR%data\pokemon.db"
set "CSV_CACHE_DIR=%SCRIPT_DIR%data\csv_cache"

rem === pick python
set "PYEXE=%SCRIPT_DIR%venv\Scripts\python.exe"
if exist "%PYEXE%" (
  echo [launcher] using venv python: "%PYEXE%" 1>&2
) else (
  for %%P in (py.exe python.exe) do (
    where %%P >nul 2>&1 && (set "PYEXE=%%P" & goto :foundpy)
  )
  echo [launcher] ERROR: Python not found. 1>&2
  popd & exit /b 1
)
:foundpy

rem === choose entrypoint
if exist "%SCRIPT_DIR%server.py" (
  set "ENTRY1=-m" & set "ENTRY2=server"
) else (
  echo [launcher] ERROR: server.py not found. 1>&2
  popd & exit /b 1
)

rem === run
"%PYEXE%" %ENTRY1% %ENTRY2%
set "EC=%ERRORLEVEL%"
popd
exit /b %EC%
