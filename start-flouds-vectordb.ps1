# =============================================================================
# File: start-flouds-vectordb.ps1
# Date: 2024-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
#
# This script sets up and runs the Flouds Vector container with proper volume mapping
# and environment variable handling based on a .env file.
#
# Usage:
#   ./start-flouds-vectordb.ps1 [-EnvFile <path>] [-InstanceName <name>] [-ImageName <name>] [-Port <port>] [-Force] [-BuildImage] [-PullAlways]
#
# Parameters:
#   -EnvFile       : Path to .env file (default: ".env")
#   -InstanceName  : Name of the Docker container (default: "floudsvector-instance")
#   -ImageName     : Docker image to use (default: "gmalakar/flouds-vector:latest")
#   -Port          : Port to expose for the API (default: 19680)
#   -Force         : Force restart container if it exists
#   -BuildImage    : Build Docker image locally before starting container
#   -PullAlways    : Always pull image from registry before running
# =============================================================================

# Custom parameter parsing
$EnvFile = ".env"
$InstanceName = "floudsvector-instance"
$ImageName = "gmalakar/flouds-vector:latest"
$Port = 19680
$Force = $false
$BuildImage = $false
$PullAlways = $false

# Valid parameter list with exact names
$validParams = @("-force", "-env-file", "-instance-name", "-image-name", "-port", "-build-image", "-pull-always")
$switchParams = @("-force", "-build-image", "-pull-always")



for ($i = 0; $i -lt $args.Count; $i++) {
    $arg = $args[$i].ToLower()
    
    # Check if parameter exists in valid list
    if ($arg -notin $validParams) {
        Write-Host "Error: Invalid parameter '$($args[$i])'" -ForegroundColor Red
        Write-Host "Valid parameters: $($validParams -join ', ')" -ForegroundColor Yellow
        exit 1
    }
    
    # Handle parameter based on type
    if ($arg -in $switchParams) {
        # Switch parameters
        switch ($arg) {
            "-force" { $Force = $true }
            "-build-image" { $BuildImage = $true }
            "-pull-always" { $PullAlways = $true }
        }
    }
    else {
        # Parameters with values
        if ($i + 1 -lt $args.Count) {
            $paramValue = $args[$i + 1]
            switch ($arg) {
                "-env-file" { $EnvFile = $paramValue }
                "-instance-name" { $InstanceName = $paramValue }
                "-image-name" { $ImageName = $paramValue }
                "-port" { $Port = [int]$paramValue }
            }
            $i++ # Skip next argument as it's the value
        }
        else {
            Write-Host "Error: Parameter '$($args[$i])' requires a value" -ForegroundColor Red
            exit 1
        }
    }
}

function Write-StepHeader {
    param ([string]$Message)
    Write-Host "`n== $Message ==" -ForegroundColor Cyan
}

function Write-Success {
    param ([string]$Message)
    Write-Host " $Message" -ForegroundColor Green
}

function Write-Warning {
    param ([string]$Message)
    Write-Host " $Message" -ForegroundColor Yellow
}

function Write-Error {
    param ([string]$Message)
    Write-Host " $Message" -ForegroundColor Red
    exit 1
}

