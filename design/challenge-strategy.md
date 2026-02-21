# Challenge Strategy Design

본 문서는 Agent WS 명령 인증 체인에서 `challenge`를 어떻게 생성/검증/관측할지에 대한 세부 전략을 정의한다.

## 1. Security Objectives

- 명령 단위 재전송(replay) 차단
- WS 연결 탈취/명령 위조 난이도 상승
- 자동 에이전트 처리와 인간 개입 비용 분리(짧은 TTL + PoW)
- 서버 자원 소모형 남용을 방어하기 위한 선검증 체계 제공

## 2. Non-Goals

- 인간 개입을 완전 차단하지 않는다.
- 클라이언트 단말 탈취 상황을 완전 방어하지 않는다.
- 대칭키 유출 이후 무결성 보장을 제공하지 않는다.

## 3. Threat Model

| Threat | Description | Mitigation |
|---|---|---|
| Replay | 과거 `command_answer`를 재사용 | one-time challenge 상태 전이 + 짧은 만료시간 |
| Tampering | `move_to` 좌표 변경 후 서명 재사용 | `cmd_hash`를 서명 입력에 결합 |
| Relay delay | 사람 개입으로 응답 지연 | `expires_at` 5초 기본, 만료 즉시 거절 |
| Flood | 무효 answer 대량 전송 | pre-verify rate limit + 실패 누적 페널티 |
| Channel hijack | 다른 연결에서 answer 전송 | `channel_id` 결합 검증 |

## 4. Challenge Lifecycle

상태 머신:

- `ISSUED`
- `ANSWERED_VALID`
- `ANSWERED_INVALID`
- `EXPIRED`
- `CONSUMED`

전이 규칙:

1. `command_req` 수신 시 `ISSUED` 생성
2. 유효한 `command_answer` 1회만 `ANSWERED_VALID`로 전이
3. 큐 승격 후 즉시 `CONSUMED`
4. 만료 시 `EXPIRED`
5. 무효 응답은 `ANSWERED_INVALID` 카운트만 증가, 상태는 `ISSUED` 유지 가능

## 5. Cryptographic Design

### 5.1 Session Command Secret

- 세션 발급 시 서버가 랜덤 32바이트 `session_cmd_secret` 생성
- 클라이언트에는 세션 생성 응답으로 1회 전달
- 서버는 Redis에 `HSET session:{jti}:cmd_secret`로 TTL과 함께 보관
- DB 영속 저장 금지

### 5.2 Canonical Signing Input

`sig_payload` 문자열 포맷:

```text
v1|session_jti|channel_id|agent_id|server_cmd_id|client_cmd_id|cmd_hash|nonce|expires_at|difficulty
```

`cmd_hash` 계산:

- `cmd`를 JSON canonical form(키 정렬, 공백 제거)으로 직렬화
- `SHA256` hex digest 사용

### 5.3 Signature

- 알고리즘: `HMAC-SHA256`
- 인코딩: `base64url` (패딩 제거)
- 계산식:

```text
sig = BASE64URL(HMAC_SHA256(session_cmd_secret, sig_payload))
```

### 5.4 PoW Proof

- 목적: answer 스팸 비용 증가
- 기본 규칙:
  - `proof_nonce`를 찾아 `SHA256(nonce|cmd_hash|proof_nonce)`의 앞 `difficulty` 개 hex가 `0`
- 검증 비용은 O(1)
- `difficulty=0`이면 PoW 생략 허용

## 6. Challenge Payload Contract

`command_challenge.payload`:

```json
{
  "client_cmd_id": "c-123",
  "server_cmd_id": "s-9f2",
  "nonce": "base64url-16bytes",
  "expires_at": 1760000005,
  "difficulty": 3,
  "channel_id": "ws-7f2d",
  "sig_alg": "HMAC-SHA256",
  "pow_alg": "sha256-leading-hex-zeroes"
}
```

`command_answer.payload`:

```json
{
  "server_cmd_id": "s-9f2",
  "sig": "base64url...",
  "proof": {
    "proof_nonce": "18446744073709551615",
    "pow_hash": "000a6f..."
  }
}
```

