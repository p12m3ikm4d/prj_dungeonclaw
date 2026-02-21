import unittest

from app.services.challenge_service import ChallengeService


def _find_pow_nonce(nonce: str, cmd_hash: str, difficulty: int) -> str:
    probe = 0
    while True:
        ok, _pow_hash = ChallengeService.verify_pow(
            nonce=nonce,
            cmd_hash=cmd_hash,
            proof_nonce=str(probe),
            difficulty=difficulty,
        )
        if ok:
            return str(probe)
        probe += 1


class ChallengeServiceTests(unittest.TestCase):
    def test_challenge_verify_success_and_replay_blocked(self) -> None:
        now = [1_700_000_000]
        service = ChallengeService(
            challenge_expires_seconds=5,
            challenge_ttl_seconds=10,
            default_difficulty=2,
            clock=lambda: float(now[0]),
        )

        record = service.issue(
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            client_cmd_id="c-1",
            cmd={"type": "move_to", "x": 1, "y": 2},
        )

        payload = service.build_sig_payload(
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

        secret = "secret-1"
        sig = service.sign(secret, payload)
        proof_nonce = _find_pow_nonce(record.nonce, record.cmd_hash, record.difficulty)

        result = service.verify_answer(
            server_cmd_id=record.server_cmd_id,
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            session_cmd_secret=secret,
            sig=sig,
            proof_nonce=proof_nonce,
        )
        self.assertTrue(result.ok)

        replay = service.verify_answer(
            server_cmd_id=record.server_cmd_id,
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            session_cmd_secret=secret,
            sig=sig,
            proof_nonce=proof_nonce,
        )
        self.assertFalse(replay.ok)
        self.assertEqual(replay.reason, "expired_challenge")

    def test_challenge_verify_fails_when_expired(self) -> None:
        now = [1_700_000_000]
        service = ChallengeService(
            challenge_expires_seconds=1,
            challenge_ttl_seconds=10,
            default_difficulty=0,
            clock=lambda: float(now[0]),
        )

        record = service.issue(
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            client_cmd_id="c-1",
            cmd={"type": "say", "text": "hi"},
        )

        payload = service.build_sig_payload(
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

        secret = "secret-1"
        sig = service.sign(secret, payload)

        now[0] = record.expires_at + 1
        result = service.verify_answer(
            server_cmd_id=record.server_cmd_id,
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            session_cmd_secret=secret,
            sig=sig,
            proof_nonce=None,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "expired_challenge")

    def test_challenge_verify_fails_when_signature_invalid(self) -> None:
        service = ChallengeService(
            challenge_expires_seconds=5,
            challenge_ttl_seconds=10,
            default_difficulty=0,
        )

        record = service.issue(
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            client_cmd_id="c-1",
            cmd={"type": "move_to", "x": 3, "y": 4},
        )

        payload = service.build_sig_payload(
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

        wrong_sig = service.sign("different-secret", payload)

        result = service.verify_answer(
            server_cmd_id=record.server_cmd_id,
            agent_id="agent-1",
            session_jti="jti-1",
            channel_id="ws-1",
            session_cmd_secret="secret-1",
            sig=wrong_sig,
            proof_nonce=None,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "auth_failed")


if __name__ == "__main__":
    unittest.main()
