from game_login import (
    CodeCheck,
    GameLoginService,
    LiveEvent,
    LoginContext,
    ModerationQueueItem,
    PlayerAsset,
)


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def verify_code(self, check, request_id):
        self.calls.append("verify")
        return {"user_id": "player-42"}

    def create_session(self, user_id, request_id):
        self.calls.append("session")
        return {"session_id": "session-99"}


def test_pending_asset_blocks_session_until_moderation_decides() -> None:
    client = RecordingClient()
    asset = PlayerAsset("map-7", "player-42", "pending")
    context = LoginContext(
        LiveEvent("creator-cup", "player-42", asset),
        ModerationQueueItem("queue-7", asset, "pending"),
    )

    outcome = GameLoginService(client).verify_login(CodeCheck("+15551234567", "123456"), context, "test")

    assert outcome.state == "review_required"
    assert outcome.session_id is None
    assert client.calls == []