호환성:
- `proof`가 문자열인 구버전은 `proof_nonce`로 해석 가능

## 7. Validation Pipeline

검증 순서:

1. `server_cmd_id` 존재 확인
2. challenge 상태 확인(`ISSUED`만 허용)
3. 만료 여부 확인(`now <= expires_at`)
4. `channel_id`, `session_jti`, `agent_id` 일치 확인
5. `sig` 재계산 후 constant-time 비교
6. `difficulty>0`인 경우 PoW 검증
7. Redis Lua 스크립트로 `ISSUED -> ANSWERED_VALID` 원자 전이

원자 전이 실패 시:
- 이미 사용된 challenge로 간주하고 `expired_challenge` 또는 `auth_failed` 반환

## 8. Redis Keys and TTL

- `challenge:{server_cmd_id}` (Hash)
- `challenge:{server_cmd_id}:state` (String)
- `challenge:{server_cmd_id}:attempts` (Counter)
- `session:{jti}:cmd_secret` (String)

권장 TTL:

- challenge TTL: 10초
- challenge expires_at: 발급 후 5초
- session_cmd_secret TTL: 세션 TTL와 동일(예: 15분)

## 9. Difficulty Strategy

초기 정책:

- 기본 `difficulty=2`
- 에이전트별 적응 범위 `0..5`

상향 조건:

- 최근 30초 `invalid_answer_rate > 20%`
- 최근 30초 `answer_rps > threshold`

하향 조건:

- 최근 5분 `valid_p95_solve_ms > 500`
- 정상 트래픽에서 실패율 낮음

안정성 규칙:

- 10초 내 1단계 이상 변동 금지
- 한 번에 ±1만 조정

## 10. Failure Policy and Penalty

- `expired_challenge`: 재요청 허용, 페널티 없음
- `auth_failed`: 60초 윈도우 5회 초과 시 30초 cooldown
- cooldown 중 명령은 `rate_limited`
- 반복 위반 시 WS 연결 종료

## 11. Observability

필수 메트릭:

- `challenge_issued_total`
- `challenge_answer_valid_total`
- `challenge_answer_invalid_total`
- `challenge_expired_total`
- `challenge_verify_ms`
- `challenge_pow_verify_ms`
- `challenge_difficulty_level{agent_id}`

필수 로그 필드:

- `trace_id`
- `server_cmd_id`
- `agent_id`
- `session_jti`
- `channel_id`
- `difficulty`
- `verify_result`

## 12. Rollout Plan

1. Phase A: PoW off(`difficulty=0`) + sig만 검증
2. Phase B: 기본 `difficulty=1` 점진 적용
3. Phase C: 적응형 difficulty 활성화
4. Phase D: 악성 패턴 기반 cooldown 자동화

## 13. Test Matrix

- 정상 응답: valid sig + valid proof
- 만료 응답: expires_at 경계값
- 재사용 응답: 동일 answer 2회 전송
- 위조 응답: cmd_hash 불일치
- 채널 불일치: 다른 ws 연결에서 answer 전송
- 고부하 응답: invalid flood 시 cooldown 동작

## 14. Integration Points

- 프로토콜 스키마는 `./design/protocol.md`와 동기화
- WS 인터페이스는 `./design/interface.md`와 동기화
- 클래스 책임은 `./design/class.md`의 `CommandCoordinator`에 귀속

## 15. Final Decisions

- 세션 secret 전달 방식은 `세션 생성 응답 body 1회 전달`로 고정하고, JWT claim에는 포함하지 않는다.
- 모바일 성능 기준은 `difficulty=2`에서 `p95 solve <= 250ms`를 목표로 하고, 글로벌 상한을 `difficulty=3`으로 제한한다.
- allowlist 기반 난이도 예외는 허용하지 않는다. 모든 agent는 동일한 난이도 정책을 따른다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | challenge 생성/검증/anti-replay/PoW/난이도 조정 전략을 상세화 | All |
| 2026-02-21 | Codex | Open decision 3건을 최종 정책으로 확정 | 15 |
