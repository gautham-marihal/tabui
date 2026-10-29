"""The bank's systems answer as the design says: logins, cheques, statements, cheque books, appointments, call-backs,
transfers, payments and cards, each for the person who holds what they act on."""

from conftest import call


def test_singapore_login_phone_code_and_pin_with_the_hosts_codes(client):
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "9999999"}) == {"ok": False, "code": 83, "reason": "invalid_phone_code"}
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "1234567"})["phone_code_valid"] is True
    ok = call(client, "POST", "/sg/as400/login", {"phone_code": "1234567", "pin": "246810"})
    assert ok == {"ok": True, "code": 0, "cif": "SG0001001", "user_type": "business", "access_level": "P", "person": "P001", "name": "Mr Tan"}
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "2468024", "pin": "000000"})["tries_left"] == 2
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "2468024", "pin": "000000"})["code"] == 53
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "2468024", "pin": "000000"})["code"] == 62, "the third wrong PIN locks it"
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "2468024", "pin": "112233"})["code"] == 62, "and the right PIN cannot open it"
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "2468024"})["reason"] == "locked", "a locked login says so at the phone code"


def test_a_wrong_current_pin_counts_towards_the_lock_when_changing_it(client):
    for _ in range(2):
        assert call(client, "POST", "/sg/as400/pin", {"phone_code": "1234567", "old_pin": "000000", "new_pin": "135135"})["reason"] == "invalid_pin"
    assert call(client, "POST", "/sg/as400/pin", {"phone_code": "1234567", "old_pin": "000000", "new_pin": "135135"})["reason"] == "locked"


def test_singapore_account_verification_dormant_wrong_nric_and_one_time_password(client):
    assert call(client, "POST", "/sg/siebel/account-login", {"account": "503000111222"})["dormant"] is True
    assert call(client, "POST", "/sg/siebel/account-login", {"account": "123"})["invalidAcct"] == "Y"
    assert call(client, "POST", "/sg/siebel/verify-contact", {"cif": "SG0002002", "nric_last4": "999Z"})["valid"] is False
    lim = call(client, "POST", "/sg/siebel/verify-contact", {"cif": "SG0002002", "nric_last4": "321b"})
    assert lim == {"valid": True, "person": "P003", "name": "Ms Lim"}
    assert call(client, "POST", "/sg/soa/otp/send", {"person": "P003"}) == {"sent": True, "to_mobile_ending": "7777", "valid_for_minutes": 5}
    assert call(client, "POST", "/sg/soa/otp/verify", {"person": "P003", "otp": "000000"})["valid"] is False
    assert call(client, "POST", "/sg/soa/otp/verify", {"person": "P003", "otp": "123456"})["valid"] is True
    assert call(client, "POST", "/sg/soa/otp/verify", {"person": "P003", "otp": "123456"})["reason"] == "no_otp_sent", "a password works once"


def test_three_wrong_one_time_passwords_suspend_the_person(client):
    call(client, "POST", "/sg/soa/otp/send", {"cif": "SG0002002"})
    assert call(client, "POST", "/sg/soa/otp/verify", {"cif": "SG0002002", "otp": "1"})["tries_left"] == 2
    call(client, "POST", "/sg/soa/otp/verify", {"cif": "SG0002002", "otp": "2"})
    assert call(client, "POST", "/sg/soa/otp/verify", {"cif": "SG0002002", "otp": "3"})["reason"] == "otp_suspended"
    assert call(client, "POST", "/sg/soa/otp/send", {"person": "P003"})["reason"] == "otp_suspended", "it is the person who is suspended"


def test_a_stop_order_is_checked_charged_and_kept(client):
    stop = call(client, "POST", "/sg/as400/cheques/501234567001/stop", {"cheque_no": "000232", "reason": "lost", "person": "P001"})
    assert stop == {"ok": True, "cheque_no": "000232", "fee": 30.0, "currency": "SGD", "reference": "STP-000002"}
    assert call(client, "GET", "/sg/as400/cheques/501234567001/000232?person=P001")["status"] == "stopped"
    history = call(client, "GET", "/hub/accounts/501234567001/history?person=P001&limit=1")["items"]
    assert history[0]["description"] == "Stop payment fee, cheque 000232" and history[0]["amount"] == -30.0, "the fee is taken from the account"
    again = call(client, "POST", "/sg/as400/cheques/501234567001/stop", {"cheque_no": "000232", "person": "P001"})
    assert again["reason"] == "already_stopped", "never stopped (and charged) twice"
    assert call(client, "POST", "/sg/as400/cheques/501234567001/stop", {"cheque_no": "000231", "person": "P001"})["reason"] == "already_paid"
    assert call(client, "POST", "/sg/as400/cheques/501234567001/stop", {"cheque_no": "999999", "person": "P001"})["reason"] == (
        "not_from_this_accounts_cheque_books"
    )
    assert call(client, "POST", "/sg/as400/cheques/501234567001/stop", {"cheque_no": "000240", "person": "P007"})["reason"] == "enquiries_only"
    assert call(client, "POST", "/sg/as400/cheques/501234567001/stop", {"cheque_no": "000240"})["reason"] == "caller_not_verified"
    assert call(client, "POST", "/sg/as400/cheques/7011223344/stop", {"cheque_no": "102231", "person": "P009"})["reason"] == "unknown_account", (
        "a Malaysian cheque is not stopped on the Singapore system"
    )


