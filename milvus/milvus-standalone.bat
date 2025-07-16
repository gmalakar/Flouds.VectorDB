@echo off
setlocal enabledelayedexpansion

:: Usage: milvus-standalone.bat [start|stop|restart|delete] [config-path] [data-root-path]

:: Set command, config path, and data root path
set "COMMAND=%~1"
set "CONFIG_PATH=%~2"
set "DATA_PATH=%~3"

:: Validate command parameter
if "%COMMAND%"=="" (
    call :show_usage "Missing command"
    exit /b 1
)

:: Validate required parameters based on command
if /i "%COMMAND%"=="start" (
    call :validate_paths
) else if /i "%COMMAND%"=="restart" (
    call :validate_paths
) else if /i "%COMMAND%"=="delete" (
    call :validate_paths
) else if /i "%COMMAND%"=="stop" (
    if "%CONFIG_PATH%"=="" (
        call :show_usage "You must provide a config path for the 'stop' command"
        exit /b 1
    )
) else (
    call :show_usage "Unknown command: %COMMAND%"
    exit /b 1
)

:: Set constants
set "NETWORK_NAME=milvus_network"
set "MILVUS_NAME=milvus-standalone"
set "ETCD_CONFIG=%CONFIG_PATH:/=\%\embedEtcd.yaml"
set "USER_CONFIG=%CONFIG_PATH:/=\%\user.yaml"
set "VOLUME_PATH=%DATA_PATH:/=\%\volumes\milvus"

:: Command routing
if /i "%COMMAND%"=="restart" (
    call :stop
    call :start
) else if /i "%COMMAND%"=="start" (
    call :start
) else if /i "%COMMAND%"=="stop" (
    call :stop
) else if /i "%COMMAND%"=="delete" (
    call :delete
)
exit /b 0

:: -------------------------------
:show_usage
echo  ERROR: %~1
echo Usage: milvus-standalone.bat start^|stop^|restart^|delete [config-path] [data-root-path]
echo   - start/restart/delete: require both config-path and data-root-path
echo   - stop: requires only config-path
goto :eof

:: -------------------------------
:validate_paths
if "%CONFIG_PATH%"=="" (
    call :show_usage "You must provide a config path as the second parameter"
    exit /b 1
)
if "%DATA_PATH%"=="" (
    call :show_usage "You must provide a data path as the third parameter"
    exit /b 1
)
goto :eof

:: -------------------------------
:create_configs
:: Create config directory if it doesn't exist
if not exist "%CONFIG_PATH%" (
    echo  Creating config directory: %CONFIG_PATH%
    mkdir "%CONFIG_PATH%" 2>nul
    if !errorlevel! neq 0 (
        echo  ERROR: Failed to create config directory
        exit /b 1
    )
)

:: Create etcd config only if it doesn't exist
if not exist "%ETCD_CONFIG%" (
    echo  Creating etcd config file: %ETCD_CONFIG%
    (
echo listen-client-urls: http://0.0.0.0:2379
echo advertise-client-urls: http://0.0.0.0:2379
echo quota-backend-bytes: 4294967296
echo auto-compaction-mode: revision
echo auto-compaction-retention: '1000'
    ) > "%ETCD_CONFIG%"
    echo  ✓ Created new etcd config file
) else (
    echo  Using existing etcd config file: %ETCD_CONFIG%
)

:: Create user config only if it doesn't exist
if not exist "%USER_CONFIG%" (
    echo  Creating user config file: %USER_CONFIG%
    (
echo # Extra config to override default milvus.yaml
    ) > "%USER_CONFIG%"
    echo  ✓ Created new user config file
) else (
    echo  Using existing user config file: %USER_CONFIG%
)
goto :eof

:: -------------------------------
:ensure_network
:: Ensure network exists
docker network ls | findstr /C:"%NETWORK_NAME%" >nul
if %errorlevel% neq 0 (
    echo  Creating network: %NETWORK_NAME%
    docker network create %NETWORK_NAME% >nul
    if !errorlevel! neq 0 (
        echo  ERROR: Failed to create network
        exit /b 1
    )
) else (
    echo  Network %NETWORK_NAME% already exists
)
goto :eof

