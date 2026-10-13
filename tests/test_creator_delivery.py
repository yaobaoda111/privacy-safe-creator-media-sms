from creator_delivery.campaign import prepare_deliveries
from creator_delivery.models import CampaignRequest


def test_only_consented_recipients_receive_a_finished_asset() -> None:
    ready = CampaignRequest.from_dict(
        {
            "campaign_id": "release-7",
            "queue": "creator-media-delivery",
            "asset": {
                "asset_id": "asset-7",
                "title": "Breathing class recording",
                "state": "ready",
                "secure_download_url": "https://media.example/download/asset-7",
            },
            "recipients": [
                {"recipient_ref": "allowed", "phone": "+15550000001", "sms_consent": True},
                {"recipient_ref": "declined", "phone": "+15550000002", "sms_consent": False},
            ],
        }
    )
    assert [item.recipient_ref for item in prepare_deliveries(ready)] == ["allowed"]

    processing = CampaignRequest(
        campaign_id=ready.campaign_id,
        queue=ready.queue,
        asset=ready.asset.__class__(
            asset_id=ready.asset.asset_id,
            title=ready.asset.title,
            state=ready.asset.state.__class__.PROCESSING,
            secure_download_url=ready.asset.secure_download_url,
        ),
        recipients=ready.recipients,
    )
    assert prepare_deliveries(processing) == []

