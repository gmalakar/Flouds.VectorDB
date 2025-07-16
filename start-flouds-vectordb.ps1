# =============================================================================
# File: start-flouds-vectordb.ps1
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

param (
    [string]$EnvFile = ".env",
    [string]$InstanceName = "floudsvector-instance",
    [string]$ImageName = "gmalakar/flouds-vector:latest",
    [int]$Port = 19680
)

function Write-StepHeader {
    param ([string]$Message)
    Write-Host "`n== $Message ==" -ForegroundColor Cyan
}

function Write-Success {
    param ([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param ([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param ([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
    exit 1
}

function New-NetworkIfMissing {
    param ([string]$Name)
    if (-not (docker network ls --format '{{.Name}}' | Where-Object { $_ -eq $Name })) {
        Write-Host "🔧 Creating network: $Name" -ForegroundColor Yellow
        docker network create $Name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Network $Name created successfully"
        } else {
            Write-Error "Failed to create network: $Name"
        }
    } else {
        Write-Success "Network $Name already exists"
    }
}

function Connect-NetworkIfNotConnected {
    param (
        [string]$Container,
        [string]$Network
    )
    $containerRunning = docker ps --format '{{.Names}}' | Where-Object { $_ -eq $Container }
    if (-not $containerRunning) {
        Write-Warning "Container $Container is not running. Skipping network connection."
        return
    }
    $networks = docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' $Container
    if ($networks -notmatch "\b$Network\b") {
        Write-Host "🔗 Connecting network $Network to container $Container" -ForegroundColor Yellow
        docker network connect $Network $Container 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Successfully connected $Container to $Network"
        } else {
            Write-Warning "Failed to connect $Container to $Network"
        }
    } else {
        Write-Success "Container $Container is already connected to $Network"
    }
}

function Read-EnvFile {
    param ([string]$FilePath)
    $envVars = @{}
    if (Test-Path $FilePath) {
        Get-Content $FilePath | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $key = $Matches[1].Trim()
                $value = $Matches[2].Trim()
                $value = $value -replace '^"(.*)"$', '$1'
                $value = $value -replace "^'(.*)'$", '$1'
                $envVars[$key] = $value
            }
        }
    }
    return $envVars
}

Write-Host "========================================================="
Write-Host "                FLOUDS VECTOR STARTER SCRIPT             " -ForegroundColor Cyan
Write-Host "========================================================="
Write-Host "Instance Name : $InstanceName"
Write-Host "Image         : $ImageName"
Write-Host "Environment   : $EnvFile"
Write-Host "========================================================="

# Read .env file
if (-not (Test-Path $EnvFile)) {
    Write-Warning "$EnvFile not found. Using default values."
    $envVars = @{}
} else {
    Write-Success "Using environment file: $EnvFile"
    (Get-Content $EnvFile) -join "`n" | Set-Content $EnvFile -NoNewline
    $envVars = Read-EnvFile -FilePath $EnvFile
}

# Set defaults for required variables
$floudsVectorNetwork = "flouds_vector_network"
$milvusNetwork = if ($envVars.ContainsKey("VECTORDB_NETWORK")) { $envVars["VECTORDB_NETWORK"] } else { "milvus_network" }
$milvusContainerName = if ($envVars.ContainsKey("VECTORDB_ENDPOINT")) { $envVars["VECTORDB_ENDPOINT"] } else { "milvus-standalone" }

# Check and create log directory if needed
if ($envVars.ContainsKey("VECTORDB_LOG_PATH")) {
    $hostLogPath = $envVars["VECTORDB_LOG_PATH"]
    if (-not (Test-Path $hostLogPath)) {
        Write-Warning "Log directory does not exist: $hostLogPath"
        Write-Host "Creating directory..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $hostLogPath -Force | Out-Null
        Write-Success "Log directory created: $hostLogPath"
    } else {
        Write-Success "Found log directory: $hostLogPath"
    }
} else {
    Write-Warning "VECTORDB_LOG_PATH not set. Container logs will not be persisted to host."
}

# Ensure networks exist
New-NetworkIfMissing -Name $floudsVectorNetwork
New-NetworkIfMissing -Name $milvusNetwork

# Stop and remove existing container if it exists
if (docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $InstanceName }) {
    Write-Host "🛑 Stopping and removing existing container: $InstanceName" -ForegroundColor Yellow
    docker stop $InstanceName | Out-Null
    docker rm $InstanceName | Out-Null
    Write-Success "Container removed"
}

# Check if Milvus is running
if (-not (docker ps --format '{{.Names}}' | Where-Object { $_ -eq $milvusContainerName })) {
    Write-Warning "Milvus container '$milvusContainerName' is not running. Vector service may fail to connect."
    $confirmation = Read-Host "Continue anyway? (y/n)"
    if ($confirmation -ne "y") {
        Write-Host "Aborted by user." -ForegroundColor Red
        exit 0
    }
} else {
    Write-Success "Milvus container '$milvusContainerName' is running"
}

# Build Docker run command
$dockerArgs = @(
    "run", "-d",
    "--name", $InstanceName,
    "--network", $floudsVectorNetwork,
    "-p", "${Port}:${Port}",
    "-e", "FLOUDS_API_ENV=Production",
    "-e", "FLOUDS_DEBUG_MODE=0"
)

foreach ($key in @("VECTORDB_ENDPOINT", "VECTORDB_PORT", "VECTORDB_USERNAME", "VECTORDB_NETWORK")) {
    if ($envVars.ContainsKey($key)) {
        Write-Host "Setting ${key}: $($envVars[$key])"
        $dockerArgs += "-e"
        $dockerArgs += "$key=$($envVars[$key])"
    }
}

# Add password file if specified
if ($envVars.ContainsKey("VECTORDB_PASSWORD_FILE")) {
    $passwordFile = $envVars["VECTORDB_PASSWORD_FILE"]
    Write-Host "Mounting password file: $passwordFile → /app/secrets/password.txt"
    $dockerArgs += "-v"
    $dockerArgs += "${passwordFile}:/app/secrets/password.txt:rw"
    $dockerArgs += "-e"
    $dockerArgs += "VECTORDB_PASSWORD_FILE=/app/secrets/password.txt"
}

# Add log directory if specified
if ($envVars.ContainsKey("VECTORDB_LOG_PATH")) {
    $hostLogPath = $envVars["VECTORDB_LOG_PATH"]
    $containerLogPath = if ($envVars.ContainsKey("FLOUDS_LOG_PATH")) { $envVars["FLOUDS_LOG_PATH"] } else { "/var/logs/flouds" }
    Write-Host "Mounting logs: $hostLogPath → $containerLogPath"
    $dockerArgs += "-v"
    $dockerArgs += "${hostLogPath}:${containerLogPath}:rw"
    $dockerArgs += "-e"
    $dockerArgs += "FLOUDS_LOG_PATH=$containerLogPath"
}

$dockerArgs += $ImageName

Write-Host "========================================================="
Write-Host "Starting Flouds Vector container..."
Write-Host "Command: docker $($dockerArgs -join ' ')" -ForegroundColor Gray

try {
    & docker $dockerArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Flouds Vector container started successfully"
        Write-Host "Waiting for container to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5

        Write-Host "Connecting container to Milvus network..." -ForegroundColor Yellow
        Connect-NetworkIfNotConnected -Container $InstanceName -Network $milvusNetwork

        if (docker ps --format '{{.Names}}' | Where-Object { $_ -eq $milvusContainerName }) {
            Write-Host "Connecting Milvus to Flouds Vector network..." -ForegroundColor Yellow
            Connect-NetworkIfNotConnected -Container $milvusContainerName -Network $floudsVectorNetwork
        }

        Write-Host "========================================================="
        Write-Host "Container Status:"
        docker ps --filter "name=$InstanceName" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
        Write-Host "========================================================="
        Write-Success "API available at: http://localhost:$Port/docs"
    } else {
        Write-Error "Failed to start Flouds Vector container."
    }
}
catch {
    Write-Error "Error starting Flouds Vector container: $_"
}

Write-Host "========================================================="
Write-Host "Container Management:" -ForegroundColor Cyan
Write-Host "  * View logs: docker logs -f $InstanceName" -ForegroundColor Gray
Write-Host "  * Stop container: docker stop $InstanceName" -ForegroundColor Gray
Write-Host "  * Remove container: docker rm $InstanceName" -ForegroundColor Gray
Write-Host ""

$showLogs = Read-Host "Would you like to view container logs now? (y/n)"
if ($showLogs -eq "y" -or $showLogs -eq "Y") {
    docker logs -f $InstanceName
}
