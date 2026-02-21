# Deploy Quickstart (Windows + Docker Compose)

## 1) Bootstrap

```powershell
pwsh ./deploy/scripts/bootstrap.ps1 -DataRoot "D:/srv/dungeonclaw"
```

## 2) Configure private files

- `deploy/private/.env.local`
- `deploy/private/Caddyfile`

## 3) First deploy

```powershell
pwsh ./deploy/scripts/deploy.ps1
```

## 4) Update after git pull

```powershell
pwsh ./deploy/scripts/update.ps1
```

## 5) Smoke test only

```powershell
pwsh ./deploy/scripts/smoke-test.ps1
```

## 6) Backup PostgreSQL

```powershell
pwsh ./deploy/scripts/backup.ps1
```

## Notes

- `deploy/private/*`는 `.gitignore`에 포함되어 개인정보/서버 설정이 커밋되지 않는다.
- 영속 데이터는 `HOST_DATA_ROOT` 하위 바인드 마운트에 저장된다.