function New-NetworkIfMissing {
    param ([string]$Name)
    if (-not (docker network ls --format '{{.Name}}' | Where-Object { $_ -eq $Name })) {
        Write-Host " Creating network: $Name" -ForegroundColor Yellow
        docker network create $Name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Network $Name created successfully"
        }
        else {
            Write-Error "Failed to create network: $Name"
        }
    }
    else {
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
        Write-Host " Connecting network $Network to container $Container" -ForegroundColor Yellow
        docker network connect $Network $Container 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Successfully connected $Container to $Network"
        }
        else {
            Write-Warning "Failed to connect $Container to $Network"
        }
    }
    else {
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

function Test-DirectoryWritable {
    param ([string]$Path)
    try {
        $testFile = Join-Path -Path $Path -ChildPath "test_write_$([Guid]::NewGuid().ToString()).tmp"
        [System.IO.File]::WriteAllText($testFile, "test")
        Remove-Item -Path $testFile -Force
        return $true
    }
    catch {
        return $false
    }
}

function Set-DirectoryPermissions {
    param (
        [string]$Path,
        [string]$Description
    )
    if (-not (Test-Path $Path)) {
        Write-Warning "$Description directory does not exist: $Path"
        Write-Host "Creating directory..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Success "$Description directory created: $Path"
    }
    else {
        Write-Success "Found $Description directory: $Path"
    }
    
    # Test if directory is writable
    if (Test-DirectoryWritable -Path $Path) {
        Write-Success "$Description directory is writable: $Path"
    }
    else {
        Write-Warning "$Description directory is not writable: $Path"
        Write-Host "Setting permissions on $Description directory..." -ForegroundColor Yellow
        try {
            # Try to set permissions (works on Windows)
            $acl = Get-Acl $Path
            $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Everyone", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
            $acl.SetAccessRule($accessRule)
            Set-Acl $Path $acl
            Write-Success "Permissions set successfully"
        }
        catch {
            Write-Warning "Failed to set permissions: $_"
            Write-Warning "$Description may not be writable. Please check directory permissions manually."
            $continue = Read-Host "Continue anyway? (y/n)"
            if ($continue -ne "y") {
                Write-Host "Aborted by user." -ForegroundColor Red
                exit 0
            }
        }
    }
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
}
else {
    Write-Success "Using environment file: $EnvFile"
    (Get-Content $EnvFile) -join "`n" | Set-Content $EnvFile -NoNewline
    $envVars = Read-EnvFile -FilePath $EnvFile
}

# Require FLOUDS_DATA_PATH_AT_HOST to be set for host data mapping
if (-not ($envVars.ContainsKey("FLOUDS_DATA_PATH_AT_HOST") -and $envVars["FLOUDS_DATA_PATH_AT_HOST"])) {
    Write-Host "❌ Error: FLOUDS_DATA_PATH_AT_HOST must be set in the .env file or environment." -ForegroundColor Red
    exit 1
}

# Require FLOUDS_SECRET_PATH_AT_HOST to be set for host secrets mapping
if (-not ($envVars.ContainsKey("FLOUDS_SECRET_PATH_AT_HOST") -and $envVars["FLOUDS_SECRET_PATH_AT_HOST"])) {
    Write-Host "❌ Error: FLOUDS_SECRET_PATH_AT_HOST must be set in the .env file or environment." -ForegroundColor Red
    exit 1
}

# Set defaults for required variables
$floudsVectorNetwork = "flouds_vector_network"
$milvusNetwork = if ($envVars.ContainsKey("VECTORDB_NETWORK")) { $envVars["VECTORDB_NETWORK"] } else { "milvus_network" }
$milvusContainerName = if ($envVars.ContainsKey("VECTORDB_ENDPOINT")) { $envVars["VECTORDB_ENDPOINT"] } else { "milvus-standalone" }
$workingDir = "/flouds-vector"
$containerLogPath = "$workingDir/logs"
$dockerDataPath = "$workingDir/data"
$containerSecretPath = "$dockerDataPath/secrets"
$vectorDBPasswordFile = "$containerSecretPath/password.txt"


# Ensure networks exist
New-NetworkIfMissing -Name $floudsVectorNetwork
New-NetworkIfMissing -Name $milvusNetwork

# Stop and remove existing container if it exists
if (docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $InstanceName }) {
    Write-Host " Stopping and removing existing container: $InstanceName" -ForegroundColor Yellow
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
}
else {
    Write-Success "Milvus container '$milvusContainerName' is running"
}

# Build Docker run command
$dockerArgs = @("run", "-d")
if ($PullAlways) {
    $dockerArgs += "--pull"
    $dockerArgs += "always"
}
$dockerArgs += @(
    "--name", $InstanceName,
    "--network", $floudsVectorNetwork,
    "-p", "${Port}:${Port}",
    "-e", "FLOUDS_API_ENV=Production",
    "-e", "APP_DEBUG_MODE=0"
)

