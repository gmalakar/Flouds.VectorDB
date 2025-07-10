# =============================================================================
# File: start-flouds-vectordb.ps1
# Date: 2024-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
#
# This script sets up and runs the Flouds Vector container with proper volume mapping,
# environment variable handling, and network connections to Milvus.
#
# Usage:
#   ./start-flouds-vectordb.ps1 [-EnvFile <path>] [-InstanceName <name>] [-ImageName <name>] [-Force] [-BuildImage]
#
# Parameters:
#   -EnvFile       : Path to .env file (default: ".env")
#   -InstanceName  : Name of the Docker container (default: "floudsvector-instance")
#   -ImageName     : Docker image to use (default: "gmalakar/flouds-vector:latest")
#   -Force         : Force restart container if it exists, or continue when Milvus is down
#   -BuildImage    : Build Docker image locally before starting container
# =============================================================================

param (
    [string]$EnvFile = ".env",
    [string]$InstanceName = "floudsvector-instance",
    [string]$ImageName = "gmalakar/flouds-vector:latest",
    [switch]$Force = $false,
    [switch]$BuildImage = $false
)

# ========================== HELPER FUNCTIONS ==========================

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
}

function Ensure-Network {
    param ([string]$Name)
    
    if (-not (docker network ls --format '{{.Name}}' | Where-Object { $_ -eq $Name })) {
        Write-Host "🔧 Creating network: $Name" -ForegroundColor Yellow
        docker network create $Name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Network $Name created successfully"
        } else {
            Write-Error "Failed to create network: $Name"
            exit 1
        }
    } else {
        Write-Success "Network $Name already exists"
    }
}

function Attach-NetworkIfNotConnected {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Container,
        
        [Parameter(Mandatory=$true)]
        [string]$Network
    )
    
    # Check if container is running
    $containerRunning = docker ps --format '{{.Names}}' | Where-Object { $_ -eq $Container }
    if (-not $containerRunning) {
        Write-Warning "Container $Container is not running. Skipping network attachment."
        return
    }
    
    # Get current networks for the container
    $networks = docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' $Container
    
    # Check if container is already connected to the network
    if ($networks -notmatch "\b$Network\b") {
        Write-Host "🔗 Attaching network $Network to container $Container" -ForegroundColor Yellow
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
                # Remove quotes if present
                $value = $value -replace '^"(.*)"$', '$1'
                $value = $value -replace "^'(.*)'$", '$1'
                $envVars[$key] = $value
            }
        }
    }
    return $envVars
}

function Check-Docker {
    try {
        $process = Start-Process -FilePath "docker" -ArgumentList "version" -NoNewWindow -Wait -PassThru -RedirectStandardError "NUL"
        if ($process.ExitCode -ne 0) {
            Write-Error "Docker is not running or not accessible. Please start Docker and try again."
            exit 1
        }
        Write-Success "Docker is running"
        return $true
    } catch {
        Write-Error "Docker command failed: $_"
        exit 1
    }
}

# ========================== MAIN SCRIPT ==========================

Write-Host "========================================================="
Write-Host "                FLOUDS VECTOR STARTER SCRIPT             " -ForegroundColor Cyan
Write-Host "========================================================="
Write-Host "Instance Name : $InstanceName"
Write-Host "Image         : $ImageName"
Write-Host "Environment   : $EnvFile"
Write-Host "Build Image   : $BuildImage"
Write-Host "Force Restart : $Force"
Write-Host "========================================================="

# Check if Docker is available
Write-StepHeader "Checking Docker installation"
Check-Docker

# Read environment variables
Write-StepHeader "Reading environment configuration"
if (-not (Test-Path $EnvFile)) {
    Write-Warning "$EnvFile not found. Using default values."
} else {
    Write-Success "Using environment file: $EnvFile"
    
    # Convert .env to Unix line endings to avoid issues
    Write-Host "Converting $EnvFile to Unix (LF) format..." -ForegroundColor Yellow
    (Get-Content $EnvFile) -join "`n" | Set-Content $EnvFile -NoNewline
    Write-Success "$EnvFile converted to Unix format"
}