def test_statements_and_cheque_books_follow_the_price_list(client):
    statement = call(client, "POST", "/sg/soa/accounts/501234567001/statements", {"delivery": "mail", "person": "P001"})
    assert statement["ok"] and statement["fee"] == 5.0 and statement["arrives_in_days"] == 5 and statement["arrives_by"]
    old = call(client, "POST", "/sg/soa/accounts/501234567001/statements", {"month": "2020-01", "person": "P001"})
    assert old["reason"] == "month_not_available_by_phone"
    book = call(client, "POST", "/sg/soa/accounts/501234567001/cheque-book", {"delivery": "express", "person": "P001"})
    assert book["fee"] == 20.0 and book["ready_in_working_days"] == 3
    assert call(client, "POST", "/sg/soa/accounts/501234567002/cheque-book", {"person": "P001"})["reason"] == "account_has_no_cheques"
    assert call(client, "POST", "/sg/soa/accounts/503000111222/statements", {"person": "P004"})["reason"] == "account_dormant"


def test_appointments_offer_only_free_slots_ahead_and_a_booking_is_the_customers_own(client):
    slots = lambda: [s["slot_id"] for s in call(client, "GET", "/sg/cmm/appointments/slots?type=foreign_worker")["items"]]  # noqa: E731
    offered = slots()
    assert len(offered) == 3, "three at a time"
    booking = call(client, "POST", "/sg/cmm/appointments", {"slot_id": offered[0], "type": "foreign_worker", "cif": "SG0001001"})
    assert booking["ok"] and booking["booking_id"].startswith("BK-")
    assert offered[0] not in slots()
    assert call(client, "POST", "/sg/cmm/appointments", {"slot_id": offered[0], "cif": "SG0001001"})["reason"] == "slot_not_available"
    assert call(client, "POST", "/sg/cmm/appointments", {"slot_id": offered[1], "cif": "NOPE"})["reason"] == "unknown_customer"
    assert call(client, "GET", "/sg/cmm/appointments")["items"] == [], "no one's bookings without a customer"
    mine = call(client, "GET", "/sg/cmm/appointments?cif=SG0001001")["items"]
    assert [b["id"] for b in mine] == [booking["booking_id"]]
    assert call(client, "POST", f"/sg/cmm/appointments/{booking['booking_id']}/cancel", {"cif": "SG0002002"})["reason"] == "no_such_booking"
    assert call(client, "POST", f"/sg/cmm/appointments/{booking['booking_id']}/cancel", {"cif": "SG0001001"})["ok"] is True
    assert offered[0] in slots()


def test_a_call_back_is_asked_for_once(client):
    assert call(client, "POST", "/sg/cmm/callbacks", {"caller": "+6591234567", "number": "12"})["reason"] == "number_must_be_5_to_15_digits"
    first = call(client, "POST", "/sg/cmm/callbacks", {"caller": "+6591234567", "number": "+6591234567", "reason": "accounts"})
    assert first == {"ok": True, "request_id": "CB-000001", "number": "+6591234567"}
    assert call(client, "GET", "/sg/cmm/callbacks/91234567")["open"] is True, "a local number finds the call-back"
    again = call(client, "POST", "/sg/cmm/callbacks", {"caller": "91234567", "number": "91234567"})
    assert again["already_requested"] is True and again["request_id"] == "CB-000001"
    assert call(client, "GET", "/my/contact/callbacks/0123456789")["open"] is False, "a Malaysian number, the Malaysian list"


def test_malaysia_logins_key_code_phone_code_or_ic_and_a_tpin_change(client):
    assert call(client, "POST", "/my/core/login", {"key_code": "12345678", "tpin": "123456"})["cif"] == "MY1001"
    assert call(client, "POST", "/my/core/login", {"phone_code": "880101145678", "tpin": "654321"})["cif"] == "MY2002", "an IC number logs in too"
    assert call(client, "POST", "/my/core/login", {"phone_code": "55667788", "tpin": "135246"})["cif"] == "MY4004", "a Singaporean's Malaysian banking"
    assert call(client, "POST", "/my/core/login", {"phone_code": "87654321", "tpin": "000000"})["tries_left"] == 2
    changed = call(client, "POST", "/my/core/tpin", {"person": "P010", "old_tpin": "654321", "new_tpin": "112358", "confirm": "112358"})
    assert changed == {"ok": True}
    assert call(client, "POST", "/my/core/login", {"phone_code": "87654321", "tpin": "112358"})["ok"] is True


