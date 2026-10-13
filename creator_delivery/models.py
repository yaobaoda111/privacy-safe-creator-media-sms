from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AssetState(StrEnum):
    INGESTING = "ingesting"
    PROCESSING = "processing"
    READY = "ready"


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    title: str
    state: AssetState
    secure_download_url: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> MediaAsset:
        return cls(
            asset_id=str(value["asset_id"]),
            title=str(value["title"]),
            state=AssetState(value["state"]),
            secure_download_url=str(value["secure_download_url"]),
        )


@dataclass(frozen=True)
class CreatorRecipient:
    recipient_ref: str
    phone: str
    sms_consent: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CreatorRecipient:
        return cls(
            recipient_ref=str(value["recipient_ref"]),
            phone=str(value["phone"]),
            sms_consent=bool(value["sms_consent"]),
        )


@dataclass(frozen=True)
class CampaignRequest:
    campaign_id: str
    queue: str
    asset: MediaAsset
    recipients: tuple[CreatorRecipient, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CampaignRequest:
        allowed = {"campaign_id", "queue", "asset", "recipients"}
        if set(value) != allowed:
            raise ValueError(f"request fields must be: {', '.join(sorted(allowed))}")
        recipients = tuple(CreatorRecipient.from_dict(item) for item in value["recipients"])
        if not recipients:
            raise ValueError("recipients must not be empty")
        return cls(
            campaign_id=str(value["campaign_id"]),
            queue=str(value["queue"]),
            asset=MediaAsset.from_dict(value["asset"]),
            recipients=recipients,
        )


@dataclass(frozen=True)
class PreparedDelivery:
    recipient_ref: str
    to: str
    text: str


@dataclass(frozen=True)
class DeliveryStatus:
    recipient_ref: str
    message_id: str
    status: str

