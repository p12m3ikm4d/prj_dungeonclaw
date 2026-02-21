$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$composeFile = Join-Path $repoRoot "deploy/docker-compose.yml"
$envFile = Join-Path $repoRoot "deploy/private/.env.local"

Push-Location $repoRoot
try {
    git pull --ff-only
    docker compose --env-file $envFile -f $composeFile pull
    docker compose --env-file $envFile -f $composeFile up -d
    & (Join-Path $repoRoot "deploy/scripts/smoke-test.ps1")
} finally {
    Pop-Location
}