# Add all environment variables from .env file
foreach ($key in $envVars.Keys) {
    Write-Host "Setting ${key}: $($envVars[$key])"
    $dockerArgs += "-e"
    $dockerArgs += "$key=$($envVars[$key])"
}

# Data directory mapping (SQLite database)
if ($envVars.ContainsKey("FLOUDS_DATA_PATH_AT_HOST")) {
    $hostDataPath = $envVars["FLOUDS_DATA_PATH_AT_HOST"]
    Write-Host "Mapping Data directory: $hostDataPath -> $dockerDataPath"
    $dockerArgs += "-v"
    $dockerArgs += "${hostDataPath}:${dockerDataPath}:rw"

    # Determine clients DB filename (allow override via env)
    if ($envVars.ContainsKey("FLOUDS_CLIENTS_DB_FILENAME") -and $envVars["FLOUDS_CLIENTS_DB_FILENAME"]) {
        $clientsFilename = $envVars["FLOUDS_CLIENTS_DB_FILENAME"]
        Write-Host "Using FLOUDS_CLIENTS_DB_FILENAME: $clientsFilename"
    }
    else {
        $clientsFilename = "clients.db"
        Write-Host "FLOUDS_CLIENTS_DB_FILENAME not specified; using default: $clientsFilename"
    }

    $dockerArgs += "-e"
    $dockerArgs += "FLOUDS_CLIENTS_DB=$dockerDataPath/$clientsFilename"
}

# Secrets handling: require and mount `FLOUDS_SECRET_PATH_AT_HOST`.
# The script enforces `FLOUDS_SECRET_PATH_AT_HOST` earlier, so use it as the single source of truth.
if ($envVars.ContainsKey("FLOUDS_SECRET_PATH_AT_HOST") -and $envVars["FLOUDS_SECRET_PATH_AT_HOST"]) {
    $hostSecretDir = $envVars["FLOUDS_SECRET_PATH_AT_HOST"]
    Write-Host "Mapping Secrets directory: $hostSecretDir -> $containerSecretPath"

    # Ensure secrets directory exists and is writable/readable
    Set-DirectoryPermissions -Path $hostSecretDir -Description "Secrets"

    # Mount the secrets directory read-only into the container
    $dockerArgs += "-v"
    $dockerArgs += "${hostSecretDir}:${containerSecretPath}:ro"

    # Determine password filename (allow override via env)
    $passwordFilename = if ($envVars.ContainsKey("VECTORDB_PASSWORD_FILENAME") -and $envVars["VECTORDB_PASSWORD_FILENAME"]) { $envVars["VECTORDB_PASSWORD_FILENAME"] } else { "password.txt" }
    Write-Host "Using VECTORDB_PASSWORD_FILENAME: $passwordFilename"

    # Export container-side env pointing into mounted secrets dir
    $dockerArgs += "-e"
    $dockerArgs += "VECTORDB_PASSWORD_FILE=$containerSecretPath/$passwordFilename"
}
else {
    # Defensive: earlier the script enforces that FLOUDS_SECRET_PATH_AT_HOST must be set,
    # but keep a clear error in case that pre-check is changed.
    Write-Host "❌ Error: FLOUDS_SECRET_PATH_AT_HOST must be set to mount secrets directory." -ForegroundColor Red
    exit 1
}

# Add log directory if specified
if ($envVars.ContainsKey("FLOUDS_LOG_PATH_AT_HOST")) {
    $hostLogPath = $envVars["FLOUDS_LOG_PATH_AT_HOST"]
    Write-Host "Mounting logs: $hostLogPath  $containerLogPath"
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
        docker ps --filter "name=$InstanceName" --format "table {{.ID}}`t{{.Image}}`t{{.Status}}`t{{.Ports}}"
        Write-Host "========================================================="
        Write-Success "API available at: http://localhost:$Port/docs"
    }
    else {
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
Write-Host "========================================================="