$envVars = Read-EnvFile -FilePath $EnvFile

# Handle vector-specific files and settings
if ($envVars.ContainsKey("VECTORDB_PASSWORD_FILE")) {
    $passwordFile = $envVars["VECTORDB_PASSWORD_FILE"]
    
    if (Test-Path $passwordFile) {
        Write-Host "Converting password file to Unix format: $passwordFile" -ForegroundColor Yellow
        (Get-Content $passwordFile) -join "`n" | Set-Content $passwordFile -NoNewline
        Write-Success "Password file converted to Unix format"
    } else {
        Write-Warning "Password file not found: $passwordFile"
    }
}

# Set defaults for required variables
if (-not $envVars.ContainsKey("VECTORDB_NETWORK")) {
    $envVars["VECTORDB_NETWORK"] = "milvus_network"
    Write-Warning "VECTORDB_NETWORK not set. Using default: 'milvus_network'"
}

if (-not $envVars.ContainsKey("VECTORDB_ENDPOINT")) {
    $envVars["VECTORDB_ENDPOINT"] = "milvus-standalone"
    Write-Warning "VECTORDB_ENDPOINT not set. Using default: 'milvus-standalone'"
}

# Check log path and create if needed
if ($envVars.ContainsKey("VECTORDB_LOG_PATH")) {
    $logPath = $envVars["VECTORDB_LOG_PATH"]
    if (-not (Test-Path $logPath)) {
        Write-Warning "Log directory does not exist: $logPath"
        Write-Host "Creating directory..." -ForegroundColor Yellow
        try {
            New-Item -ItemType Directory -Path $logPath -Force | Out-Null
            Write-Success "Log directory created: $logPath"
        } catch {
            Write-Error "Failed to create log directory: $_"
            exit 1
        }
    } else {
        Write-Success "Found log directory: $logPath"
    }
} else {
    Write-Warning "VECTORDB_LOG_PATH not set. Container logs will not be persisted to host."
}

# Build image if requested
if ($BuildImage) {
    Write-StepHeader "Building Docker image"
    Write-Host "Building $ImageName..." -ForegroundColor Yellow
    docker build -t $ImageName .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Docker image."
        exit 1
    }
    
    Write-Success "Docker image built successfully: $ImageName"
}

# Stop and remove existing container if it exists
Write-StepHeader "Managing container instance"
$containerExists = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $InstanceName }
if ($containerExists) {
    Write-Warning "Container $InstanceName already exists"
    Write-Host "Stopping and removing existing container: $InstanceName" -ForegroundColor Yellow
    docker stop $InstanceName | Out-Null
    docker rm $InstanceName | Out-Null
    Write-Success "Container removed"
}

# Check if Milvus is running
Write-StepHeader "Checking Milvus connectivity"
$milvusContainerName = $envVars["VECTORDB_ENDPOINT"]
if (-not (docker ps --format '{{.Names}}' | Where-Object { $_ -eq $milvusContainerName })) {
    Write-Warning "Milvus container '$milvusContainerName' is not running. Vector service may fail to connect."
    
    if (-not $Force) {
        $confirmation = Read-Host "Continue anyway? (y/n)"
        if ($confirmation -ne 'y') {
            Write-Host "Aborted by user." -ForegroundColor Red
            exit 0
        }
    }
} else {
    Write-Success "Milvus container '$milvusContainerName' is running"
}

# Define networks with clear names
Write-StepHeader "Creating Docker networks"
$floudsVectorNetwork = "flouds_vector_network"
$milvusNetwork = $envVars["VECTORDB_NETWORK"]

# Ensure networks exist
Ensure-Network -Name $floudsVectorNetwork
Ensure-Network -Name $milvusNetwork

