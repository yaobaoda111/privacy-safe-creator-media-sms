from __future__ import annotations

import json
import os

from creator_delivery.campaign import launch_campaign
from creator_delivery.infrai_client import InfraiClient
from creator_delivery.models import CampaignRequest


def main() -> None:
    phone = os.environ.get("DEMO_PHONE")
    if not phone:
        raise SystemExit("DEMO_PHONE is required")
    request = CampaignRequest.from_dict(
        {
            "campaign_id": "studio-release-2026-09",
            "queue": "creator-media-delivery",
            "asset": {
                "asset_id": "asset-1042",
                "title": "September mobility class",
                "state": "ready",
                "secure_download_url": "https://media.example/download/asset-1042",
            },
            "recipients": [
                {"recipient_ref": "member-17", "phone": phone, "sms_consent": True}
            ],
        }
    )
    print(json.dumps(launch_campaign(InfraiClient(), request), indent=2))


if __name__ == "__main__":
    main()

