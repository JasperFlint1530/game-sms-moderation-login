import sys
from types import SimpleNamespace

import login_walkthrough


def test_walkthrough_only_requests_code_without_code(monkeypatch, capsys) -> None:
    calls = []

    class FakeService:
        def __init__(self, client):
            pass

        def request_login_code(self, request, request_id):
            calls.append("send")

        def verify_login(self, check, context, request_id):
            calls.append("verify")
            return SimpleNamespace(state="signed_in", session_id="session-99")

    monkeypatch.setattr(login_walkthrough.InfraiClient, "from_environment", lambda: object())
    monkeypatch.setattr(login_walkthrough, "GameLoginService", FakeService)
    monkeypatch.setattr(sys, "argv", ["login_walkthrough.py", "--phone", "+15551234567", "--code", "123456"])
    login_walkthrough.main()
    assert calls == ["verify"]
    assert "signed_in" in capsys.readouterr().out

    calls.clear()
    monkeypatch.setattr(sys, "argv", ["login_walkthrough.py", "--phone", "+15551234567"])
    login_walkthrough.main()
    assert calls == ["send"]
