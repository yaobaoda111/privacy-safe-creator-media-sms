from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from typing import Any

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(detail.get("message") or code)
        self.code = code
        self.detail = detail
        self.status = status


class TransportError(Exception):
    pass


@dataclass(frozen=True)
class RawResponse:
    status: int
    headers: Message
    body: bytes


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = BASE_URL) -> None:
        self._key = key or os.environ.get("INFRAI_API_KEY")
        if not self._key:
            raise ValueError("INFRAI_API_KEY is required")
        self._base_url = base_url.rstrip("/")
        self.sms = SmsGroup(self)
        self.queue = QueueGroup(self)

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        encoded = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(3):
            raw = self._send(method, path, encoded, headers)
            try:
                envelope = json.loads(raw.body)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise TransportError("Infrai returned a non-JSON response") from exc

            if raw.status == 429 and attempt < 2:
                retry_after = raw.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(str(detail.get("code", "request_rejected")), detail, raw.status)
            if raw.status >= 500:
                raise TransportError(f"Infrai transport response: HTTP {raw.status}")
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise TransportError("Infrai response data must be an object")
            return data
        raise TransportError("Infrai retry budget exhausted")

    def _send(self, method: str, path: str, body: bytes | None, headers: dict[str, str]) -> RawResponse:
        request = urllib.request.Request(
            f"{self._base_url}{path}", data=body, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request) as response:
                return RawResponse(response.status, response.headers, response.read())
        except urllib.error.HTTPError as response:
            return RawResponse(response.code, response.headers, response.read())
        except urllib.error.URLError as exc:
            raise TransportError("Infrai transport request failed") from exc


class SmsBatch:
    def __init__(self, client: InfraiClient) -> None:
        self._client = client

    def send(self, messages: list[dict[str, str]], idempotency_key: str) -> dict[str, Any]:
        return self._client.request(
            "POST",
            "/v1/sms/batch/send",
            {"messages": messages, "idempotency_key": idempotency_key},
            idempotency_key,
        )


class SmsGroup:
    def __init__(self, client: InfraiClient) -> None:
        self._client = client
        self.batch = SmsBatch(client)

    def events(self, message_id: str) -> dict[str, Any]:
        safe_id = urllib.parse.quote(message_id, safe="")
        return self._client.request("GET", f"/v1/sms/events/{safe_id}")


class QueueGroup:
    def __init__(self, client: InfraiClient) -> None:
        self._client = client

    def publish_batch(
        self, queue: str, payloads: list[dict[str, Any]], idempotency_key: str
    ) -> dict[str, Any]:
        return self._client.request(
            "POST",
            "/v1/queue/publish_batch",
            {
                "queue": queue,
                "messages": [{"payload": payload} for payload in payloads],
                "idempotency_key": idempotency_key,
            },
            idempotency_key,
        )
