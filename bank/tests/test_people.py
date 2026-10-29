"""People and the customer hub: one person logs in once and sees every account they may use, in both countries; the
lines serve them as the company they act for or as themselves; a caller is recognised by their number; and an account
is read only by someone who holds it."""

from conftest import call


def test_one_login_finds_the_person_and_serves_them_as_the_line_expects(client):
    sg = call(client, "POST", "/sg/as400/login", {"phone_code": "1234567", "pin": "246810"})
    assert (sg["person"], sg["cif"], sg["user_type"]) == ("P001", "SG0001001", "business"), "a director is served as their company"
    koh = call(client, "POST", "/sg/as400/login", {"phone_code": "1111111", "pin": "111111"})
    assert koh["user_type"] == "personal", "someone with only personal banking is told the personal line"
    ong = call(client, "POST", "/sg/as400/login", {"phone_code": "4433221", "pin": "556677"})
    assert ong["access_level"] == "AC", "Old Harbour Traders may only make enquiries"
    key = call(client, "POST", "/my/core/login", {"key_code": "12345678", "tpin": "123456"})
    assert (key["person"], key["cif"], key["line"]) == ("P009", "MY1001", "business")
    phone = call(client, "POST", "/my/core/login", {"phone_code": "22446688", "tpin": "123456"})
    assert (phone["person"], phone["cif"], phone["line"]) == ("P009", "MY5005", "consumer"), "the same person, as themselves"


def test_a_person_sees_every_account_they_hold_in_both_countries_home_first(client):
    tan = call(client, "GET", "/hub/people/P001/accounts?country=sg")
    assert tan["count"] == 7
    assert [a["last4"] for a in tan["items"]] == ["7001", "7002", "7003", "0101", "0103", "0102", "6601"]
    assert tan["items"][0]["whose"] == "for Acme Trading Pte Ltd" and tan["items"][5]["whose"] == "joint"
    assert tan["items"][-1]["country"] == "Malaysia"
    assert tan["spoken"].startswith("a Business Current Account in SGD ending 7001, for Acme Trading Pte Ltd; ")
    assert "an ACU Current Account in USD ending 7003" in tan["spoken"]
    assert "a Savings Account in SGD ending 0102, joint" in tan["spoken"]
    assert tan["spoken"].endswith("a Savings Account in MYR ending 6601 in Malaysia"), "only the other country is named"
    from_malaysia = call(client, "GET", "/hub/people/P001/accounts?country=my")
    assert from_malaysia["items"][0]["last4"] == "6601", "the line's country comes first"
    wife = call(client, "GET", "/hub/people/P002/accounts")
    assert {a["last4"] for a in wife["items"]} == {"0201", "0202", "0102"}, "her own two, and the joint one"
    chua = call(client, "GET", "/hub/people/P007/accounts")
    assert all(not a["can_transact"] for a in chua["items"]), "a signatory for enquiries only"
    ong = call(client, "GET", "/hub/people/P004/accounts")
    assert "ending 1222 (dormant)" in ong["spoken"], "a dormant account is listed, and says so"


def test_choosing_an_account_by_its_last_digits_and_reading_it_in_either_country(client):
    chosen = call(client, "GET", "/hub/people/P001/accounts/6601")
    assert (chosen["found"], chosen["number"], chosen["market"], chosen["cif"]) == (True, "7044556601", "my", "MY4004")
    assert call(client, "GET", "/hub/people/P001/accounts/9999") == {"found": False, "reason": "not_one_of_theirs"}
    assert call(client, "GET", "/hub/people/P002/accounts/0101")["found"] is False, "not her husband's own account"
    assert call(client, "GET", "/hub/people/P001/accounts/01")["found"] is False, "two digits are not enough"
    assert call(client, "GET", "/hub/accounts/7044556601/balance?person=P001")["ledger_balance"] == 22500.0
    assert len(call(client, "GET", "/hub/accounts/7044556601/history?person=P001&limit=3")["items"]) == 3


def test_an_account_is_read_only_by_someone_who_holds_it(client):
    assert call(client, "GET", "/hub/accounts/7044556601/balance?person=P002")["reason"] == "not_one_of_theirs"
    assert call(client, "GET", "/hub/accounts/7044556601/balance")["reason"] == "caller_not_verified"
    assert call(client, "GET", "/hub/accounts/7044556601/history?person=P009")["items"] == []
    assert call(client, "GET", "/sg/soa/accounts/501234567001/balance?person=P003")["reason"] == "not_one_of_theirs"


def test_the_available_balance_is_the_ledger_less_holds(client):
    acme = call(client, "GET", "/hub/accounts/501234567001/balance?person=P001")
    assert acme["ledger_balance"] == 128450.75 and acme["available_balance"] == 126900.75
    assert acme["on_hold"] == 1550.0 and acme["holds"] == ["GIRO payment to Keppel Packaging scheduled"]
    dormant = call(client, "GET", "/hub/accounts/503000111222/balance?person=P004")
    assert dormant["status"] == "dormant" and dormant["ledger_balance"] == 12.5 and dormant["available_balance"] == 0.0


def test_a_caller_is_recognised_by_their_number(client):
    tan = call(client, "GET", "/hub/callers/91234567")
    assert tan == {"found": True, "person": "P001", "name": "Mr Tan", "language": "en", "favourite": "balance", "is_vip": False}
    assert call(client, "GET", "/hub/callers/+6598765432")["is_vip"] is True
    assert call(client, "GET", "/hub/callers/0123456789")["name"] == "Encik Ahmad", "a Malaysian number dialled at home"
    assert call(client, "GET", "/hub/callers/80000000")["found"] is False


def test_who_a_person_banks_as(client):
    ahmad = call(client, "GET", "/hub/people/P009")
    assert {(b["cif"], b["role"]) for b in ahmad["banks_as"]} == {("MY1001", "director"), ("MY5005", "owner"), ("SG1000909", "owner")}
    assert call(client, "GET", "/hub/people/P005")["open_cases"][0]["case"] == "INV-77120"


def test_the_nric_check_takes_any_of_the_people_acting_for_the_company(client):
    assert call(client, "POST", "/sg/siebel/verify-contact", {"cif": "SG0001001", "nric_last4": "567a"})["valid"] is True
    assert call(client, "POST", "/sg/siebel/verify-contact", {"cif": "SG0001001", "nric_last4": "112G"})["valid"] is True, "the signatory too"
    assert call(client, "POST", "/sg/siebel/verify-contact", {"cif": "SG0001001", "nric_last4": "321B"})["valid"] is False


def test_vips_are_people(client):
    goh = call(client, "GET", "/sg/cmm/vip/98765432")
    assert (goh["name"], goh["person"], goh["vip_type"], goh["last_service_manager"]["name"]) == ("Mr Goh", "P005", "account", "Rachel Ng")
    assert call(client, "POST", "/sg/cmm/vip/98765432/check-account", {"account": "509876543210"})["valid"] is True
    assert call(client, "GET", "/sg/cmm/vip/91234567") == {"found": False}
