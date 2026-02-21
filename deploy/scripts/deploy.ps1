$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$composeFile = Join-Path $repoRoot "deploy/docker-compose.yml"
$envFile = Join-Path $repoRoot "deploy/private/.env.local"

if (-not (Test-Path $envFile)) {
    throw "Missing $envFile. Run ./deploy/scripts/bootstrap.ps1 first."
}

if (-not (Test-Path (Join-Path $repoRoot "deploy/private/Caddyfile"))) {
    throw "Missing deploy/private/Caddyfile. Copy deploy/Caddyfile.example and fill domain settings."
}

Push-Location $repoRoot
try {
    docker compose --env-file $envFile -f $composeFile up -d
    & (Join-Path $repoRoot "deploy/scripts/smoke-test.ps1")
} finally {
    Pop-Location
}
