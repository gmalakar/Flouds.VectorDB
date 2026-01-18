@echo off
setlocal enabledelayedexpansion

:: Set constants
set "NETWORK_NAME=milvus_network"
set "MILVUS_NAME=milvus-standalone"
set "ATTU_NAME=attu-instance"

:: Ensure network exists
docker network ls | findstr /C:"%NETWORK_NAME%" >nul
if %errorlevel% neq 0 (
    echo Creating network: %NETWORK_NAME%
    docker network create %NETWORK_NAME%
) else (
    echo Network %NETWORK_NAME% already exists.
)

:: Check if Milvus container is running
docker inspect -f "{{.State.Running}}" %MILVUS_NAME% 2>nul | findstr /C:"true" >nul
if %errorlevel% neq 0 (
    echo ERROR: Milvus container "%MILVUS_NAME%" is not running.
    echo Please start Milvus before launching ATTU.
    exit /b 1
)

:: Check if ATTU container exists
docker ps -a --format "{{.Names}}" | findstr /C:"%ATTU_NAME%" >nul
if %errorlevel% equ 0 (
    echo Stopping and removing existing ATTU container: %ATTU_NAME%
    docker stop %ATTU_NAME% >nul
    docker rm %ATTU_NAME% >nul
)

:: Run ATTU container
echo Starting ATTU container...
docker run -d ^
    --network %NETWORK_NAME% ^
    --name %ATTU_NAME% ^
    -p 8000:3000 ^
    -e MILVUS_URL=%MILVUS_NAME% ^
    zilliz/attu:latest >nul

:: Wait for ATTU container to be running
echo Waiting for ATTU container to be live...
set /a retries=10
:wait_loop
docker inspect -f "{{.State.Running}}" %ATTU_NAME% 2>nul | findstr /C:"true" >nul
if %errorlevel% equ 0 (
    echo ATTU container is running.
    goto end
)
set /a retries-=1
if !retries! leq 0 (
    echo ERROR: ATTU container failed to start.
    exit /b 1
)
timeout /t 2 >nul
goto wait_loop

:end
echo Done.
