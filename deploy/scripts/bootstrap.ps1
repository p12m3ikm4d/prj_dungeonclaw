param(
    [string]$DataRoot = "D:/srv/dungeonclaw"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$deployRoot = Join-Path $repoRoot "deploy"
$privateDir = Join-Path $deployRoot "private"
$normalizedDataRoot = $DataRoot -replace "\\", "/"

New-Item -ItemType Directory -Force -Path $privateDir | Out-Null

$dirs = @(
    "$normalizedDataRoot/postgres",
    "$normalizedDataRoot/redis",
    "$normalizedDataRoot/caddy_data",
    "$normalizedDataRoot/caddy_config",
    "$normalizedDataRoot/logs/caddy",
    "$normalizedDataRoot/backups"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

$envLocal = Join-Path $privateDir ".env.local"
$caddyLocal = Join-Path $privateDir "Caddyfile"

if (-not (Test-Path $envLocal)) {
    Copy-Item (Join-Path $deployRoot ".env.example") $envLocal
    (Get-Content $envLocal) -replace "HOST_DATA_ROOT=D:/srv/dungeonclaw", "HOST_DATA_ROOT=$normalizedDataRoot" | Set-Content $envLocal
    Write-Host "[bootstrap] created $envLocal"
} else {
    Write-Host "[bootstrap] exists  $envLocal"
}

if (-not (Test-Path $caddyLocal)) {
    Copy-Item (Join-Path $deployRoot "Caddyfile.example") $caddyLocal
    Write-Host "[bootstrap] created $caddyLocal"
} else {
    Write-Host "[bootstrap] exists  $caddyLocal"
}

Write-Host "[bootstrap] edit deploy/private/.env.local and deploy/private/Caddyfile before first deploy"
