from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Tuple


@dataclass
class Account:
    id: str
    email: str
    password_hash: str
    created_at: int


@dataclass
class ApiKey:
    id: str
    account_id: str
    key_prefix: str
    key_hash: str
    label: Optional[str]
    created_at: int


@dataclass
class Session:
    token: str
    jti: str
    account_id: str
    role: str
    agent_id: Optional[str]
    cmd_secret: str
    expires_at: int


class AuthError(Exception):
    pass


class InMemoryAuthStore:
    def __init__(self, session_ttl_seconds: int) -> None:
        self._session_ttl_seconds = session_ttl_seconds
        self._accounts_by_id: Dict[str, Account] = {}
        self._accounts_by_email: Dict[str, Account] = {}
        self._keys_by_id: Dict[str, ApiKey] = {}
        self._sessions_by_token: Dict[str, Session] = {}
        self._busy_agents: Dict[str, str] = {}
        self._lock = Lock()

    @staticmethod
    def _hash_raw(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def create_account(self, email: str, password: str) -> Account:
        email_normalized = email.strip().lower()
        with self._lock:
            if email_normalized in self._accounts_by_email:
                raise AuthError("email_already_exists")

            account = Account(
                id=f"acc_{uuid.uuid4().hex}",
                email=email_normalized,
                password_hash=self._hash_raw(password),
                created_at=int(time.time()),
            )
            self._accounts_by_id[account.id] = account
            self._accounts_by_email[email_normalized] = account
            return account

    def create_api_key(self, account_id: str, label: Optional[str]) -> Tuple[ApiKey, str]:
        with self._lock:
            if account_id not in self._accounts_by_id:
                raise AuthError("account_not_found")

            raw_key = f"dcw_{secrets.token_urlsafe(24)}"
            api_key = ApiKey(
                id=f"key_{uuid.uuid4().hex}",
                account_id=account_id,
                key_prefix=raw_key[:12],
                key_hash=self._hash_raw(raw_key),
                label=label,
                created_at=int(time.time()),
            )
            self._keys_by_id[api_key.id] = api_key
            return api_key, raw_key

    def create_session(self, api_key_raw: str, role: str, agent_id: Optional[str]) -> Session:
        if role not in {"agent", "owner_spectator", "spectator"}:
            raise AuthError("invalid_scope")

        if role in {"agent", "owner_spectator"} and not agent_id:
            raise AuthError("agent_id_required")
        if role == "spectator":
            agent_id = None

        api_key_hash = self._hash_raw(api_key_raw)
        with self._lock:
            key_record = next((k for k in self._keys_by_id.values() if k.key_hash == api_key_hash), None)
            if key_record is None:
                raise AuthError("invalid_api_key")

            session = self._issue_session(
                account_id=key_record.account_id,
                role=role,
                agent_id=agent_id,
            )
            self._sessions_by_token[session.token] = session
            return session

    def create_dev_spectator_session(self) -> Session:
        with self._lock:
            session = self._issue_session(
                account_id="acc_dev_spectator",
                role="spectator",
                agent_id=None,
            )
            self._sessions_by_token[session.token] = session
            return session

    def create_dev_owner_session(self, agent_id: str) -> Session:
        if not agent_id:
            raise AuthError("agent_id_required")
        with self._lock:
            session = self._issue_session(
                account_id="acc_dev_owner",
                role="owner_spectator",
                agent_id=agent_id,
            )
            self._sessions_by_token[session.token] = session
            return session

    def _issue_session(self, account_id: str, role: str, agent_id: Optional[str]) -> Session:
        issued_at = int(time.time())
        return Session(
            token=f"sess_{secrets.token_urlsafe(24)}",
            jti=f"jti_{uuid.uuid4().hex}",
            account_id=account_id,
            role=role,
            agent_id=agent_id,
            cmd_secret=secrets.token_urlsafe(32),
            expires_at=issued_at + self._session_ttl_seconds,
        )

    def get_session(self, token: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions_by_token.get(token)
            if session is None:
                return None
            if session.expires_at <= int(time.time()):
                self._sessions_by_token.pop(token, None)
                return None
            return session

    def validate_session(self, token: str, role: str, agent_id: Optional[str]) -> Session:
        session = self.get_session(token)
        if session is None:
            raise AuthError("invalid_session")
        if session.role != role:
            raise AuthError("invalid_scope")
        if role in {"agent", "owner_spectator"} and session.agent_id != agent_id:
            raise AuthError("agent_mismatch")
        return session

    def acquire_agent_lock(self, agent_id: str, server_cmd_id: str) -> bool:
        with self._lock:
            current = self._busy_agents.get(agent_id)
            if current is not None and current != server_cmd_id:
                return False
            self._busy_agents[agent_id] = server_cmd_id
            return True

    def release_agent_lock(self, agent_id: str, server_cmd_id: str) -> None:
        with self._lock:
            current = self._busy_agents.get(agent_id)
            if current == server_cmd_id:
                self._busy_agents.pop(agent_id, None)
