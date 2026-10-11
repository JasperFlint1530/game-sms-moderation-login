"""Run a complete game login after a player receives a code."""

from __future__ import annotations

import argparse
import uuid

from game_login import (
    CodeCheck,
    CodeRequest,
    GameLoginService,
    InfraiClient,
    LiveEvent,
    LoginContext,
    ModerationQueueItem,
    PlayerAsset,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", required=True)
    parser.add_argument("--code")
    args = parser.parse_args()

    client = InfraiClient.from_environment()
    service = GameLoginService(client)
    asset = PlayerAsset("castle-17", "player-42", "approved")
    context = LoginContext(
        LiveEvent("weekend-build", "player-42", asset),
        ModerationQueueItem("review-17", asset, "approved"),
    )
    request_id = str(uuid.uuid4())
    if args.code:
        outcome = service.verify_login(CodeCheck(args.phone, args.code), context, request_id)
        print(f"login state: {outcome.state}; session: {outcome.session_id}")
    else:
        service.request_login_code(CodeRequest(args.phone), request_id)
        print("SMS code requested for game login")


if __name__ == "__main__":
    main()
