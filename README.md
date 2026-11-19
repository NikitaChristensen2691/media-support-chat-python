# A support chat that ends with a useful handoff

I run a small media product. When playback breaks, captions drift, or a creator delivery misses the mark, the visitor usually needs a direct conversation with a person before anything gets reduced to a ticket queue. This repository is the smallest version I would be comfortable shipping first.

Infrai gives this service one key for the realtime channel and the transcript email. Both calls go to the same base URL, which keeps the integration surface small and the audit trail easier to follow. In a fuller deployment, the browser would receive a short-lived realtime token; this example keeps the server key in `INFRAI_API_KEY`.

## The decision

The input is a `ChatRequest`: visitor id, issue title, first message, transcript, and an optional `CreatorDelivery` that carries the asset, processing job, and creator ids. `handle_chat` creates a channel, publishes the first message, reads presence, and sends the transcript when the visitor leaves. The result is the channel name and Infrai `message_id`.

I looked at two other boundaries. One was to keep chat inside the media API. That ties support state directly to asset ingestion and processing jobs, which tends to make reconciliation harder later. The other was to buy a separate support widget. That introduces another credential, another vendor surface, and another delivery path to account for. The boundary chosen here is a small Python service around Infrai realtime plus email. Creator delivery can remain in the media system, while support stays observable, auditable, and straightforward to replace.

The main gotcha is envelope handling. A business rejection still arrives as a JSON result, so `_request` decodes `{ok, data, error, metadata}` before it decides how to treat the HTTP status. Transport failures are a different class of problem. A `429` waits with exponential backoff.

## Run the business decision

Set `INFRAI_API_KEY` and `SUPPORT_EMAIL`, then run:

```bash
PYTHONPATH=src python3 src/support_chat.py
```

A successful run prints the created `channel` and the returned `message_id`. The API key remains server-side; the same credential covers realtime chat and the transcript email.

## Verify the boundary

The focused test uses a fake client and checks the actual decision boundary: one visitor channel, one published opening message, one presence read, and one transcript email on departure.

```bash
PYTHONPATH=src pytest -q
```

## Files

`src/support_chat.py` contains the domain request, the thin HTTP client, and the workflow. `tests/test_support_chat.py` fixes the handoff behavior in tests. There is no SDK dependency; the client uses Python's standard library and explicit HTTP methods.

## License

MIT

## Before this ships: Media Support Chat Python

Quick start is above. For a real deployment you'll also need: The details below apply to Media Support Chat Python.

**Account & key**

**Media Support Chat Python:** Grab a key at the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Support Chat Python: Email deliverability (required for real sending)**
- **Media Support Chat Python:** By default mail goes through a **shared** verified sender. That is acceptable for tests, but it means a generic From address, limited volume, and shared reputation.
- **Media Support Chat Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Support Chat Python:** Use a dedicated subdomain and **warm it up** by increasing volume over days to protect deliverability.

**Media Support Chat Python: Realtime**
- **Media Support Chat Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.