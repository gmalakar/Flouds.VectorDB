param (
    [string]$EnvFile = ".env",
    [string]$InstanceName = "floudsvector-instance",
    [string]$ImageName = "gmalakar/flouds-vector:latest",
    [switch]$Force = $false,
    [switch]$BuildImage = $false
)

Write-Host "========================================================="
Write-Host "Starting Flouds Vector Service"
Write-Host "========================================================="

# Function to ensure network exists
function Ensure-Network {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Name
    )
    
    if (-not (docker network ls --format '{{.Name}}' | Where-Object { $_ -eq $Name })) {
        Write-Host "🔧 Creating network: $Name"
        docker network create $Name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Network $Name created successfully"
        } else {
            Write-Error "❌ Failed to create network: $Name"
            exit 1
        }
    } else {
        Write-Host "✅ Network $Name already exists"
    }
}

# Function to attach a container to a network if not already connected
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
        Write-Warning "⚠️ Container $Container is not running. Skipping network attachment."
        return
    }
    
    # Get current networks for the container
    $networks = docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' $Container
    
    # Check if container is already connected to the network
    if ($networks -notmatch "\b$Network\b") {
        Write-Host "🔗 Attaching network $Network to container $Container"
        docker network connect $Network $Container 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Successfully connected $Container to $Network"
        } else {
            Write-Warning "⚠️ Failed to connect $Container to $Network"
        }
    } else {
        Write-Host "✅ Container $Container is already connected to $Network"
    }
}

# Function to read environment variables from .env file
function Read-EnvFile {
    param (
        [string]$FilePath
    )
    
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

# Check if .env file exists
if (-not (Test-Path $EnvFile)) {
    Write-Warning "⚠️ $EnvFile not found. Make sure environment variables are properly set."
}
else {
    Write-Host "✅ Using environment file: $EnvFile"
    
    # Convert .env to Unix line endings
    Write-Host "🔧 Converting $EnvFile to Unix (LF) format..."
    (Get-Content $EnvFile) -join "`n" | Set-Content $EnvFile -NoNewline
    Write-Host "✅ $EnvFile converted to Unix format"
    
    # Read variables from .env file
    $envVars = Read-EnvFile -FilePath $EnvFile
    
    # Check password file
    if ($envVars.ContainsKey("VECTORDB_PASSWORD_FILE")) {
        $passwordFile = $envVars["VECTORDB_PASSWORD_FILE"]
        
        if (Test-Path $passwordFile) {
            Write-Host "🔧 Converting password file to Unix (LF) format: $passwordFile"
            (Get-Content $passwordFile) -join "`n" | Set-Content $passwordFile -NoNewline
            Write-Host "✅ Password file converted to Unix format"
        }
        else {
            Write-Warning "⚠️ Password file not found: $passwordFile"
        }
    }
    
    # Set default values if not defined
    if (-not $envVars.ContainsKey("VECTORDB_NETWORK")) {
        $envVars["VECTORDB_NETWORK"] = "milvus_network"
    }
    
    if (-not $envVars.ContainsKey("VECTORDB_ENDPOINT")) {
        $envVars["VECTORDB_ENDPOINT"] = "milvus-standalone"
    }
}

# Check if Docker is running
try {
    $process = Start-Process -FilePath "docker" -ArgumentList "version" -NoNewWindow -Wait -PassThru -RedirectStandardError "NUL"
    
    if ($process.ExitCode -ne 0) {
        Write-Error "❌ ERROR: Docker is not running or not accessible. Please start Docker and try again."
        exit 1
    }
    
    Write-Host "✅ Docker is running"
} 
catch {
    Write-Error "❌ ERROR: Docker command failed: $_"
    exit 1
}

# Build image if requested
if ($BuildImage) {
    Write-Host "🔨 Building Docker image..."
    docker build -t $ImageName .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ ERROR: Failed to build Docker image."
        exit 1
    }
    
    Write-Host "✅ Docker image built successfully: $ImageName"
}

