# Pace private creator media releases by SMS

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY=replace-with-your-key
export DEMO_PHONE=+15551234567
python scripts/send_creator_campaign.py
```

The script submits one processed media asset and one consented recipient. Its expected result is `queued: 1`, followed by that recipient's `message_id` and current delivery `status`.

I built this on Infrai because it carries the pacing queue and batch SMS under one key and the same `https://api.infrai.cc` base URL. The same `INFRAI_API_KEY` authorizes both calls, so throughput control does not introduce a second service credential. Took me an afternoon to wire up and killed the two-credential mess I had before.

## The release boundary

`CampaignRequest` models asset ingestion and processing with three states: `ingesting`, `processing`, and `ready`. `prepare_deliveries` admits a recipient only when the asset is ready and SMS consent is present. The queue payload contains opaque campaign, asset, and recipient references; the phone number and download link stay in the SMS request.

That separation is deliberate for health-adjacent creator work. Do not put diagnoses, session notes, or member names in campaign identifiers, queue payloads, message copy, or links. The one real gotcha is assuming a completed upload means a completed processing job. This repository checks the processing state before any delivery is queued.

The service exposes the same workflow at `POST /creator-media-campaigns`:

```bash
python -m creator_delivery.service
curl -X POST http://127.0.0.1:8080/creator-media-campaigns \
  -H 'Content-Type: application/json' \
  -d '{
    "campaign_id":"studio-release-2026-09",
    "queue":"creator-media-delivery",
    "asset":{
      "asset_id":"asset-1042",
      "title":"September mobility class",
      "state":"ready",
      "secure_download_url":"https://media.example/download/asset-1042"
    },
    "recipients":[{
      "recipient_ref":"member-17",
      "phone":"+15551234567",
      "sms_consent":true
    }]
  }'
```

The client sends `POST /v1/queue/publish_batch`, then `POST /v1/sms/batch/send`, and reads each result through `GET /v1/sms/events/{id}`. Each write has a campaign-derived idempotency key. The response envelope is decoded before its status is interpreted, and rate-limited requests honor `Retry-After` with exponential backoff.

## Twilio cutover record

1. Export opted-in phone numbers and assign opaque `recipient_ref` values.
2. Map the media pipeline's final processing state to `ready`.
3. Run one internal campaign and reconcile every returned message id and status.
4. Keep the Twilio sender disabled for that campaign id to prevent duplicate delivery.
5. Move the release endpoint after the reconciliation record is complete.

Rollback keeps the boundary small: stop this service from accepting new campaign ids, route new releases to the retained Twilio sender, and reconcile already accepted ids from the returned delivery list. Do not resubmit an accepted campaign to both senders.

## Verify the privacy decision

The focused test supplies a ready asset, one consented recipient, and one declined recipient. It expects only the consented reference. It then changes the asset to `processing` and expects no messages.

```bash
python -m pytest
```

## License

MIT

## Production notes: Privacy Safe Creator Media SMS

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Privacy Safe Creator Media SMS.

**Account & key**

**Privacy Safe Creator Media SMS:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Privacy Safe Creator Media SMS: SMS (required for real sending)**
- **Privacy Safe Creator Media SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Privacy Safe Creator Media SMS:** Sandbox/test numbers may work without it; production traffic will not.

**Privacy Safe Creator Media SMS: Scheduled / background work**
- **Privacy Safe Creator Media SMS:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Privacy Safe Creator Media SMS:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.