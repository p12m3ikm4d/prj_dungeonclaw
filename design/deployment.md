# Deployment Strategy (Windows Server + Docker Compose)

본 문서는 Windows 상시 서버(공인 IP + 도메인 보유) 환경에서 `git clone/pull -> 즉시 실행 -> 스모크 테스트`까지 가능한 배포 전략을 정의한다.

## 1. Deployment Goals

- 단일 명령으로 서비스 기동(`docker compose up -d`)
- 데이터 영속성 보장(Postgres/Redis/Caddy state)
- 도메인 기반 HTTPS 자동 발급/갱신(Let's Encrypt)
- Pull 기반 무중단에 가까운 재배포 절차 제공

## 2. Runtime Topology

- `game-api`: 애플리케이션 컨테이너(초기 기본값은 `traefik/whoami`)
- `postgres`: 영속 DB
- `redis`: AOF enabled 캐시/실시간 coordination
- `caddy`: reverse proxy + TLS 자동화

## 3. Persistent Mount Policy (Critical)

영속 데이터는 반드시 `HOST_DATA_ROOT` 아래에 바인드 마운트한다.

- `${HOST_DATA_ROOT}/postgres -> /var/lib/postgresql/data`
- `${HOST_DATA_ROOT}/redis -> /data`
- `${HOST_DATA_ROOT}/caddy_data -> /data`
- `${HOST_DATA_ROOT}/caddy_config -> /config`
- `${HOST_DATA_ROOT}/logs/caddy -> /var/log/caddy`
- `${HOST_DATA_ROOT}/backups` (pg_dump 산출물)

주의:
- `HOST_DATA_ROOT`는 OS 재부팅/컨테이너 재생성에 영향받지 않는 로컬 디스크 경로여야 한다.
- 예시: `D:/srv/dungeonclaw`

## 4. Secret and Privacy Handling

민감정보는 `deploy/private/` 아래에서만 관리한다.

- `deploy/private/.env.local`
- `deploy/private/Caddyfile`

해당 경로는 `.gitignore`에 포함되어 git에 올라가지 않는다.

## 5. TLS Strategy

- Caddy가 Let's Encrypt를 통해 인증서를 자동 발급/갱신한다.
- 선행조건:
  - 도메인 A/AAAA 레코드가 서버 공인 IP를 가리켜야 함
  - 방화벽/라우터에서 80, 443 포트 개방
- Caddy 인증서 상태는 `${HOST_DATA_ROOT}/caddy_data`에 영속 저장된다.

## 6. Bootstrap and Operations

### 6.1 최초 1회

1. `pwsh ./deploy/scripts/bootstrap.ps1 -DataRoot "D:/srv/dungeonclaw"`
2. `deploy/private/.env.local` 수정(도메인/이메일/DB 비밀번호)
3. `deploy/private/Caddyfile` 검토
4. `pwsh ./deploy/scripts/deploy.ps1`

### 6.2 일상 업데이트

- `pwsh ./deploy/scripts/update.ps1`

동작:
- `git pull --ff-only`
- 이미지 pull
- compose up
- smoke test 실행

### 6.3 수동 스모크 테스트

- `pwsh ./deploy/scripts/smoke-test.ps1`

검증 항목:
- compose 서비스 상태
- postgres readiness
- redis ping
- domain HTTPS 응답

### 6.4 백업

- `pwsh ./deploy/scripts/backup.ps1`

## 7. Failure and Recovery

- caddy 인증 실패: DNS/포트 개방 상태 확인 후 caddy 재기동
- postgres 손상: 백업 SQL 복원 + 최신 compose 재기동
- redis 손상: AOF 복구 실패 시 redis 디렉토리 백업 후 재생성

## 8. Production Promotion Rule

현재 `game-api` 기본 이미지는 부트스트랩용이다.

- 실제 백엔드 구현 후 `.env.local`의 `APP_IMAGE`를 운영 이미지로 교체한다.
- 교체 후 `update.ps1` 실행만으로 롤링 반영 가능하다.

## 9. Final Decisions

- 배포 오케스트레이션은 Docker Compose로 고정한다.
- Reverse proxy/TLS는 Caddy + Let's Encrypt로 고정한다.
- 영속 데이터는 bind mount로 고정하고 named volume은 사용하지 않는다.
- 개인 정보/서버 정보는 `deploy/private/` 파일로만 관리한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Windows 서버 기준 Compose 배포 전략과 영속 마운트/SSL/운영 스크립트 절차를 확정 | All |
