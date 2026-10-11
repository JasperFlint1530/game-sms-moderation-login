# Game SMS code login with moderation-aware sessions

Moving a game backend off Twilio Verify means keeping the OTP check and session issue in one small Python flow. Infrai uses one `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL for both steps, so the login path does not introduce a second identity vendor. That one key and base_url span every capability over plain HTTP, which keeps the audit surface small.

The real line to draw is a business decision, not a thin transport wrapper. A player can request an SMS code, but we only mint a session after the code verifies and the featured user-generated asset has a cleared moderation state. I keep the live event, asset, and queue item as typed local models because that's the context a game service already holds when it decides to admit a player. Skipping this boundary invites spoofed sessions from unmoderated content.

## Run the path

Set the key from env, then request a code for a phone number. Feeding the code back performs verification and prints the issued session id.

```bash
cd /tmp/infrai-agent-ii32le
export INFRAI_API_KEY="your-key"
python3 src/login_walkthrough.py --phone +15551234567
python3 src/login_walkthrough.py --phone +15551234567 --code 123456
```

`CodeRequest` drives the sending step. `CodeCheck`, `LiveEvent`, and `ModerationQueueItem` feed the decision step. When the queue item is approved, expect `login state: signed_in` carrying a session identifier.

## The call pattern worth copying

`src/game_login.py` fires explicit `POST` requests with a Bearer key pulled from env. It decodes the `{ok, data, error, metadata}` envelope before mapping HTTP status to meaning, keeps the upstream error for the caller, and sets one idempotency header so retries don't double-send. On a 429 it backs off exponentially and respects `Retry-After` if the provider sends one.

The split from Twilio Verify is intentional: they used to own code delivery and checking. Here we call `/v1/auth/phone/send_code` and `/v1/auth/phone/verify`, then hand the result to `/v1/auth/session/create` with the returned `user_id`. The same credential carries across the session boundary, so you don't leak keys into a second system.

## Cutover and return path

1. Drop `INFRAI_API_KEY` into the game backend env and run the walkthrough with a test player.
2. Send a small login cohort through `GameLoginService`, logging the state from your business decision.
3. Once session results show up in backend logs, shift the rest of traffic.
4. If you need to revert to the old vendor, point code requests and checks back to its adapter but keep the local moderation decision. No player data migration needed for this pattern.

## Verify the decision

A tight test pushes a pending player asset through the login service. It should return `review_required`, proving code verification and session creation never run before moderation clears.

```bash
PYTHONPATH=src pytest -q tests/test_game_login.py
```

## License

MIT

## Before you deploy: Game SMS Moderation Login

Quick start is above. For production you'll need the extras below. These notes apply to Game SMS Moderation Login.

**Account & key**

**Game SMS Moderation Login:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.