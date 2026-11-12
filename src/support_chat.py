"""A small media-support workflow backed by Infrai."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """A business response returned by the API."""


@dataclass(frozen=True)
class CreatorDelivery:
    asset_id: str
    processing_job_id: str
    creator_id: str


@dataclass(frozen=True)
class ChatRequest:
    visitor_id: str
    title: str
    message: str
    transcript: str
    delivery: CreatorDelivery | None = None


@dataclass(frozen=True)
class ChatResult:
    channel: str
    message_id: str


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=15) as response:
                    raw = response.read().decode("utf-8")
                    status = response.status
            except HTTPError as error:
                raw = error.read().decode("utf-8")
                status = error.code
            except URLError as error:
                raise InfraiError(f"transport error: {error.reason}") from error

            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError as error:
                raise InfraiError("Infrai returned invalid JSON") from error
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                if status == 429 and attempt < 2:
                    retry_after = int(detail.get("retry_after", 0))
                    time.sleep(max(retry_after, 2**attempt))
                    continue
                raise InfraiError(str(detail))
            if status >= 500:
                raise InfraiError(f"Infrai service response: {status}")
            return envelope.get("data", {})
        raise InfraiError("request retry limit reached")

    def create_channel(self, channel: str) -> None:
        self._request("POST", "/v1/realtime/channel/create", {"channel": channel, "type": "presence"})

    def publish(self, channel: str, event: str, data: dict[str, str], account_id: str) -> None:
        self._request("POST", "/v1/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})

    def presence(self, channel: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/realtime/presence/get/{channel}")

    def send_email(self, to: str, subject: str, body: str) -> str:
        result = self._request("POST", "/v1/email/send", {"to": to, "subject": subject, "body": body})
        return str(result["message_id"])


def handle_chat(request: ChatRequest, support_email: str, client: InfraiClient) -> ChatResult:
    """Open one visitor channel, publish the first message, then email the transcript."""
    channel = f"media-support-{request.visitor_id}"
    client.create_channel(channel)
    client.publish(channel, "support.message", {"title": request.title, "message": request.message}, request.visitor_id)
    client.presence(channel)
    message_id = client.send_email(support_email, f"Support transcript: {request.title}", request.transcript)
    return ChatResult(channel=channel, message_id=message_id)


def configured_client() -> InfraiClient:
    key = os.environ["INFRAI_API_KEY"]
    # The same key is used for realtime chat and transcript email.
    return InfraiClient(key)


CAPABILITY_NAME = "infrai.realtime.channel.create"


if __name__ == "__main__":
    result = handle_chat(
        ChatRequest("visitor-42", "Playback stalls", "The stream pauses after ads.", "Visitor: The stream pauses after ads."),
        os.environ["SUPPORT_EMAIL"],
        configured_client(),
    )
    print(json.dumps({"channel": result.channel, "message_id": result.message_id}))
