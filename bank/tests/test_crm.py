"""The CRM routes (/crm/...): they ask for the key, show masked records, check PINs without handing them out, and keep
what a call leaves behind (hand-overs, call-backs, service requests) with the customer."""

import pytest

KEY = {"Authorization": "Bearer test-crm-key"}


def get(client, path):
    return client.get(path, headers=KEY).json()


def post(client, path, body):
    return client.post(path, json=body, headers=KEY).json()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "test-crm-key x"}])
def test_every_crm_route_asks_for_the_key(client, headers):
    for path in ["/crm/health", "/crm/customers", "/crm/customers/SG0001001", "/crm/activity"]:
        response = client.get(path, headers=headers)
        assert response.status_code == 401, path
        assert response.json() == {"error": "missing_or_wrong_key"}


def test_health_and_summary(client):
    assert get(client, "/crm/health") == {"ok": True, "database": "up", "customers": 19}
    summary = get(client, "/crm/summary")
    assert (summary["people"], summary["customers"], summary["accounts"], summary["cards"]) == (12, 19, 38, 5)


def test_customers_are_found_by_name_the_people_behind_them_cif_or_last_digits_and_shown_masked(client):
    assert {c["cif"] for c in get(client, "/crm/customers?q=acme")["items"]} == {"SG0001001"}
    assert [c["cif"] for c in get(client, "/crm/customers?q=7001")["items"]] == ["SG0001001"], "the last digits of an account"
    assert [c["cif"] for c in get(client, "/crm/customers?q=MY2002")["items"]] == ["MY2002"]
    assert "SG0001001" in {c["cif"] for c in get(client, "/crm/customers?q=Chua")["items"]}, "by a signatory's name"
    assert len(get(client, "/crm/customers?market=my")["items"]) == 7
    acme = get(client, "/crm/customers?q=acme")["items"][0]
    assert acme["contact"] == "Tan Wei Ming" and acme["mobile"] == "+65 ****4567" and acme["accounts"] == 3


def test_a_customers_whole_picture_with_nothing_confidential(client):
    acme = get(client, "/crm/customers/SG0001001")
    assert [a["number"] for a in acme["accounts"]] == ["****7001", "****7002", "****7003"]
    assert acme["accounts"][0]["ledger_balance"] == 128450.75 and acme["accounts"][0]["product"] == "Business Current Account"
    assert {p["name"] for p in acme["people"]} == {"Tan Wei Ming", "Chua Li Ting"}
    assert acme["registration_number"] == "201512345K" and acme["service_manager"] == "Daniel Lee"
    text = str(acme)
    for secret in ("501234567001", "246810", "1234567", "+6591234567"):
        assert secret not in text, secret
    lim = get(client, "/crm/customers/SG0002002")
    assert lim["cases"] == [{"id": "INV-77098", "topic": "Returned cheque 009812", "service_manager": "Daniel Lee", "account": "****3579"}]
    aisyah = get(client, "/crm/customers/MY2002")
    assert [c["number"] for c in aisyah["cards"]] == ["****4321", "****5511"] and aisyah["cards"] and aisyah["iq_member"] is True
    assert aisyah["loans"][0]["outstanding"] == 372915.2
    assert client.get("/crm/customers/NOPE", headers=KEY).status_code == 404


def test_transactions_by_account_or_all(client):
    one = get(client, "/crm/customers/SG0001001/transactions?account=7001&limit=2")["items"]
    assert one[0]["description"] == "FAST payment to Sunrise Supplies" and one[0]["balance"] == 128450.75
    assert all(t["account"] == "****7001" for t in one)
    assert len(get(client, "/crm/customers/SG0001001/transactions")["items"]) == 10, "the newest ten, by default"


def test_who_is_calling_from_their_number(client):
    tan = get(client, "/crm/lookup?phone=91234567")
    assert (tan["person"], tan["cif"], tan["name"], tan["language"], tan["is_vip"]) == ("P001", "SG0001001", "Tan Wei Ming", "en", False)
    vip = get(client, "/crm/lookup?phone=%2B6598765432")
    assert vip["is_vip"] is True and vip["service_manager"] == "Rachel Ng"
    assert get(client, "/crm/lookup?phone=80000000") == {"found": False}


