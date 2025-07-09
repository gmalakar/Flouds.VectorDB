param (
    [string]$ImageName = "gmalakar/flouds-vector",
    [string]$Tag = "latest",
    [switch]$PushImage = $false,
    [switch]$Force = $false
)

Write-Host "========================================================="
Write-Host "Building Flouds Vector Docker Image"
Write-Host "========================================================="

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

# Check if Dockerfile exists
if (-not (Test-Path "Dockerfile")) {
    Write-Error "❌ ERROR: Dockerfile not found in the current directory"
    exit 1
}

# Full image name with tag
$fullImageName = "${ImageName}:${Tag}"

# Check if image with this tag already exists
$imageExists = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -eq $fullImageName }
if ($imageExists -and -not $Force) {
    $confirmation = Read-Host "Image $fullImageName already exists. Rebuild? (y/n)"
    if ($confirmation -ne 'y') {
        Write-Host "Build cancelled."
        exit 0
    }
}

# Build Docker image
Write-Host "🔨 Building Docker image: $fullImageName"
Write-Host "This may take a few minutes..."

$buildArgs = @(
    "build",
    "--no-cache",
    "-t", $fullImageName,
    "."
)

# Execute docker build command
try {
    & docker $buildArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker image built successfully: $fullImageName"
        
        # Push image if requested
        if ($PushImage) {
            Write-Host "🚀 Pushing image to registry..."
            docker push $fullImageName
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Image pushed successfully to registry"
            } else {
                Write-Error "❌ Failed to push image to registry"
                exit 1
            }
        }
    } else {
        Write-Error "❌ Failed to build Docker image"
        exit 1
    }
}
catch {
    Write-Error "❌ Error building Docker image: $_"
    exit 1
}

# Show available images
Write-Host "Available Flouds Vector images:"
docker images "${ImageName}*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# The following are just comments, not commands to run:
# Usage examples:
# .\build-flouds-vector.ps1
# .\build-flouds-vector.ps1 -Tag v1.0.0
# .\build-flouds-vector.ps1 -PushImage
# .\build-flouds-vector.ps1 -Force  