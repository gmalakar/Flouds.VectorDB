@echo off
REM Clean Python cache and build artifacts, but keep .venv

echo Cleaning FloudsVector.Py project...
echo.

echo [1/8] Removing __pycache__ folders...
for /d /r . %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d" 2>nul

echo [2/8] Removing .pyc/.pyo files...
for /r . %%f in (*.pyc *.pyo) do del /f /q "%%f" 2>nul

echo [3/8] Removing test cache...
if exist .pytest_cache rd /s /q .pytest_cache 2>nul
if exist .tox rd /s /q .tox 2>nul
if exist htmlcov rd /s /q htmlcov 2>nul
if exist .coverage del /f /q .coverage 2>nul

echo [4/8] Removing build artifacts...
if exist build rd /s /q build 2>nul
if exist dist rd /s /q dist 2>nul
for /d %%d in (*.egg-info) do if exist "%%d" rd /s /q "%%d" 2>nul

echo [5/8] Removing logs...
if exist logs rd /s /q logs 2>nul
for /r . %%f in (*.log) do del /f /q "%%f" 2>nul

echo [6/8] Removing temp files...
for /r . %%f in (*.tmp *.bak *.old) do del /f /q "%%f" 2>nul

echo [7/8] Removing IDE files...
if exist .vscode\.vscode rd /s /q .vscode\.vscode 2>nul
for /r . %%f in (*.swp *.swo *~) do del /f /q "%%f" 2>nul

echo [8/8] Removing Docker build cache...
for /f "tokens=*" %%i in ('docker images -f "dangling=true" -q 2^>nul') do docker rmi %%i 2>nul

echo.
echo ✓ Clean complete! Virtual environment (.venv) preserved.
echo.
pause