def test_a_transfer_between_own_accounts_by_their_last_four_digits(client):
    body = {"person": "P009", "from_account": "7011223344", "to_last4": "3366", "amount": "5000"}
    done = call(client, "POST", "/my/core/transfers/own", body)
    assert done["ok"] and done["from_last4"] == "3344" and done["to_last4"] == "3366" and done["new_balance_from"] == 251780.4
    assert call(client, "GET", "/hub/accounts/7011223366/balance?person=P009")["ledger_balance"] == 93400.0, "and arrives"
    different = call(client, "POST", "/my/core/transfers/own", {**body, "to_last4": "3355"})
    assert different["reason"] == "different_currencies"
    assert call(client, "POST", "/my/core/transfers/own", {**body, "to_last4": "4455"})["reason"] == "accounts_not_yours"
    assert call(client, "POST", "/my/core/transfers/own", {**body, "amount": 10_000_000})["reason"] == "insufficient_funds"
    assert call(client, "POST", "/my/core/transfers/own", {**body, "person": "P010"})["reason"] == "not_one_of_theirs"
    fd = call(client, "POST", "/my/core/transfers/own", {"person": "P010", "from_account": "7022334477", "to_last4": "4455", "amount": 1})
    assert fd["reason"] == "cannot_pay_from_this_account", "a fixed deposit is not drawn on by transfer"


def test_payments_go_only_to_what_the_customer_has(client):
    payees = call(client, "GET", "/my/core/people/P009/payees")
    assert [loan["id"] for loan in payees["loans"]] == ["LN-5521", "HP-3307"]
    assert [c["last4"] for c in payees["credit_cards"]] == ["8765"]
    assert [p["payee"] for p in payees["payees"]] == ["Landlord", "Pembekal Bina"]
    loan = call(client, "POST", "/my/core/payments/loan", {"person": "P009", "from_account": "7055667701", "loan": "HP-3307", "amount": "1238.81"})
    assert loan["ok"] and loan["paid_to"] == "HP-3307"
    assert call(client, "GET", "/my/core/people/P009/payees")["loans"][1]["arrears"] == 0.0, "the arrears are paid first"
    card = call(client, "POST", "/my/core/payments/credit_card", {"person": "P009", "from_account": "7055667701", "card": "8765", "amount": 206})
    assert card["ok"] and "ending 8765" in card["paid_to"]
    bill = call(client, "POST", "/my/core/payments/utility", {"person": "P010", "from_account": "7022334455", "bill": "Home electricity", "amount": 88.2})
    assert bill["paid_to"] == "Tenaga Nasional Berhad 220011443322"
    assert call(client, "POST", "/my/core/payments/utility", {"person": "P010", "from_account": "7022334455", "bill": "TNB-1", "amount": 1})["reason"] == (
        "not_a_registered_bill"
    )
    giro = call(client, "POST", "/my/core/payments/giro", {"person": "P010", "from_account": "7022334455", "payee": "mum", "amount": 300})
    assert giro["paid_to"] == "Rahmah binti Yusof at Maybank (account ending 7788)"
    stranger = call(client, "POST", "/my/core/payments/loan", {"person": "P010", "from_account": "7022334455", "loan": "LN-5521", "amount": 1})
    assert stranger["reason"] == "not_one_of_their_loans"
    usd = call(client, "POST", "/my/core/payments/giro", {"person": "P009", "from_account": "7011223355", "payee": "Pembekal Bina", "amount": 1})
    assert usd["reason"] == "pay_from_a_local_currency_account"


def test_cards_are_found_within_the_customer_and_act_as_a_bank_would(client):
    card = lambda digits, person="P010": call(client, "GET", f"/my/core/customers/MY2002/cards/{digits}?person={person}")  # noqa: E731
    assert card("4321")["status"] == "inactive" and card("4321")["annual_fee"] == 150.0
    assert card("8765")["reason"] == "not_one_of_their_cards", "another customer's card is not found here"
    assert card("4321", person="P009")["reason"] == "not_one_of_their_cards"
    act = lambda action, **body: call(client, "POST", f"/my/core/customers/MY2002/cards/4321/{action}", {"person": "P010", **body})  # noqa: E731
    assert act("activate")["status"] == "active"
    assert act("activate")["reason"] == "already_active"
    waived = act("fee-waiver")
    assert waived["waived"] == 150.0 and waived["until"]
    assert act("fee-waiver")["reason"] == "already_waived"
    assert act("credit-limit", new_limit=20000)["outcome"] == "review"
    assert act("credit-limit", new_limit=12000)["limit"] == 12000.0
    assert act("balance-transfer", amount=50000)["reason"] == "more_than_available_credit"
    assert act("balance-transfer", amount=3000, from_bank="Maybank")["outcome"] == "submitted"
    blocked = act("block", reason="lost")
    assert blocked["status"] == "blocked" and blocked["replacement_in_working_days"] == 7
    debit = card("5511")
    assert debit["kind"] == "debit_card" and debit["linked_account_last4"] == "4455"


def test_an_unknown_path_is_a_404_and_a_body_that_is_not_json_a_400(client):
    assert client.get("/sg/nowhere").status_code == 404
    assert client.get("/sg/cmm/surveys").status_code == 404, "a known path with the wrong method is not there either"
    assert client.post("/sg/cmm/surveys", content=b"{nope").status_code == 400
