$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$composeFile = Join-Path $repoRoot "deploy/docker-compose.yml"
$envFile = Join-Path $repoRoot "deploy/private/.env.local"

$envMap = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_.Split('=',2)
    if ($parts.Count -eq 2) {
        $envMap[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$dataRoot = $envMap["HOST_DATA_ROOT"]
$backupDir = "$dataRoot/backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = "$backupDir/postgres_$ts.sql"

Push-Location $repoRoot
try {
    docker compose --env-file $envFile -f $composeFile exec -T postgres pg_dump -U $envMap["POSTGRES_USER"] $envMap["POSTGRES_DB"] > $outFile
    Write-Host "[backup] created $outFile"
} finally {
    Pop-Location
}