:: -------------------------------
:run_embed
:: Create configs and ensure network exists
call :create_configs
call :ensure_network

:: Run Milvus container
echo  Starting Milvus container...
docker run -d ^
    --network %NETWORK_NAME% ^
    --name %MILVUS_NAME% ^
    --security-opt seccomp:unconfined ^
    -e ETCD_USE_EMBED=true ^
    -e ETCD_DATA_DIR=/var/lib/milvus/etcd ^
    -e ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml ^
    -e COMMON_STORAGETYPE=local ^
    -v "%VOLUME_PATH%:/var/lib/milvus" ^
    -v "%ETCD_CONFIG%:/milvus/configs/embedEtcd.yaml" ^
    -v "%USER_CONFIG%:/milvus/configs/user.yaml" ^
    -p 19530:19530 ^
    -p 9091:9091 ^
    -p 2379:2379 ^
    --health-cmd="curl -f http://localhost:9091/healthz" ^
    --health-interval=30s ^
    --health-start-period=90s ^
    --health-timeout=20s ^
    --health-retries=3 ^
    milvusdb/milvus:v2.5.5 ^
    milvus run standalone >nul

if %errorlevel% neq 0 (
    echo  ERROR: Failed to start Milvus container
    exit /b 1
)
goto :eof

:: -------------------------------
:wait_for_milvus_running
echo  Waiting for Milvus to become healthy...
:wait_loop
set "running="
for /f "tokens=*" %%A in ('docker ps ^| findstr "%MILVUS_NAME%" ^| findstr "healthy"') do set running=1
if defined running (
    echo  ✓ Milvus started successfully
    echo  To change the default configuration, edit %USER_CONFIG% and restart the service
    goto :eof
)
timeout /t 1 >nul
goto wait_loop

:: -------------------------------
:start
:: Check if already running
for /f "tokens=*" %%A in ('docker ps ^| findstr "%MILVUS_NAME%" ^| findstr "healthy"') do (
    echo  Milvus is already running
    exit /b 0
)

:: Check if container exists but not running
set "container_exists="
for /f "tokens=*" %%A in ('docker ps -a ^| findstr "%MILVUS_NAME%"') do set container_exists=1

if defined container_exists (
    echo  Starting existing container...
    docker start %MILVUS_NAME% >nul
    if !errorlevel! neq 0 (
        echo  ERROR: Failed to start existing container
        exit /b 1
    )
) else (
    echo  Running new Milvus container...
    call :run_embed
    if !errorlevel! neq 0 exit /b 1
)

call :wait_for_milvus_running
goto :eof

:: -------------------------------
:stop
echo  Stopping Milvus container...
docker stop %MILVUS_NAME% >nul
if %errorlevel% neq 0 (
    echo  WARNING: Failed to stop Milvus container. It might not be running.
    exit /b 0
)
echo  ✓ Stopped successfully
goto :eof

:: -------------------------------
:delete_container
for /f "tokens=*" %%A in ('docker ps ^| findstr "%MILVUS_NAME%"') do (
    echo  ERROR: Please stop Milvus before deleting
    exit /b 1
)
docker rm %MILVUS_NAME% >nul
if %errorlevel% neq 0 (
    echo  WARNING: Failed to delete Milvus container. It might not exist.
    exit /b 0
)
echo  ✓ Milvus container deleted
goto :eof

:: -------------------------------
:delete
call :delete_container
if not "%CONFIG_PATH%"=="" (
    echo  Cleaning up files in %CONFIG_PATH%...
    if exist "%ETCD_CONFIG%" del /q "%ETCD_CONFIG%" 2>nul
    if exist "%USER_CONFIG%" del /q "%USER_CONFIG%" 2>nul
    echo  ✓ Configuration files cleaned
)
if not "%DATA_PATH%"=="" (
    echo  Cleaning up files in %DATA_PATH%\volumes...
    if exist "%DATA_PATH%\volumes" rmdir /s /q "%DATA_PATH%\volumes" 2>nul
    echo  ✓ Data files cleaned
)
echo  ✓ Deleted all Milvus data and configs
goto :eof