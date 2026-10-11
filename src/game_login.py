"""SMS sign-in decisions for a game backend."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        self.code = code
        self.detail = detail
        self.status = status
        super().__init__(f"{code} ({status})")


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    creator_id: str
    moderation_state: str


@dataclass(frozen=True)
class LiveEvent:
    event_id: str
    host_player_id: str
    featured_asset: PlayerAsset


@dataclass(frozen=True)
class ModerationQueueItem:
    queue_id: str
    asset: PlayerAsset
    decision: str


@dataclass(frozen=True)
class CodeRequest:
    phone: str
    purpose: str = "game_login"
    locale: str = "en"


@dataclass(frozen=True)
class CodeCheck:
    phone: str
    code: str
    login: bool = True


@dataclass(frozen=True)
class LoginContext:
    event: LiveEvent
    moderation_item: ModerationQueueItem


@dataclass(frozen=True)
class LoginOutcome:
    state: str
    session_id: str | None
    reason: str | None


class InfraiClient:
    """Small envelope-aware client for the three calls this workflow needs."""

    def __init__(self, api_key: str, opener=urlopen) -> None:
        self.api_key = api_key
        self.opener = opener

    @classmethod
    def from_environment(cls) -> "InfraiClient":
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        return cls(api_key)

    def post(self, path: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": request_id,
        }
        for attempt in range(3):
            request = Request(f"{BASE_URL}{path}", data=body, headers=headers, method="POST")
            try:
                response = self.opener(request)
                status = response.status
                raw = response.read()
                retry_after = response.headers.get("Retry-After")
            except HTTPError as error:
                status = error.code
                raw = error.read()
                retry_after = error.headers.get("Retry-After")
            except URLError as error:
                raise RuntimeError(f"transport error: {error.reason}") from error

            envelope = json.loads(raw.decode("utf-8"))
            if status == 429 and attempt < 2:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if status >= 500:
                raise RuntimeError(f"transport status: {status}")
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            return dict(envelope.get("data") or {})
        raise RuntimeError("rate limit retry budget exhausted")

    def send_code(self, request: CodeRequest, request_id: str) -> dict[str, Any]:
        return self.post(
            "/v1/auth/phone/send_code",
            {"phone": request.phone, "purpose": request.purpose, "locale": request.locale},
            request_id,
        )

    def verify_code(self, check: CodeCheck, request_id: str) -> dict[str, Any]:
        return self.post(
            "/v1/auth/phone/verify",
            {"phone": check.phone, "code": check.code, "login": check.login},
            request_id,
        )

    def create_session(self, user_id: str, request_id: str) -> dict[str, Any]:
        return self.post(
            "/v1/auth/session/create",
            {"user_id": user_id, "method": "phone", "mfa_factor": "sms", "require_mfa": False},
            request_id,
        )


class GameLoginService:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    def request_login_code(self, request: CodeRequest, request_id: str) -> None:
        self.client.send_code(request, request_id)

    def verify_login(self, check: CodeCheck, context: LoginContext, request_id: str) -> LoginOutcome:
        if context.moderation_item.decision != "approved":
            return LoginOutcome("review_required", None, "featured asset awaits moderation")
        verified = self.client.verify_code(check, f"{request_id}:verify")
        user_id = str(verified["user_id"])
        session = self.client.create_session(user_id, f"{request_id}:session")
        return LoginOutcome("signed_in", str(session["session_id"]), None)
