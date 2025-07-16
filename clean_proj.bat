@echo off
REM Clean Python cache and build artifacts, but keep .venv

echo Removing __pycache__ folders...
for /d /r . %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d"

echo Removing .pyc files...
for /r . %%f in (*.pyc) do del /f /q "%%f"

echo Removing pytest cache...
if exist .pytest_cache rd /s /q .pytest_cache

echo Removing pip cache...
if exist .pip_cache rd /s /q .pip_cache

echo Removing build.log...
if exist build.log del /f /q build.log

echo Removing logs folder...
if exist logs rd /s /q logs

echo Removing node_modules...
if exist node_modules rd /s /q node_modules


echo Clean complete! .venv was not touched.
pause