# Build Docker command
Write-StepHeader "Preparing container configuration"
$dockerArgs = @(
    "run", "-d", 
    "--name", $InstanceName, 
    "--network", $floudsVectorNetwork, 
    "-p", "19680:19680", 
    "-e", "FLOUDS_API_ENV=Production", 
    "-e", "FLOUDS_DEBUG_MODE=0"
)

# Add Vector-specific environment variables
foreach ($key in @("VECTORDB_ENDPOINT", "VECTORDB_PORT", "VECTORDB_USERNAME", "VECTORDB_NETWORK")) {
    if ($envVars.ContainsKey($key)) {
        Write-Host "Setting $key: $($envVars[$key])" -ForegroundColor Gray
        $dockerArgs += "-e" 
        $dockerArgs += "$key=$($envVars[$key])"
    }
}

# Add password file if specified
if ($envVars.ContainsKey("VECTORDB_PASSWORD_FILE")) {
    $passwordFile = $envVars["VECTORDB_PASSWORD_FILE"]
    Write-Host "Mounting password file: $passwordFile → /app/secrets/password.txt" -ForegroundColor Gray
    $dockerArgs += "-v"
    $dockerArgs += "${passwordFile}:/app/secrets/password.txt:ro"
    $dockerArgs += "-e"
    $dockerArgs += "VECTORDB_PASSWORD_FILE=/app/secrets/password.txt"
}

# Add log directory if specified
if ($envVars.ContainsKey("VECTORDB_LOG_PATH")) {
    $hostLogPath = $envVars["VECTORDB_LOG_PATH"]
    $containerLogPath = $envVars.ContainsKey("FLOUDS_LOG_PATH") ? $envVars["FLOUDS_LOG_PATH"] : "/var/log/flouds"
    Write-Host "Mounting logs: $hostLogPath → $containerLogPath" -ForegroundColor Gray
    $dockerArgs += "-v"
    $dockerArgs += "${hostLogPath}:${containerLogPath}:rw"
    $dockerArgs += "-e"
    $dockerArgs += "FLOUDS_LOG_PATH=${containerLogPath}"
}

# Add image name
$dockerArgs += $ImageName

# Start the container
Write-StepHeader "Starting Flouds Vector container"
Write-Host "Command: docker $($dockerArgs -join ' ')" -ForegroundColor Gray

try {
    & docker $dockerArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Flouds Vector container started successfully"
        
        # Wait for container to initialize
        Write-Host "Waiting for container to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Connect to the Milvus network after starting
        Write-Host "Connecting container to Milvus network..." -ForegroundColor Yellow
        Attach-NetworkIfNotConnected -Container $InstanceName -Network $milvusNetwork
        
        # Connect Milvus to our network if it's running
        if (docker ps --format '{{.Names}}' | Where-Object { $_ -eq $milvusContainerName }) {
            Write-Host "Connecting Milvus to Flouds Vector network..." -ForegroundColor Yellow
            Attach-NetworkIfNotConnected -Container $milvusContainerName -Network $floudsVectorNetwork
        }
        
        # Show container status
        Write-StepHeader "Container Status"
        docker ps --filter "name=$InstanceName" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
        
        Write-Success "API available at: http://localhost:19680/docs"
    } else {
        Write-Error "Failed to start Flouds Vector container."
        exit 1
    }
}
catch {
    Write-Error "Error starting Flouds Vector container: $_"
    exit 1
}

# Show management options
Write-StepHeader "Container Management"
Write-Host "Use the following commands to manage the container:" -ForegroundColor Cyan
Write-Host "  * View logs: docker logs -f $InstanceName" -ForegroundColor Gray
Write-Host "  * Stop container: docker stop $InstanceName" -ForegroundColor Gray
Write-Host "  * Remove container: docker rm $InstanceName" -ForegroundColor Gray
Write-Host ""

$showLogs = Read-Host "Would you like to view container logs now? (y/n)"
if ($showLogs -eq "y" -or $showLogs -eq "Y") {
    docker logs -f $InstanceName
}