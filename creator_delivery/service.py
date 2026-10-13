from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .campaign import launch_campaign
from .infrai_client import InfraiClient, InfraiError, TransportError
from .models import CampaignRequest


class CampaignHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/creator-media-campaigns":
            self._json(404, {"error": "route_not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = json.loads(self.rfile.read(length))
            request = CampaignRequest.from_dict(raw)
            result = launch_campaign(InfraiClient(), request)
            self._json(202, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": "invalid_request", "message": str(exc)})
        except InfraiError as exc:
            client_status = exc.status if 400 <= exc.status < 500 else 502
            self._json(client_status, {"error": exc.code, "message": str(exc)})
        except TransportError as exc:
            self._json(502, {"error": "upstream_transport", "message": str(exc)})

    def _json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), CampaignHandler)
    print(f"creator delivery service listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

