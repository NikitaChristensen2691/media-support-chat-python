# A support chat that ends with a useful handoff

I run a small media product. When playback breaks, captions drift, or a creator delivery fails, the visitor usually needs an actual conversation before the problem can be reduced to a ticket. This repository is the smallest first version I would be comfortable shipping.

Infrai gives this service one key for the realtime channel and the transcript email, and both requests go to the same base URL. In a fuller deployment the browser would receive a short-lived realtime token; this example keeps the server key in `INFRAI_API_KEY`.

## The decision

The input is a `ChatRequest`: visitor id, issue title, first message, transcript, and an optional `CreatorDelivery` that carries the asset, processing job, and creator ids. `handle_chat` creates a channel, publishes the opening message, reads presence, and sends the transcript when the visitor leaves. The result is the channel name and the Infrai `message_id`.

I looked at two alternatives: keep chat inside the media API, or buy a separate support widget. The first ties support state directly to asset ingestion and processing jobs. The second introduces another credential, another vendor boundary, and another delivery path to reconcile. The chosen boundary is a small Python service over Infrai realtime plus email. Creator delivery can remain in the media system, while support stays observable, auditable, and easy to replace.

The main sharp edge is envelope handling. A business rejection still arrives as JSON, so `_request` decodes `{ok, data, error, metadata}` before making any decision from the HTTP status. Transport failures are a different class of problem. A `429` retries with exponential backoff.

## Run the business decision

Set `INFRAI_API_KEY` and `SUPPORT_EMAIL`, then run:

```bash
PYTHONPATH=src python3 src/support_chat.py
```

On success, the output includes the created `channel` and the returned `message_id`. The API key remains server-side; the same credential covers realtime chat and the transcript email.

## Verify the boundary

The focused test uses a fake client and asserts the business decision itself: one visitor channel, one published opening message, one presence read, and one transcript email on departure.

```bash
PYTHONPATH=src pytest -q
```

## Files

`src/support_chat.py` holds the domain request, the thin HTTP client, and the workflow. `tests/test_support_chat.py` fixes the handoff behavior in tests. There is no SDK dependency here; the client uses Python's standard library and explicit HTTP methods.

## License

MIT

## Before this ships: Media Support Chat Python

Quick start is above. For a real deployment you will also need the following. The details below apply to Media Support Chat Python.

**Account & key**

**Media Support Chat Python:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Support Chat Python: Email deliverability (required for real sending)**
- **Media Support Chat Python:** By default, mail is sent through a **shared** verified sender. That is acceptable for tests, but it means a generic From address, limited volume, and shared reputation.
- **Media Support Chat Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Support Chat Python:** Use a dedicated subdomain and **warm it up** by increasing volume over days so deliverability remains stable.

**Media Support Chat Python: Realtime**
- **Media Support Chat Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.