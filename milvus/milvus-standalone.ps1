<#
.SYNOPSIS
    Milvus Standalone Docker Container Management Script

.PARAMETER Command
    The action to perform: start, stop, restart, remove, or delete

.PARAMETER DataPath
    Required for start and delete commands. Local path for Milvus data.

.PARAMETER ConfigPath
    Required for start and delete commands. Local path for config files.

.EXAMPLE
    .\milvus-standalone.ps1 -Command start -DataPath "C:\milvus\data" -ConfigPath "C:\milvus\configs"

.EXAMPLE
    .\milvus-standalone.ps1 -Command stop
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "remove", "delete")]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [string]$DataPath,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath
)

if ($Command -in @("start", "restart", "remove", "delete")) {
    if (-not $DataPath -or -not $ConfigPath) {
        Write-Host "ERROR: DataPath and ConfigPath are required for '$Command' command" -ForegroundColor Red
        exit 1
    }
}

$NetworkName = "milvus_network"
$ContainerName = "milvus-standalone"

if ($ConfigPath) {
    $EtcdConfig = Join-Path $ConfigPath "embedEtcd.yaml"
    $UserConfig = Join-Path $ConfigPath "user.yaml"
}

function Create-Configs {
    if (!(Test-Path $ConfigPath)) {
        New-Item -ItemType Directory -Path $ConfigPath -Force | Out-Null
    }
    
    if (!(Test-Path $EtcdConfig)) {
        @"
listen-client-urls: http://0.0.0.0:2379
advertise-client-urls: http://0.0.0.0:2379
quota-backend-bytes: 4294967296
auto-compaction-mode: revision
auto-compaction-retention: '1000'
"@ | Out-File -FilePath $EtcdConfig -Encoding UTF8
        Write-Host "Created etcd config file"
    }
    
    if (!(Test-Path $UserConfig)) {
        "# Extra config to override default milvus.yaml" | Out-File -FilePath $UserConfig -Encoding UTF8
        Write-Host "Created user config file"
    }
}

function Ensure-Network {
    $networkExists = docker network ls | Select-String $NetworkName
    if (!$networkExists) {
        docker network create $NetworkName | Out-Null
    }
}

function Start-Milvus {
    $running = docker ps | Select-String "$ContainerName.*healthy"
    if ($running) {
        Write-Host "Milvus is already running"
        return
    }
    
    $containerExists = docker ps -a | Select-String $ContainerName
    if ($containerExists) {
        docker start $ContainerName | Out-Null
    } else {
        Create-Configs
        Ensure-Network
        
        if (!(Test-Path $DataPath)) { New-Item -ItemType Directory -Path $DataPath -Force | Out-Null }
        
        # Convert Windows paths to Docker-compatible paths
        function Convert-ToDockerPath($path) {
            $fullPath = (Resolve-Path $path).Path
            if ($fullPath -match '^([A-Z]):(.*)') {
                $drive = $matches[1].ToLower()
                $pathPart = $matches[2] -replace '\\', '/'
                return "/mnt/$drive$pathPart"
            }
            return $fullPath -replace '\\', '/'
        }
        
        $DockerDataPath = $DataPath
        $DockerConfigPath = $ConfigPath
        
        Write-Host "Using paths:"
        Write-Host "  Data: $DockerDataPath"
        Write-Host "  Config: $DockerConfigPath"

        docker run -d --network $NetworkName `
            --name $ContainerName `
            --security-opt seccomp:unconfined `
            -e ETCD_USE_EMBED=true `
            -e ETCD_DATA_DIR=/var/lib/milvus/etcd `
            -e ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml `
            -e COMMON_STORAGETYPE=local `
            -v "${DockerDataPath}:/var/lib/milvus" `
            -v "${DockerConfigPath}\embedEtcd.yaml:/milvus/configs/embedEtcd.yaml" `
            -v "${DockerConfigPath}\user.yaml:/milvus/configs/user.yaml" `
            -p 19530:19530 `
            -p 9091:9091 `
            -p 2379:2379 `
            --health-cmd="curl -f http://localhost:9091/healthz" `
            --health-interval=30s `
            --health-start-period=90s `
            --health-timeout=20s `
            --health-retries=3 `
            milvusdb/milvus:v2.5.5 `
            milvus run standalone
    }
    
    Write-Host "Waiting for Milvus to become healthy..."
    do {
        Start-Sleep -Seconds 1
        $healthy = docker ps | Select-String "$ContainerName.*healthy"
    } while (!$healthy)
    
    Write-Host "Milvus started successfully"
}

function Stop-Milvus {
    docker stop $ContainerName | Out-Null
    Write-Host "Stopped successfully"
}

function Remove-Container {
    $running = docker ps | Select-String $ContainerName
    if ($running) {
        Write-Host "ERROR: Please stop Milvus before removing"
        exit 1
    }
    docker rm $ContainerName | Out-Null
    Write-Host "Container removed"
}

function Remove-Milvus {
    Remove-Container
    Write-Host "Container removed, data preserved"
}

function Delete-Milvus {
    Write-Host "WARNING: This will permanently delete all Milvus data and configuration files!"
    Write-Host "Data path: $DataPath"
    Write-Host "Config files: $EtcdConfig, $UserConfig"
    $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
    
    if ($confirmation -eq "yes") {
        Remove-Container
        if (Test-Path $EtcdConfig) { Remove-Item $EtcdConfig -Force }
        if (Test-Path $UserConfig) { Remove-Item $UserConfig -Force }
        if (Test-Path $DataPath) { Remove-Item $DataPath -Recurse -Force }
        Write-Host "Deleted all Milvus data and configs"
    } else {
        Write-Host "Delete operation cancelled"
    }
}

switch ($Command) {
    "start" { Start-Milvus }
    "stop" { Stop-Milvus }
    "restart" { Stop-Milvus; Start-Milvus }
    "remove" { Remove-Milvus }
    "delete" { Delete-Milvus }
}