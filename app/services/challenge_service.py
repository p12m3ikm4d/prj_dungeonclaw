from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple


STATUS_ISSUED = "ISSUED"
STATUS_CONSUMED = "CONSUMED"
STATUS_EXPIRED = "EXPIRED"


@dataclass
class ChallengeRecord:
    server_cmd_id: str
    client_cmd_id: str
    agent_id: str
    session_jti: str
    channel_id: str
    cmd_hash: str
    nonce: str
    expires_at: int
    difficulty: int
    status: str
    created_at: int


@dataclass
class VerifyResult:
    ok: bool
    reason: Optional[str]


class ChallengeService:
    def __init__(
        self,
        challenge_expires_seconds: int,
        challenge_ttl_seconds: int,
        default_difficulty: int,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._challenge_expires_seconds = challenge_expires_seconds
        self._challenge_ttl_seconds = challenge_ttl_seconds
        self._default_difficulty = default_difficulty
        self._clock = clock or time.time
        self._records: Dict[str, ChallengeRecord] = {}
        self._lock = Lock()

    @staticmethod
    def hash_cmd(cmd: Dict[str, Any]) -> str:
        canonical = json.dumps(cmd, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _b64url_no_pad(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @classmethod
    def build_sig_payload(
        cls,
        *,
        session_jti: str,
        channel_id: str,
        agent_id: str,
        server_cmd_id: str,
        client_cmd_id: str,
        cmd_hash: str,
        nonce: str,
        expires_at: int,
        difficulty: int,
    ) -> str:
        return (
            f"v1|{session_jti}|{channel_id}|{agent_id}|{server_cmd_id}|{client_cmd_id}|"
            f"{cmd_hash}|{nonce}|{expires_at}|{difficulty}"
        )

    @classmethod
    def sign(cls, secret: str, payload: str) -> str:
        digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
        return cls._b64url_no_pad(digest)

    @staticmethod
    def verify_pow(nonce: str, cmd_hash: str, proof_nonce: str, difficulty: int) -> Tuple[bool, str]:
        pow_hash = hashlib.sha256(f"{nonce}|{cmd_hash}|{proof_nonce}".encode("utf-8")).hexdigest()
        if not pow_hash.startswith("0" * difficulty):
            return False, pow_hash
        return True, pow_hash

    def _purge_old_records(self, now: int) -> None:
        stale_ids = [
            k for k, v in self._records.items() if now > (v.created_at + self._challenge_ttl_seconds)
        ]
        for sid in stale_ids:
            self._records.pop(sid, None)

    def issue(
        self,
        *,
        agent_id: str,
        session_jti: str,
        channel_id: str,
        client_cmd_id: str,
        cmd: Dict[str, Any],
        difficulty: Optional[int] = None,
    ) -> ChallengeRecord:
        now = int(self._clock())
        selected_difficulty = self._default_difficulty if difficulty is None else difficulty

        record = ChallengeRecord(
            server_cmd_id=f"cmd_{uuid.uuid4().hex[:12]}",
            client_cmd_id=client_cmd_id,
            agent_id=agent_id,
            session_jti=session_jti,
            channel_id=channel_id,
            cmd_hash=self.hash_cmd(cmd),
            nonce=secrets.token_urlsafe(16),
            expires_at=now + self._challenge_expires_seconds,
            difficulty=max(0, selected_difficulty),
            status=STATUS_ISSUED,
            created_at=now,
        )

        with self._lock:
            self._purge_old_records(now)
            self._records[record.server_cmd_id] = record

        return record

    def get(self, server_cmd_id: str) -> Optional[ChallengeRecord]:
        with self._lock:
            return self._records.get(server_cmd_id)

    def verify_answer(
        self,
        *,
        server_cmd_id: str,
        agent_id: str,
        session_jti: str,
        channel_id: str,
        session_cmd_secret: str,
        sig: str,
        proof_nonce: Optional[str],
    ) -> VerifyResult:
        now = int(self._clock())

        with self._lock:
            record = self._records.get(server_cmd_id)
            if record is None:
                return VerifyResult(ok=False, reason="expired_challenge")

            if record.status != STATUS_ISSUED:
                return VerifyResult(ok=False, reason="expired_challenge")

            if now > record.expires_at:
                record.status = STATUS_EXPIRED
                return VerifyResult(ok=False, reason="expired_challenge")

            if record.agent_id != agent_id or record.session_jti != session_jti or record.channel_id != channel_id:
                return VerifyResult(ok=False, reason="auth_failed")

            sig_payload = self.build_sig_payload(
                session_jti=record.session_jti,
                channel_id=record.channel_id,
                agent_id=record.agent_id,
                server_cmd_id=record.server_cmd_id,
                client_cmd_id=record.client_cmd_id,
                cmd_hash=record.cmd_hash,
                nonce=record.nonce,
                expires_at=record.expires_at,
                difficulty=record.difficulty,
            )
            expected = self.sign(session_cmd_secret, sig_payload)
            if not hmac.compare_digest(expected, sig):
                return VerifyResult(ok=False, reason="auth_failed")

            if record.difficulty > 0:
                if not proof_nonce:
                    return VerifyResult(ok=False, reason="auth_failed")
                ok, _pow_hash = self.verify_pow(record.nonce, record.cmd_hash, proof_nonce, record.difficulty)
                if not ok:
                    return VerifyResult(ok=False, reason="auth_failed")

            record.status = STATUS_CONSUMED
            return VerifyResult(ok=True, reason=None)
