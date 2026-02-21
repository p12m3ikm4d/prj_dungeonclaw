$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$composeFile = Join-Path $repoRoot "deploy/docker-compose.yml"
$envFile = Join-Path $repoRoot "deploy/private/.env.local"

if (-not (Test-Path $envFile)) {
    throw "Missing $envFile"
}

$envMap = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_.Split('=',2)
    if ($parts.Count -eq 2) {
        $envMap[$parts[0].Trim()] = $parts[1].Trim()
    }
}

Push-Location $repoRoot
try {
    Write-Host "[smoke] docker compose ps"
    docker compose --env-file $envFile -f $composeFile ps

    Write-Host "[smoke] postgres readiness"
    docker compose --env-file $envFile -f $composeFile exec -T postgres pg_isready -U $envMap["POSTGRES_USER"] -d $envMap["POSTGRES_DB"]

    Write-Host "[smoke] redis ping"
    docker compose --env-file $envFile -f $composeFile exec -T redis redis-cli ping

    $domain = $envMap["APP_DOMAIN"]
    if (-not [string]::IsNullOrWhiteSpace($domain)) {
        Write-Host "[smoke] https://$domain/"
        curl.exe -fsS "https://$domain/" | Out-Null
        Write-Host "[smoke] domain response ok"
    } else {
        Write-Host "[smoke] APP_DOMAIN not set; skipping HTTPS check"
    }

    Write-Host "[smoke] all checks passed"
} finally {
    Pop-Location
}
