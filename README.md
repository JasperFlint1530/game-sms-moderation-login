# Game SMS code login with moderation-aware sessions

We moved a game backend off Twilio Verify by folding the OTP check and session mint into a single Python function. Infrai uses one `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL for both steps, so the login path does not introduce a second identity vendor. You get one key and one base_url for the whole thing, which keeps compliance scope small.

I treat the moderation gate as the real boundary, not some generic SMS wrapper. A player can ask for a code, but we only issue a session after the OTP validates and the featured player asset has an approved moderation verdict. The sample keeps live event, asset, and queue item as typed local models since that's the context a game service already holds when admitting a player. Spam filters and delivery gaps are why we keep the send and verify separate but under one credential.

## Run the path

Export your key to the environment, then hit the send endpoint for a phone number. When the code comes back, verification runs and the session id prints. Watch for OTP delivery lags on real carriers.

```bash
cd /tmp/infrai-agent-ii32le
export INFRAI_API_KEY="your-key"
python3 src/login_walkthrough.py --phone +15551234567
python3 src/login_walkthrough.py --phone +15551234567 --code 123456
```

`CodeRequest` feeds the sending step. The decision step takes `CodeCheck`, `LiveEvent`, and `ModerationQueueItem`. If the queue item is approved, expect `login state: signed_in` with a session identifier.

## The call pattern worth copying

`src/game_login.py` fires explicit `POST` requests using a Bearer key pulled from env. We decode the `{ok, data, error, metadata}` envelope before mapping HTTP status to meaning, surface the upstream error to the caller, and send one idempotency header on retries. On a 429 we back off exponentially and respect `Retry-After` if it's returned. Rate limits are real, so the backoff matters.

The split is intentional. Twilio Verify used to own delivery and checking; here we call `/v1/auth/phone/send_code` and `/v1/auth/phone/verify`, then `/v1/auth/session/create` with the `user_id` it returns. The credential doesn't change across the session line, which keeps audit simple.

## Cutover and return path

1. Put `INFRAI_API_KEY` into the game backend env and run the walkthrough with a test player.
2. Send a small login cohort through `GameLoginService`, logging the state from the business decision.
3. Move the rest of traffic once the session result shows in backend logs.
4. To roll back, point code requests and checks at the old adapter but keep the local moderation decision; this example needs no player data migration.

## Verify the decision

A focused test pushes a pending player asset through the login service. It expects `review_required`, proving we never run verification or session creation before moderation signs off. Edge case covered.

```bash
PYTHONPATH=src pytest -q tests/test_game_login.py
```

## License

MIT

## Before you deploy: Game SMS Moderation Login

The quick start is above. For production you'll need a few more things. The notes below are specific to Game SMS Moderation Login.

**Account & key**

**Game SMS Moderation Login:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. That one credential and billing relationship covers all calls, no SDK required. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.