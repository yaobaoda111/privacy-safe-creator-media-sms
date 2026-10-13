from __future__ import annotations

from typing import Any

from .infrai_client import InfraiClient
from .models import AssetState, CampaignRequest, DeliveryStatus, PreparedDelivery


def prepare_deliveries(request: CampaignRequest) -> list[PreparedDelivery]:
    if request.asset.state is not AssetState.READY:
        return []
    return [
        PreparedDelivery(
            recipient_ref=recipient.recipient_ref,
            to=recipient.phone,
            text=f"{request.asset.title} is ready: {request.asset.secure_download_url}",
        )
        for recipient in request.recipients
        if recipient.sms_consent
    ]


def launch_campaign(infrai: InfraiClient, request: CampaignRequest) -> dict[str, Any]:
    deliveries = prepare_deliveries(request)
    if not deliveries:
        return {"campaign_id": request.campaign_id, "queued": 0, "deliveries": []}

    queue_key = f"{request.campaign_id}:queue"
    send_key = f"{request.campaign_id}:send"
    infrai.queue.publish_batch(
        request.queue,
        [
            {
                "campaign_id": request.campaign_id,
                "asset_id": request.asset.asset_id,
                "recipient_ref": delivery.recipient_ref,
            }
            for delivery in deliveries
        ],
        queue_key,
    )
    sent = infrai.sms.batch.send(
        [{"to": delivery.to, "text": delivery.text} for delivery in deliveries], send_key
    )

    results = sent.get("results", [])
    statuses: list[DeliveryStatus] = []
    for delivery, result in zip(deliveries, results, strict=False):
        message_id = str(result["message_id"])
        event = infrai.sms.events(message_id)
        statuses.append(
            DeliveryStatus(
                recipient_ref=delivery.recipient_ref,
                message_id=message_id,
                status=str(event.get("status", result.get("status", "accepted"))),
            )
        )
    return {
        "campaign_id": request.campaign_id,
        "queued": len(deliveries),
        "deliveries": [status.__dict__ for status in statuses],
    }