def test_verify_checks_a_pin_or_tpin_and_locks_after_three_wrong_tries(client):
    assert post(client, "/crm/verify", {"code": "1234567", "secret": "246810"})["cif"] == "SG0001001"
    assert post(client, "/crm/verify", {"code": "12345678", "secret": "123456"})["cif"] == "MY1001", "a key code and TPIN"
    assert post(client, "/crm/verify", {"code": "880101145678", "secret": "654321"})["cif"] == "MY2002", "an IC number"
    assert post(client, "/crm/verify", {"cif": "SG0004004", "secret": "112233"})["verified"] is True
    assert post(client, "/crm/verify", {"cif": "SG0001001", "person": "P007", "secret": "778899"})["person"] == "P007", "a named signatory"
    assert post(client, "/crm/verify", {"code": "9999999", "secret": "1"})["reason"] == "unknown_customer"
    assert post(client, "/crm/verify", {"cif": "SG0004004", "secret": "0"})["tries_left"] == 2
    post(client, "/crm/verify", {"cif": "SG0004004", "secret": "0"})
    assert post(client, "/crm/verify", {"cif": "SG0004004", "secret": "0"})["reason"] == "locked"
    assert post(client, "/crm/verify", {"cif": "SG0004004", "secret": "112233"})["reason"] == "locked"


def test_one_time_passwords(client):
    assert post(client, "/crm/otp/send", {"cif": "NOPE"})["reason"] == "unknown_customer"
    assert post(client, "/crm/otp/send", {"cif": "SG0002002"}) == {"sent": True, "to_mobile_ending": "7777", "valid_for_minutes": 5}
    assert post(client, "/crm/otp/verify", {"cif": "SG0002002", "code": "000000"})["tries_left"] == 2
    assert post(client, "/crm/otp/verify", {"cif": "SG0002002", "code": "123456"}) == {"valid": True}
    assert post(client, "/crm/otp/verify", {"cif": "SG0002002", "code": "123456"})["reason"] == "no_otp_sent"


def test_what_a_call_leaves_behind_is_kept_with_the_customer(client):
    handed = post(
        client,
        "/crm/hand-overs",
        {"cif": "MY2002", "queue": "cards", "reason": "Card blocked abroad", "summary": "Verified. Card 4321 blocked in Bangkok.", "priority": "high"},
    )
    assert handed == {"ok": True, "reference": "HO-000001", "queue": "cards", "estimated_wait_s": 30}
    assert post(client, "/crm/hand-overs", {"queue": "x"})["reason"] == "customer_or_market_required"
    assert post(client, "/crm/hand-overs", {"market": "sg", "queue": "general"})["estimated_wait_s"] == 90, "an unknown caller with a market"
    assert post(client, "/crm/callbacks", {"cif": "MY2002", "number": "+60 12-345 6789", "reason": "after 6pm"})["reference"] == "CB-000001"
    assert post(client, "/crm/callbacks", {"cif": "MY2002", "number": "+60 12-345 6789"})["already_requested"] is True
    assert post(client, "/crm/callbacks", {"cif": "MY2002", "number": "12"})["reason"] == "number_must_be_5_to_15_digits"
    assert post(client, "/crm/service-requests", {"cif": "MY2002", "type": "card replacement", "account_last4": "4455"})["sr_number"] == "SR-0000001"
    aisyah = get(client, "/crm/customers/MY2002")
    assert aisyah["hand_overs"][0]["summary"] == "Verified. Card 4321 blocked in Bangkok."
    assert aisyah["callbacks"][0]["number"] == "+60 ****6789" and aisyah["service_requests"][0]["id"] == "SR-0000001"
    kinds = [a["kind"] for a in get(client, "/crm/activity")["items"]]
    assert kinds[:3] == ["service_request", "callback_requested", "hand_over"], "newest first"