# Stop and remove existing container if it exists
$containerExists = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $InstanceName }
if ($containerExists) {
    Write-Host "🛑 Stopping and removing existing container: $InstanceName"
    docker stop $InstanceName | Out-Null
    docker rm $InstanceName | Out-Null
}

# Get Milvus container name from env file or default
$milvusContainerName = $envVars["VECTORDB_ENDPOINT"]
if (-not (docker ps --format '{{.Names}}' | Where-Object { $_ -eq $milvusContainerName })) {
    Write-Warning "⚠️ Milvus container '$milvusContainerName' is not running. Vector service may fail to connect."
    
    if (-not $Force) {
        $confirmation = Read-Host "Continue anyway? (y/n)"
        if ($confirmation -ne 'y') {
            Write-Host "Aborted by user."
            exit 0
        }
    }
}

# Define networks with clear names
$floudsVectorNetwork = "flouds_vector_network"
$milvusNetwork = $envVars["VECTORDB_NETWORK"]

# Ensure networks exist - create them first before any container operations
Write-Host "Creating necessary Docker networks..."
Ensure-Network -Name $floudsVectorNetwork
Ensure-Network -Name $milvusNetwork

# Build Docker command as an array of arguments
$dockerArgs = @(
    "run", "-d", 
    "--name", $InstanceName, 
    "--network", $floudsVectorNetwork, 
    "-p", "19680:19680", 
    "-e", "FLOUDS_API_ENV=Production", 
    "-e", "FLOUDS_DEBUG_MODE=0"
)

# Add environment variables
foreach ($key in @("VECTORDB_ENDPOINT", "VECTORDB_PORT", "VECTORDB_USERNAME", "VECTORDB_NETWORK")) {
    if ($envVars.ContainsKey($key)) {
        $dockerArgs += "-e" 
        $dockerArgs += "$key=$($envVars[$key])"
    }
}

# Add volume mounts
if ($envVars.ContainsKey("VECTORDB_LOG_PATH")) {
    $logPath = $envVars["VECTORDB_LOG_PATH"]
    $dockerArgs += "-v"
    $dockerArgs += "${logPath}:/var/log/flouds:rw" 
}

if ($envVars.ContainsKey("VECTORDB_PASSWORD_FILE")) {
    $passwordFile = $envVars["VECTORDB_PASSWORD_FILE"]
    $dockerArgs += "-v"
    $dockerArgs += "${passwordFile}:/app/secrets/password.txt:rw"
    $dockerArgs += "-e"
    $dockerArgs += "VECTORDB_PASSWORD_FILE=/app/secrets/password.txt"
}

# Add image name
$dockerArgs += $ImageName

# Start the container
Write-Host "🚀 Starting Flouds Vector container..."
Write-Host "Command: docker $($dockerArgs -join ' ')"

try {
    & docker $dockerArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Flouds Vector container started successfully."
        
        # Wait a moment for the container to fully initialize
        Write-Host "Waiting for container to initialize..."
        Start-Sleep -Seconds 5
        
        # Connect to the Milvus network after starting
        Write-Host "Connecting to Milvus network..."
        Attach-NetworkIfNotConnected -Container $InstanceName -Network $milvusNetwork
        
        # Make sure Milvus container is connected to our network
        if (docker ps --format '{{.Names}}' | Where-Object { $_ -eq $milvusContainerName }) {
            Write-Host "Connecting Milvus container to our network..."
            Attach-NetworkIfNotConnected -Container $milvusContainerName -Network $floudsVectorNetwork
        }
        
        Write-Host "✅ API available at: http://localhost:19680/docs"
        Write-Host "✅ Network connections established"
    } else {
        Write-Error "❌ Failed to start Flouds Vector container."
        exit 1
    }
}
catch {
    Write-Error "❌ Error starting Flouds Vector container: $_"
    exit 1
}

# Show logs - optional
$showLogs = Read-Host "Show container logs? (y/n)"
if ($showLogs -eq "y") {
    docker logs -f $InstanceName
}