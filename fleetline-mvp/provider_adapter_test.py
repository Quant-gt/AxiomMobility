#!/usr/bin/env python3
"""Contract tests for the deterministic mock provider adapters."""

from provider_adapters import ProviderRegistry


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS {message}")


def main() -> None:
    providers = ProviderRegistry.mock()
    payment = providers.payments.create_payment(amount_paise=12500, idempotency_key="payment-test-1")
    expect(payment.ok and payment.status == "succeeded" and payment.reference.startswith("mock_pay_"), "mock payment returns deterministic success")
    same = providers.payments.create_payment(amount_paise=12500, idempotency_key="payment-test-1")
    expect(same.reference == payment.reference, "mock payment is idempotency-key stable")
    message = providers.messaging.send(channel="sms", recipient="+919900000000", template="duty_started", idempotency_key="message-test-1")
    expect(message.status == "queued" and message.payload["channel"] == "sms", "mock messaging queues a notification")
    call = providers.telephony.create_masked_call(from_number="+910000000000", to_number="+919900000000", context="duty-test", idempotency_key="call-test-1")
    expect(call.payload["masked"] is True, "mock telephony never exposes direct numbers")
    route = providers.maps.route(pickup={"label": "BKC"}, dropoff={"label": "Airport"})
    expect(route.status == "estimated" and route.payload["distance_km"] > 0, "mock maps returns a route estimate")
    einvoice = providers.einvoice.issue(invoice_number="INV-TEST-1", total_paise=12500, idempotency_key="einvoice-test-1")
    expect(einvoice.status == "issued" and einvoice.payload["qr_payload"], "mock e-invoice returns IRN and QR payload")
    attachment = providers.storage.register_attachment(organization_id="org_test", entity_type="duty_proof", entity_id="duty_test", filename="proof.jpg", content_type="image/jpeg", size_bytes=2048)
    expect(attachment.status == "registered" and attachment.payload["storage_path"].startswith("mock/"), "mock storage returns an attachment path")
    print("RESULT provider adapter tests passed")


if __name__ == "__main__":
    main()
