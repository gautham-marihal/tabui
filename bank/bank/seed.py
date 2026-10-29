"""The made-up bank's starting data, for the Singapore and Malaysia lines (docs: "Business Banking Phone Agents: Weave
Design"). Every name, number and code is invented. The logins a tester uses are listed in bank/README.md; here they are
hashed on the way in.

    python -m bank.seed            empty every table, then load this data (the "reset" of the mock bank)

The data holds together the way a bank's does:
- every account's ledger balance is its "balance brought forward" plus every posting since, and each posting keeps the
  balance it left; what cannot be spent yet is a hold (a cheque in clearing, a payment earmarked for a date);
- a cheque paid, a cheque paid in, a transfer, a loan instalment, a direct debit, a bill: each is also a posting, on
  both accounts when the money stays in the bank;
- dates count back (history) and forward (maturities, due dates, appointment slots) from today in the country's time.
"""

import random
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal
from .models import (
    AccessLevel,
    Account,
    AccountHolder,
    AccountStatus,
    Address,
    AddressKind,
    ApplicationStatus,
    AppointmentSlot,
    BankIdentity,
    Bill,
    Biller,
    Branch,
    Card,
    CardApplication,
    CardStatus,
    ChequeBook,
    ChequeDeposit,
    ChequeStatus,
    ContactPoint,
    Credential,
    CredentialKind,
    Customer,
    CustomerType,
    DepositRate,
    DepositStatus,
    DirectDebit,
    DocumentType,
    ExchangeRate,
    FixedDeposit,
    Form,
    Hold,
    HolderRole,
    IdentifierKind,
    IdentityDocument,
    IncomingFund,
    IncomingFundStatus,
    Investigation,
    IssuedCheque,
    LendingRate,
    Loan,
    LoginIdentifier,
    MandateStatus,
    Market,
    Maturity,
    Payee,
    Person,
    Product,
    ProductCategory,
    Promotion,
    PublicHoliday,
    Relationship,
    RelationshipRole,
    RiskRating,
    Segment,
    ServiceCode,
    ServiceManager,
    Setting,
    StopPayment,
    Tariff,
    Transaction,
    Vip,
    VipCheck,
)
from .security import fingerprint, hash_secret, last4

SG, MY = Market.SG, Market.MY
CENT = Decimal("0.01")


def D(value: str | float) -> Decimal:
    return Decimal(str(value))


# ---- the bank in each country: (market, bank, country, currency, time zone, dialling code, trunk prefix,
#      local number pattern, account number digits, GIRO bank code, SWIFT, branch code note)
BANK_IDENTITY = [
    (SG, "OCBC Bank (Singapore)", "Singapore", "SGD", "Asia/Singapore", "65", "", r"[3689]\d{7}", 12, "7339", "OCBCSGSG",
     "The branch code is the first three digits of the account number."),
    (MY, "OCBC Bank (Malaysia) Berhad", "Malaysia", "MYR", "Asia/Kuala_Lumpur", "60", "0", r"0\d{8,10}", 10, "OCBCMYKL", "OCBCMYKL",
     "No branch code is needed for IBG or DuitNow transfers."),
]  # fmt: skip

CURRENCY = {row[0]: row[3] for row in BANK_IDENTITY}

# "today" for the starting data: the bank's own clock (both countries keep the same time)
TODAY = datetime.now(ZoneInfo(BANK_IDENTITY[0][4])).date()


def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def months_ago(n: int, day: int = 1) -> date:
    """The given day of the month n months back (a negative n: ahead)."""
    year, month = divmod(TODAY.year * 12 + TODAY.month - 1 - n, 12)
    return date(year, month + 1, min(day, 28))


# ---- the rules the systems follow: (market or None for both, name, value, what it is)
SETTINGS = [
    (None, "max_wrong_otps", "3", "Wrong one-time passwords before the feature is suspended"),
    (None, "otp_lifetime_minutes", "5", "How long a one-time password works"),
    (None, "callback_number_min_digits", "5", "Shortest call-back number accepted"),
    (None, "callback_number_max_digits", "15", "Longest call-back number accepted"),
    (SG, "max_wrong_pins", "3", "Wrong phone PINs before the login is locked"),
    (SG, "history_items", "5", "Postings read out by default"),
    (SG, "statement_months_by_phone", "3", "Statement copies that can be asked for by phone (months back)"),
    (SG, "fx_indicative_limit", "40000", "Indicative FX rates apply below this amount (local currency)"),
    (SG, "slots_offered", "3", "Appointment slots offered at once"),
    (SG, "queue_wait_high_s", "20", "Expected wait in a high-priority queue (seconds)"),
    (SG, "queue_wait_normal_s", "90", "Expected wait in a normal queue (seconds)"),
    (SG, "fax_number_min_digits", "8", "Shortest fax number accepted"),
    (MY, "max_wrong_pins", "3", "Wrong TPINs before the login is locked"),
    (MY, "history_items", "5", "Postings read out by default"),
    (MY, "payments_cutoff", "20:00", "Payments and transfers after this time take effect the next working day"),
    (MY, "slots_offered", "3", "Appointment slots offered at once"),
    (MY, "queue_wait_high_s", "30", "Expected wait in a high-priority queue (seconds)"),
    (MY, "queue_wait_normal_s", "120", "Expected wait in a normal queue (seconds)"),
    (MY, "fax_number_min_digits", "9", "Shortest fax number accepted"),
]

# ---- the price list: (market, code, what it is, fee, currency, working days)
TARIFFS = [
    (SG, "stop_cheque", "Stop payment of a cheque", "30", "SGD", 0),
    (SG, "cheque_book_normal", "Cheque book, posted", "0", "SGD", 7),
    (SG, "cheque_book_express", "Cheque book, express courier", "20", "SGD", 3),
    (SG, "cheque_book_same_day", "Cheque book, same-day collection at a branch", "20", "SGD", 0),
    (SG, "statement_mail", "Copy of a statement, posted", "5", "SGD", 5),
    (SG, "statement_fax", "Copy of a statement, by fax", "5", "SGD", 0),
    (MY, "stop_cheque", "Stop payment of a cheque", "10", "MYR", 0),
    (MY, "cheque_book_normal", "Cheque book, posted", "0", "MYR", 7),
    (MY, "statement_mail", "Copy of a statement, posted", "5", "MYR", 7),
    (MY, "credit_limit_review", "Credit limit increase review", "0", "MYR", 3),
    (MY, "balance_transfer", "Balance transfer from another bank's card", "0", "MYR", 5),
    (MY, "card_replacement", "Replacement of a lost or stolen card", "12", "MYR", 7),
]

# ---- phone lines and desks: (market, code, label, as told, as dialled, hours (empty: around the clock), hours as said)
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
CONTACT_POINTS = [
    (SG, "business_line", "Business Banking line", "6538 1111", "+6565381111", [], "24 hours"),
    (SG, "service_centre", "Commercial Service Centre (service managers)", "6538 1111", "+6565381111",
     [{"days": WEEKDAYS, "start": "08:30", "end": "18:00"}], "8:30 am to 6:00 pm, Monday to Friday"),
    (SG, "vip_line", "Business Banking VIP line", "6538 2222", "+6565382222", [], "24 hours"),
    (SG, "investigations_line", "Investigations line", "6586 5292", "+6565865292", [], "24 hours"),
    (SG, "personal_line", "Personal Banking line", "1800 363 3333", "+6518003633333", [], "24 hours"),
    (SG, "trade_hotline", "Trade hotline", "6318 7777", "+6563187777",
     [{"days": WEEKDAYS, "start": "08:30", "end": "17:30"}], "8:30 am to 5:30 pm, Monday to Friday"),
    (SG, "card_centre", "24-hour card centre", "6538 1999", "+6565381999", [], "24 hours"),
    (MY, "business_line", "Business Banking (General)", "1300 88 7000", "+601300887000", [], "24 hours"),
    (MY, "islamic_line", "Business Banking (Islamic)", "1300 88 0255", "+601300880255", [], "24 hours"),
    (MY, "premier_line", "Business Banking (Premier)", "1300 88 7200", "+601300887200", [], "24 hours"),
    (MY, "consumer_line", "Consumer Banking", "1300 88 5000", "+601300885000", [], "24 hours"),
    (MY, "al_amin_line", "Consumer Banking (Al-Amin)", "1300 88 0310", "+601300880310", [], "24 hours"),
    (MY, "service_centre", "Customer service executives", "1300 88 7000", "+601300887000",
     [{"days": WEEKDAYS, "start": "09:00", "end": "18:00"}], "9:00 am to 6:00 pm, Monday to Friday"),
    (MY, "iq_desk", "iQ service executives", "1300 88 5000", "+601300885000", [], "24 hours"),
    (MY, "card_centre", "24-hour card centre", "03 8317 5000", "+60383175000", [], "24 hours"),
]  # fmt: skip

# ---- public holidays (Singapore; Malaysia as kept in Kuala Lumpur), with the days off in lieu
PUBLIC_HOLIDAYS = [
    (SG, "2026-11-09", "Deepavali (in lieu)"),
    (SG, "2026-12-25", "Christmas Day"),
    (SG, "2027-01-01", "New Year's Day"),
    (SG, "2027-02-08", "Chinese New Year (in lieu)"),
    (SG, "2027-02-09", "Chinese New Year (in lieu)"),
    (SG, "2027-03-10", "Hari Raya Puasa"),
    (SG, "2027-03-26", "Good Friday"),
    (SG, "2027-05-17", "Hari Raya Haji"),
    (SG, "2027-05-20", "Vesak Day"),
    (SG, "2027-08-09", "National Day"),
    (SG, "2027-10-28", "Deepavali"),
    (SG, "2027-12-27", "Christmas Day (in lieu)"),
    (MY, "2026-11-09", "Deepavali (in lieu)"),
    (MY, "2026-12-25", "Christmas Day"),
    (MY, "2027-01-01", "New Year's Day"),
    (MY, "2027-02-01", "Federal Territory Day"),
    (MY, "2027-02-08", "Chinese New Year (in lieu)"),
    (MY, "2027-02-09", "Chinese New Year (in lieu)"),
    (MY, "2027-03-10", "Hari Raya Aidilfitri"),
    (MY, "2027-03-11", "Hari Raya Aidilfitri"),
    (MY, "2027-05-17", "Hari Raya Haji"),
    (MY, "2027-05-20", "Wesak Day"),
    (MY, "2027-06-07", "Birthday of the Yang di-Pertuan Agong"),
    (MY, "2027-08-31", "National Day"),
    (MY, "2027-09-16", "Malaysia Day"),
    (MY, "2027-10-28", "Deepavali"),
    (MY, "2027-12-25", "Christmas Day"),
]

# ---- branches: (code, market, name, address, opening hours, area, phone)
BRANCHES = [
    ("B01", SG, "OCBC Centre", "65 Chulia Street, Singapore 049513", "Mon–Fri 9:30 am to 4:30 pm", "central", "6363 3333"),
    ("B02", SG, "Tampines", "1 Tampines Central 5, #01-01, Singapore 529508", "Mon–Fri 9:30 am to 4:30 pm, Sat 9:30 am to 12:30 pm", "east", "6363 3333"),
    ("B03", SG, "Jurong East", "50 Jurong Gateway Road, #01-01, Singapore 608549", "Mon–Fri 9:30 am to 4:30 pm", "west", "6363 3333"),
    ("MB01", MY, "Menara OCBC, Kuala Lumpur", "18 Jalan Tun Perak, 50050 Kuala Lumpur", "Mon–Fri 9:15 am to 4:30 pm", "kuala lumpur", "03 8317 5000"),
    ("MB02", MY, "Penang", "10 Lebuh Pantai, 10300 George Town, Penang", "Mon–Fri 9:15 am to 4:30 pm", "penang", "04 263 3322"),
    ("MB03", MY, "Johor Bahru", "1 Jalan Ibrahim, 80000 Johor Bahru, Johor", "Mon–Fri 9:15 am to 4:30 pm", "johor", "07 222 4400"),
]

# ---- staff customers are put through to: (code, market, name, team, free now)
SERVICE_MANAGERS = [
    ("sm_rachel", SG, "Rachel Ng", "BC Service Managers", True),
    ("sm_daniel", SG, "Daniel Lee", "BI Service Managers", False),
    ("sm_farah", MY, "Farah binti Hassan", "Business Banking Relationship Managers", True),
    ("sm_kumar", MY, "Kumar Selvam", "iQ Service Executives", True),
]

# ---- products: (market, code, name, category, for business, cheques, ACU, Islamic, rate % (None: pays none),
#      minimum balance, fall-below fee, monthly fee, annual fee)
CUR, SAV, FD, FCY = ProductCategory.CURRENT, ProductCategory.SAVINGS, ProductCategory.FIXED_DEPOSIT, ProductCategory.FOREIGN_CURRENCY
LOAN, CREDIT, DEBIT = ProductCategory.LOAN, ProductCategory.CREDIT_CARD, ProductCategory.DEBIT_CARD
PRODUCTS = [
    (SG, "SG-BCA", "Business Current Account", CUR, True, True, False, False, None, "1000", "15", "10", "0"),
    (SG, "SG-BSA", "Business Savings Account", SAV, True, False, False, False, "0.10", "10000", "10", "0", "0"),
    (SG, "SG-ACU", "ACU Current Account", CUR, True, True, True, False, None, "5000", "20", "0", "0"),
    (SG, "SG-SAV", "Savings Account", SAV, False, False, False, False, "0.05", "1000", "2", "0", "0"),
    (SG, "SG-PCA", "Current Account", CUR, False, True, False, False, None, "3000", "7.50", "0", "0"),
    (SG, "SG-GSA", "Global Savings Account", FCY, False, False, False, False, "0.20", "0", "0", "0", "0"),
    (SG, "SG-FD", "Fixed Deposit", FD, False, False, False, False, None, "1000", "0", "0", "0"),
    (MY, "MY-BCA", "Business Current Account", CUR, True, True, False, False, None, "2000", "10", "10", "0"),
    (MY, "MY-BSA", "Business Savings Account", SAV, True, False, False, False, "0.25", "5000", "10", "0", "0"),
    (MY, "MY-BCAI", "Business Current Account-i", CUR, True, True, False, True, None, "2000", "10", "10", "0"),
    (MY, "MY-BSAI", "Business Savings Account-i", SAV, True, False, False, True, "0.25", "5000", "10", "0", "0"),
    (MY, "MY-FCA", "Foreign Currency Account", FCY, False, False, False, False, "0.50", "0", "0", "0", "0"),
    (MY, "MY-SAV", "Savings Account", SAV, False, False, False, False, "0.25", "20", "0", "0", "0"),
    (MY, "MY-CA", "Current Account", CUR, False, True, False, False, None, "1000", "10", "0", "0"),
    (MY, "MY-SAVI", "Savings Account-i", SAV, False, False, False, True, "0.25", "20", "0", "0", "0"),
    (MY, "MY-FD", "Fixed Deposit", FD, False, False, False, False, None, "1000", "0", "0", "0"),
    (MY, "MY-FDI", "Fixed Deposit-i", FD, False, False, False, True, None, "1000", "0", "0", "0"),
    (MY, "MY-BTL", "Business Term Loan", LOAN, True, False, False, False, "6.20", "0", "0", "0", "0"),
    (MY, "MY-HL", "Home Loan", LOAN, False, False, False, False, "4.15", "0", "0", "0", "0"),
    (MY, "MY-HP", "Car Hire Purchase", LOAN, False, False, False, False, "3.20", "0", "0", "0", "0"),
    (MY, "MY-TITAN", "OCBC Titanium MasterCard", CREDIT, False, False, False, False, "15.00", "0", "0", "0", "150"),
    (MY, "MY-PLAT", "OCBC Platinum Visa", CREDIT, False, False, False, False, "15.00", "0", "0", "0", "250"),
    (MY, "MY-365", "OCBC 365 Credit Card", CREDIT, False, False, False, False, "15.00", "0", "0", "0", "0"),
    (MY, "MY-BDC", "OCBC Business Debit Card", DEBIT, True, False, False, False, None, "0", "0", "0", "12"),
    (MY, "MY-DC", "OCBC Debit Card", DEBIT, False, False, False, False, None, "0", "0", "0", "8"),
]

# ---- people: (ref, full name, how agents address them, date of birth, mobile, email, language, nationality, calls most about)
PEOPLE = [
    ("P001", "Tan Wei Ming", "Mr Tan", "1974-03-12", "+6591234567", "weiming.tan@acmetrading.example", "en", "SG", "balance"),
    ("P002", "Lee Hui Min", "Mrs Tan", "1977-08-02", "+6591234568", "huimin.lee@mail.example", "zh", "SG", ""),
    ("P003", "Lim Mei Ling", "Ms Lim", "1981-11-23", "+6598887777", "meiling@limco.example", "zh", "SG", ""),
    ("P004", "Ong Boon Keat", "Mr Ong", "1958-05-30", "+6590001111", None, "en", "SG", "balance"),
    ("P005", "Goh Kian Huat", "Mr Goh", "1966-01-17", "+6598765432", "kh.goh@gohholdings.example", "en", "SG", ""),
    ("P006", "Jessie Koh", "Ms Koh", "1992-06-09", "+6593334444", "jessie.koh@mail.example", "en", "SG", ""),
    ("P007", "Chua Li Ting", "Ms Chua", "1985-09-14", "+6597770000", "liting.chua@acmetrading.example", "zh", "SG", ""),
    ("P008", "Arjun Pillai", "Mr Pillai", "1979-12-03", "+6596660000", "arjun.pillai@mail.example", "en", "SG", ""),
    ("P009", "Ahmad bin Ismail", "Encik Ahmad", "1975-06-15", "+60123456789", "ahmad@majujaya.example", "ms", "MY", ""),
    ("P010", "Aisyah binti Rahman", "Puan Aisyah", "1988-01-01", "+60198765432", "aisyah.rahman@mail.example", "ms", "MY", ""),
    ("P011", "Lee Chong Hui", "Mr Lee", "1982-03-02", "+60167778888", "ch.lee@lchenterprise.example", "zh", "MY", ""),
    ("P012", "Nurul Huda binti Salleh", "Cik Nurul", "1995-08-12", "+60134445555", "nurul.huda@mail.example", "ms", "MY", ""),
]

# ---- customers (CIFs): (cif, market, name, type, registration, access, segment, since, home branch, relationship manager,
#      risk, business internet banking, iQ)
B, P, C = CustomerType.BUSINESS, CustomerType.PERSONAL, CustomerType.CONSUMER
FULL, SERVICES, ENQUIRIES = AccessLevel.FULL, AccessLevel.ACCOUNT_SERVICES, AccessLevel.ENQUIRIES
BI, BC = Segment.BUSINESS_INDIVIDUAL, Segment.BUSINESS_CORPORATE
LOW, MEDIUM = RiskRating.LOW, RiskRating.MEDIUM
CUSTOMERS = [
    # Singapore: four companies, and the personal banking of the people behind them (one shared by a couple)
    ("SG0001001", SG, "Acme Trading Pte Ltd", B, "201512345K", FULL, BI, "2015-06-01", "B01", "sm_daniel", LOW, True, False),
    ("SG0002002", SG, "Lim & Co Logistics", B, "53312345A", SERVICES, BI, "2018-02-12", "B02", "sm_daniel", LOW, False, False),
    ("SG0003003", SG, "Old Harbour Traders", B, "199901234C", ENQUIRIES, BI, "1999-04-20", "B01", "sm_daniel", MEDIUM, False, False),
    ("SG0004004", SG, "Goh Holdings Pte Ltd", B, "200809876D", FULL, BC, "2008-09-01", "B01", "sm_rachel", LOW, True, False),
    ("SG1000101", SG, "Tan Wei Ming", P, None, FULL, None, "2003-07-15", "B01", None, LOW, False, False),
    ("SG1000102", SG, "Tan Wei Ming & Lee Hui Min", P, None, FULL, None, "2010-03-01", "B01", None, LOW, False, False),
    ("SG1000202", SG, "Lee Hui Min", P, None, FULL, None, "2004-01-10", "B02", None, LOW, False, False),
    ("SG1000303", SG, "Lim Mei Ling", P, None, FULL, None, "2006-05-05", "B02", None, LOW, False, False),
    ("SG1000505", SG, "Goh Kian Huat", P, None, FULL, None, "1995-11-11", "B01", "sm_rachel", LOW, False, False),
    ("SG1000606", SG, "Jessie Koh", P, None, FULL, None, "2014-08-20", "B03", None, LOW, False, False),
    ("SG1000808", SG, "Arjun Pillai", P, None, FULL, None, "2011-02-14", "B01", "sm_rachel", LOW, False, False),
    ("SG1000909", SG, "Ahmad bin Ismail", P, None, FULL, None, "2019-10-01", "B01", None, LOW, False, False),
    # Malaysia: two companies, and consumer banking (one of them for a Singaporean)
    ("MY1001", MY, "Syarikat Maju Jaya Sdn Bhd", B, "201801012345", None, None, "2018-01-15", "MB01", "sm_farah", LOW, True, False),
    ("MY3003", MY, "Lee Chong Hui Enterprise", B, "202003045678", None, None, "2020-03-04", "MB02", "sm_farah", LOW, False, False),
    ("MY2002", MY, "Aisyah binti Rahman", C, None, None, None, "2012-09-09", "MB01", "sm_kumar", LOW, False, True),
    ("MY4004", MY, "Tan Wei Ming", C, None, None, None, "2016-04-01", "MB03", None, LOW, False, False),
    ("MY5005", MY, "Ahmad bin Ismail", C, None, None, None, "2001-06-18", "MB01", None, LOW, False, False),
    ("MY6006", MY, "Nurul Huda binti Salleh", C, None, None, None, "2017-07-01", "MB01", None, LOW, False, False),
    ("MY7007", MY, "Lee Chong Hui", C, None, None, None, "2009-12-12", "MB02", None, LOW, False, False),
]

# ---- who banks as whom: (person, cif, role)
OWNER, DIRECTOR, SIGNS = RelationshipRole.OWNER, RelationshipRole.DIRECTOR, RelationshipRole.SIGNATORY
RELATIONSHIPS = [
    ("P001", "SG0001001", DIRECTOR),
    ("P001", "SG1000101", OWNER),
    ("P001", "SG1000102", OWNER),
    ("P001", "MY4004", OWNER),
    ("P002", "SG1000102", OWNER),
    ("P002", "SG1000202", OWNER),
    ("P003", "SG0002002", DIRECTOR),
    ("P003", "SG1000303", OWNER),
    ("P004", "SG0003003", DIRECTOR),
    ("P005", "SG0004004", DIRECTOR),
    ("P005", "SG1000505", OWNER),
    ("P006", "SG1000606", OWNER),
    ("P007", "SG0001001", SIGNS),
    ("P008", "SG1000808", OWNER),
    ("P009", "MY1001", DIRECTOR),
    ("P009", "MY5005", OWNER),
    ("P009", "SG1000909", OWNER),
    ("P010", "MY2002", OWNER),
    ("P011", "MY3003", DIRECTOR),
    ("P011", "MY7007", OWNER),
    ("P012", "MY6006", OWNER),
]
# a signatory who may only make enquiries on the company's accounts: (person, cif). A customer whose phone access is
# "enquiries only" (AC) is enquiries only for everyone.
ENQUIRY_ONLY = [("P007", "SG0001001")]

# ---- addresses: (person or cif, kind, line 1, line 2, postal code, city, country)
HOME, REGISTERED, MAILING = AddressKind.HOME, AddressKind.REGISTERED, AddressKind.MAILING
ADDRESSES = [
    ("P001", HOME, "12 Siglap Drive", "", "456123", "Singapore", "SG"),
    ("P002", HOME, "12 Siglap Drive", "", "456123", "Singapore", "SG"),
    ("P003", HOME, "Blk 821 Tampines Street 81", "#09-120", "520821", "Singapore", "SG"),
    ("P004", HOME, "33 Jalan Kembangan", "", "419112", "Singapore", "SG"),
    ("P005", HOME, "7 Nassim Road", "", "258374", "Singapore", "SG"),
    ("P006", HOME, "Blk 288 Jurong East Street 21", "#05-33", "600288", "Singapore", "SG"),
    ("P007", HOME, "Blk 115 Bishan Street 12", "#11-08", "570115", "Singapore", "SG"),
    ("P008", HOME, "18 Holland Grove Road", "", "278802", "Singapore", "SG"),
    ("P009", HOME, "21 Jalan SS 2/24", "Petaling Jaya", "47300", "Selangor", "MY"),
    ("P010", HOME, "8 Jalan Setiabakti 3", "Bukit Damansara", "50490", "Kuala Lumpur", "MY"),
    ("P011", HOME, "55 Lorong Kelawai", "", "10250", "George Town", "MY"),
    ("P012", HOME, "3A-12-5 Pangsapuri Seri Ampang", "Ampang", "68000", "Selangor", "MY"),
    ("SG0001001", REGISTERED, "10 Anson Road", "#22-08 International Plaza", "079903", "Singapore", "SG"),
    ("SG0002002", REGISTERED, "25 Tampines Industrial Avenue 5", "#03-11", "528629", "Singapore", "SG"),
    ("SG0003003", REGISTERED, "2 Havelock Road", "#04-15", "059763", "Singapore", "SG"),
    ("SG0004004", REGISTERED, "1 Raffles Place", "#40-01 One Raffles Place", "048616", "Singapore", "SG"),
    ("MY1001", REGISTERED, "Lot 12, Jalan Perusahaan 2", "Kawasan Perindustrian Batu Caves", "68100", "Selangor", "MY"),
    ("MY3003", REGISTERED, "88 Jalan Burma", "", "10050", "George Town", "MY"),
]

# ---- how each person logs in: codes (fingerprinted, per country) and secrets (hashed). Singapore: phone code + PIN;
# Malaysia: key code (for the companies they act for) or phone code (their own banking) + TPIN.
PHONE, KEY = IdentifierKind.PHONE_CODE, IdentifierKind.KEY_CODE
LOGIN_CODES = [
    ("P001", SG, PHONE, "1234567"),
    ("P001", MY, PHONE, "55667788"),
    ("P002", SG, PHONE, "3355779"),
    ("P003", SG, PHONE, "7654321"),
    ("P004", SG, PHONE, "4433221"),
    ("P005", SG, PHONE, "2468024"),
    ("P006", SG, PHONE, "1111111"),
    ("P007", SG, PHONE, "5577991"),
    ("P008", SG, PHONE, "6644220"),
    ("P009", SG, PHONE, "9988776"),
    ("P009", MY, KEY, "12345678"),
    ("P009", MY, PHONE, "22446688"),
    ("P010", MY, PHONE, "87654321"),
    ("P011", MY, KEY, "11112222"),
    ("P011", MY, PHONE, "33557799"),
    ("P012", MY, PHONE, "44668800"),
]
SECRETS = [
    ("P001", CredentialKind.PIN, "246810"),
    ("P001", CredentialKind.TPIN, "135246"),
    ("P002", CredentialKind.PIN, "224466"),
    ("P003", CredentialKind.PIN, "135790"),
    ("P004", CredentialKind.PIN, "556677"),
    ("P005", CredentialKind.PIN, "112233"),
    ("P006", CredentialKind.PIN, "111111"),
    ("P007", CredentialKind.PIN, "778899"),
    ("P008", CredentialKind.PIN, "445566"),
    ("P009", CredentialKind.PIN, "998877"),
    ("P009", CredentialKind.TPIN, "123456"),
    ("P010", CredentialKind.TPIN, "654321"),
    ("P011", CredentialKind.TPIN, "999999"),
    ("P012", CredentialKind.TPIN, "246802"),
]
# ---- national IDs: the full number where the bank holds it (fingerprinted), else only the last four
IDENTITY_DOCUMENTS = [
    ("P001", DocumentType.NRIC, None, "567A"),
    ("P002", DocumentType.NRIC, None, "778E"),
    ("P003", DocumentType.NRIC, None, "321B"),
    ("P004", DocumentType.NRIC, None, "888C"),
    ("P005", DocumentType.NRIC, None, "246D"),
    ("P006", DocumentType.NRIC, None, "909F"),
    ("P007", DocumentType.NRIC, None, "112G"),
    ("P008", DocumentType.NRIC, None, "450H"),
    ("P009", DocumentType.MYKAD, "750615105511", None),
    ("P010", DocumentType.MYKAD, "880101145678", None),
    ("P011", DocumentType.MYKAD, "820302085533", None),
    ("P012", DocumentType.MYKAD, "950812146622", None),
]

# ---- accounts: (number, cif, product, currency, ledger balance today, opened, status)
ACTIVE, DORMANT = AccountStatus.ACTIVE, AccountStatus.DORMANT
ACCOUNTS = [
    ("501234567001", "SG0001001", "SG-BCA", "SGD", "128450.75", "2015-06-01", ACTIVE),
    ("501234567002", "SG0001001", "SG-BSA", "SGD", "482300.00", "2016-01-04", ACTIVE),
    ("501234567003", "SG0001001", "SG-ACU", "USD", "75210.40", "2017-03-20", ACTIVE),
    ("502468013579", "SG0002002", "SG-BCA", "SGD", "23890.10", "2018-02-12", ACTIVE),
    ("502468013580", "SG0002002", "SG-BSA", "SGD", "61200.00", "2018-02-12", ACTIVE),
    ("503000111222", "SG0003003", "SG-BCA", "SGD", "12.50", "1999-04-20", DORMANT),
    ("503000111223", "SG0003003", "SG-BSA", "SGD", "2340.00", "2005-08-01", ACTIVE),
    ("509876543210", "SG0004004", "SG-BCA", "SGD", "918400.00", "2008-09-01", ACTIVE),
    ("509876543211", "SG0004004", "SG-ACU", "USD", "240000.00", "2009-02-02", ACTIVE),
    ("512000010101", "SG1000101", "SG-SAV", "SGD", "48230.55", "2003-07-15", ACTIVE),
    ("512000010103", "SG1000101", "SG-FD", "SGD", "100000.00", "2021-05-10", ACTIVE),
    ("512000010102", "SG1000102", "SG-SAV", "SGD", "156800.00", "2010-03-01", ACTIVE),
    ("512000020201", "SG1000202", "SG-SAV", "SGD", "12450.20", "2004-01-10", ACTIVE),
    ("512000020202", "SG1000202", "SG-GSA", "USD", "5300.00", "2019-06-01", ACTIVE),
    ("512000030301", "SG1000303", "SG-SAV", "SGD", "8920.40", "2006-05-05", ACTIVE),
    ("512000030302", "SG1000303", "SG-FD", "SGD", "50000.00", "2022-01-03", ACTIVE),
    ("512000050501", "SG1000505", "SG-SAV", "SGD", "380000.00", "1995-11-11", ACTIVE),
    ("512000050502", "SG1000505", "SG-FD", "SGD", "500000.00", "2018-08-08", ACTIVE),
    ("512000060601", "SG1000606", "SG-SAV", "SGD", "6120.75", "2014-08-20", ACTIVE),
    ("512000060602", "SG1000606", "SG-PCA", "SGD", "3890.00", "2020-02-02", ACTIVE),
    ("512000080801", "SG1000808", "SG-SAV", "SGD", "74300.00", "2011-02-14", ACTIVE),
    ("512000080802", "SG1000808", "SG-GSA", "USD", "12000.00", "2018-10-10", ACTIVE),
    ("512000090901", "SG1000909", "SG-SAV", "SGD", "3450.00", "2019-10-01", ACTIVE),
    ("7011223344", "MY1001", "MY-BCA", "MYR", "256780.40", "2018-01-15", ACTIVE),
    ("7011223355", "MY1001", "MY-FCA", "USD", "18900.00", "2019-05-02", ACTIVE),
    ("7011223366", "MY1001", "MY-BSA", "MYR", "88400.00", "2018-01-15", ACTIVE),
    ("7033445566", "MY3003", "MY-BCAI", "MYR", "41200.00", "2020-03-04", ACTIVE),
    ("7033445577", "MY3003", "MY-BSAI", "MYR", "15600.00", "2020-03-04", ACTIVE),
    ("7022334455", "MY2002", "MY-SAV", "MYR", "8420.15", "2012-09-09", ACTIVE),
    ("7022334466", "MY2002", "MY-CA", "MYR", "3210.00", "2015-01-20", ACTIVE),
    ("7022334477", "MY2002", "MY-FD", "MYR", "20000.00", "2023-02-01", ACTIVE),
    ("7044556601", "MY4004", "MY-SAV", "MYR", "22500.00", "2016-04-01", ACTIVE),
    ("7055667701", "MY5005", "MY-SAV", "MYR", "14300.00", "2001-06-18", ACTIVE),
    ("7055667702", "MY5005", "MY-CA", "MYR", "2100.00", "2008-03-03", ACTIVE),
    ("7066778801", "MY6006", "MY-SAVI", "MYR", "4850.00", "2017-07-01", ACTIVE),
    ("7066778802", "MY6006", "MY-FDI", "MYR", "10000.00", "2024-01-15", ACTIVE),
    ("7077889901", "MY7007", "MY-SAV", "MYR", "31200.00", "2009-12-12", ACTIVE),
    ("7077889902", "MY7007", "MY-FCA", "USD", "4000.00", "2021-11-11", ACTIVE),
]

# ---- fixed deposits: (account, tenor months, placed months ago, on maturity, credit account)
FIXED_DEPOSITS = [
    ("512000010103", 12, 5, Maturity.RENEW_ALL, None),
    ("512000030302", 6, 2, Maturity.RENEW_PRINCIPAL, "512000030301"),
    ("512000050502", 12, 9, Maturity.RENEW_ALL, None),
    ("7022334477", 12, 4, Maturity.CREDIT_ALL, "7022334455"),
    ("7066778802", 3, 1, Maturity.RENEW_ALL, None),
]

# ---- loans: (number, cif, product, principal, outstanding, tenor months, started months ago, instalment, due in days,
#      repaid from, arrears)
LOANS = [
    ("LN-5521", "MY1001", "MY-BTL", "500000.00", "287450.55", 120, 48, "5600.00", 6, "7011223344", "0"),
    ("HL-8810", "MY2002", "MY-HL", "420000.00", "372915.20", 360, 86, "2041.66", 9, "7022334455", "0"),
    ("HP-3307", "MY5005", "MY-HP", "85000.00", "41290.00", 84, 44, "1238.81", 14, "7055667701", "1238.81"),
]

# ---- cards: (last four, cif, holder, product, status, months to expiry, limit, owed, minimum due, due in days, account)
CARDS = [
    ("4321", "MY2002", "P010", "MY-TITAN", CardStatus.INACTIVE, 36, "15000", "0", "0", None, None),
    ("5511", "MY2002", "P010", "MY-DC", CardStatus.ACTIVE, 20, "0", "0", "0", None, "7022334455"),
    ("8765", "MY5005", "P009", "MY-PLAT", CardStatus.ACTIVE, 14, "20000", "4120.00", "206.00", 10, None),
    ("7720", "MY1001", "P009", "MY-BDC", CardStatus.ACTIVE, 26, "0", "0", "0", None, "7011223344"),
    ("2468", "MY6006", "P012", "MY-365", CardStatus.ACTIVE, 30, "8000", "640.30", "50.00", 16, None),
]
CARD_APPLICATIONS = [("880101145678", "MY-365", ApplicationStatus.APPROVED, 12, 6)]  # (IC, product, status, applied days ago, sent days ago)

# ---- billers, the bills customers registered, payees at other banks, direct debits
BILLERS = [
    (MY, "TNB", "Tenaga Nasional Berhad", "electricity"),
    (MY, "UNIFI", "TM Unifi", "broadband"),
    (MY, "AIRSEL", "Air Selangor", "water"),
]
BILLS = [  # (cif, biller, the customer's account with them, nickname, paid from, monthly amount range)
    ("MY2002", "TNB", "220011443322", "Home electricity", "7022334455", (90, 260)),
    ("MY2002", "UNIFI", "1998877665", "Home internet", "7022334455", (139, 139)),
    ("MY5005", "TNB", "220033021199", "Electricity", "7055667701", (120, 310)),
    ("MY6006", "AIRSEL", "5520011223", "Water", "7066778801", (25, 60)),
]
PAYEES = [  # (cif, nickname, name, bank, account last four)
    ("MY2002", "Mum", "Rahmah binti Yusof", "Maybank", "7788"),
    ("MY5005", "Landlord", "Tan Ah Kow", "Public Bank", "4410"),
    ("MY1001", "Pembekal Bina", "Pembekal Bina Sdn Bhd", "CIMB Bank", "9921"),
]
DIRECT_DEBITS = [  # (mandate, cif, account, merchant, monthly amount, status)
    ("DD-310", "MY1001", "7011223344", "Takaful Ikhlas", "380.00", MandateStatus.ACTIVE),
    ("DD-311", "MY2002", "7022334455", "Great Eastern Life", "250.00", MandateStatus.ACTIVE),
]

# ---- cheques: books sent (account, first, last, sent days ago, how)
CHEQUE_BOOKS = [
    ("501234567001", "000226", "000275", 40, "mailed to registered address"),
    ("501234567003", "900101", "900125", 90, "mailed to registered address"),
    ("502468013579", "118801", "118850", 15, "collected at Tampines branch"),
    ("509876543210", "450001", "450050", 60, "mailed to registered address"),
    ("512000060602", "300101", "300125", 120, "mailed to home address"),
    ("7011223344", "102226", "102275", 30, "mailed to registered address"),
    ("7033445566", "630001", "630050", 75, "collected at Penang branch"),
    ("7022334466", "610001", "610025", 200, "mailed to home address"),
    ("7055667702", "620001", "620025", 150, "mailed to home address"),
]
# cheques written: (account, cheque, status, amount, paid or stopped days ago, payee)
ISSUED_CHEQUES = [
    ("501234567001", "000231", ChequeStatus.PAID, "1250.00", 4, "Harbourfront Printing"),
    ("501234567001", "000232", ChequeStatus.NOT_PRESENTED, None, None, ""),
    ("501234567001", "000233", ChequeStatus.STOPPED, None, 10, ""),
    ("502468013579", "118804", ChequeStatus.NOT_PRESENTED, None, None, ""),
    ("7011223344", "102230", ChequeStatus.PAID, "4300.00", 3, "Kilang Plastik Utama"),
    ("7011223344", "102231", ChequeStatus.NOT_PRESENTED, None, None, ""),
]
# cheques paid in: (account, deposited days ago, cheque, amount, status, cleared or returned days ago, reason)
CHEQUE_DEPOSITS = [
    ("501234567001", 3, "774410", "2600.00", DepositStatus.CLEARED, 1, None),
    ("502468013579", 1, "482211", "3400.00", DepositStatus.CLEARING, None, None),
    ("502468013579", 5, "009812", "780.00", DepositStatus.RETURNED, 3, "Payment stopped by drawer"),
    ("7011223344", 2, "102233", "8600.00", DepositStatus.CLEARED, 1, None),
]
# money on its way in: (account, received days ago, remitter, currency, amount, status, reference)
INCOMING_FUNDS = [
    ("501234567001", 2, "Nippon Parts Co", "SGD", "15880.25", IncomingFundStatus.CREDITED, "TT260412"),
    ("501234567003", 0, "Harbour Exports Ltd", "USD", "6200.00", IncomingFundStatus.PENDING, "TT260419"),
    ("501234567003", 5, "Pacific Freight LLC", "USD", "9800.00", IncomingFundStatus.CREDITED, "TT260377"),
    ("509876543211", 8, "Shenzhen Bright Electronics", "USD", "48000.00", IncomingFundStatus.CREDITED, "TT260301"),
]
# holds: (account, amount, why, release in days)
HOLDS = [
    ("501234567001", "1550.00", "GIRO payment to Keppel Packaging scheduled", 2),
    ("502468013579", "3400.00", "Cheque 482211 in clearing", 1),
]
# other recent postings that are part of the story: (account, days ago, description, amount)
RECENT = [
    ("501234567001", 0, "FAST payment to Sunrise Supplies", "-4200.00"),
    ("502468013579", 2, "PayNow to Lim Mei Ling", "-1500.00"),
    ("512000030301", 2, "PayNow from Lim & Co Logistics", "1500.00"),
    ("7011223344", 0, "IBG transfer to Pembekal Bina Sdn Bhd", "-12500.00"),
    ("7022334455", 1, "DuitNow from Siti", "250.00"),
]

# ---- contact centre
VIPS = [  # (person, how they are checked, the account they are checked by, the customer they call about, service manager)
    ("P005", VipCheck.ACCOUNT, "509876543210", "SG0004004", "sm_rachel"),
    ("P007", VipCheck.PHONE_CODE, None, "SG0001001", "sm_daniel"),
    ("P008", VipCheck.NONE, None, "SG1000808", "sm_rachel"),
]
INVESTIGATIONS = [  # (case, account, topic, opened days ago, service manager)
    ("INV-77120", "509876543211", "Inward remittance trace (TT260301)", 6, "sm_rachel"),
    ("INV-77098", "502468013579", "Returned cheque 009812", 3, "sm_daniel"),
]
SERVICE_CODES = [("328", "fd_loans", "Fixed deposit, loan or FX dealing")]

# appointments: (kind, branch, weekdays (0 = Monday), times)
SLOT_PLAN = [
    ("foreign_worker", "B02", (1, 3), (time(10, 0), time(14, 30))),
    ("foreign_worker", "B03", (2, 4), (time(10, 0),)),
    ("payment_training", "B01", (0, 2), (time(9, 30),)),
    ("trade_training", "B01", (4,), (time(14, 0),)),
]
SLOT_WEEKS = 3

# ---- published rates, promotions, forms
LENDING_RATES = [
    (SG, "prime", "Prime lending rate", "5.35"),
    (MY, "base_rate", "Base rate", "3.00"),
    (MY, "blr", "Base lending rate", "6.68"),
    (MY, "islamic_bfr", "Islamic base financing rate", "6.68"),
]
DEPOSIT_RATES = [
    (SG, "SGD", 3, "2.15"),
    (SG, "SGD", 6, "2.25"),
    (SG, "SGD", 12, "2.40"),
    (SG, "USD", 3, "3.80"),
    (MY, "MYR", 1, "2.50"),
    (MY, "MYR", 3, "2.60"),
    (MY, "MYR", 6, "2.70"),
    (MY, "MYR", 12, "2.85"),
    (MY, "USD", 3, "4.10"),
]
EXCHANGE_RATES = [
    (SG, "USD", "1.3412", "1.3528"),
    (SG, "EUR", "1.4521", "1.4688"),
    (SG, "JPY", "0.008912", "0.009034"),
    (SG, "MYR", "0.2985", "0.3061"),
    (MY, "USD", "4.402", "4.462"),
    (MY, "SGD", "3.268", "3.35"),
]
PROMOTIONS = [  # (code, market, title, started days ago, ends in days)
    ("PR01", SG, "Business Growth Account: no fall-below fee for the first 12 months", 30, 62),
    ("PR02", SG, "2.60% p.a. on a 6-month SGD fixed deposit from S$50,000", 14, 31),
    ("PR03", SG, "Waived express cheque book fee for new Velocity users", 120, -10),
    ("MP01", MY, "No annual fee on the OCBC Business Debit Card in its first year", 20, 70),
]
FORMS = [
    ("F01", SG, "Corporate Electronic Services Update Form", "phone_pin_reset"),
    ("F02", SG, "Velocity Application Form", "velocity_application"),
    ("F03", SG, "Velocity User Request Form", "velocity_user"),
    ("F04", SG, "Stop Cheque Payment Instruction", "stop_cheque"),
    ("MF01", MY, "Account Mandate Change Form", "mandate_change"),
    ("MF02", MY, "FPX Direct Debit Termination Form", "fpx_termination"),
]


# ---- about three months of ordinary activity on every account, made the same way each time (seeded by the account number)
_NAMES = {
    SG: {
        "supplier": ["Sunrise Supplies", "Keppel Packaging", "Jurong Freight", "Harbourfront Printing", "Lion City Electrical"],
        "client": ["Nippon Parts Co", "Pacific Freight LLC", "Marina Retail Pte Ltd", "Orchard Interiors", "Tampines Engineering"],
        "employer": ["Changi Logistics", "Raffles Medical Group", "Sentosa Leisure", "Keppel Offshore"],
        "shop": ["FairPrice", "Cold Storage", "Guardian", "Popular Bookstore", "Kopitiam"],
        "friend": ["Rachel Tan", "Marcus Lim", "Priya Nair", "Daniel Ong"],
    },
    MY: {
        "supplier": ["Pembekal Bina Sdn Bhd", "Kilang Plastik Utama", "Syarikat Logistik Jaya", "Percetakan Mutiara"],
        "client": ["Perniagaan Seri Kembangan", "Mega Hardware Sdn Bhd", "Kedai Runcit Aman", "Borneo Timber Trading"],
        "employer": ["Petronas Dagangan", "Hospital Pantai", "Universiti Malaya", "Sime Darby Property"],
        "shop": ["Mydin", "Lotus's", "Watsons", "99 Speedmart", "Tealive"],
        "friend": ["Siti", "Farid", "Mei Ling", "Kumar"],
    },
}
# (description, lowest, highest): debits are negative
_ACTIVITY = {
    "business": {
        SG: [("GIRO payment to {supplier}", -18000, -900), ("FAST transfer from {client}", 1500, 26000), ("Inward TT from {client}", 3000, 40000)],
        MY: [("IBG transfer to {supplier}", -15000, -800), ("DuitNow from {client}", 1200, 22000), ("Instant transfer from {client}", 900, 15000)],
    },
    "personal": {
        SG: [("NETS purchase at {shop}", -180, -8), ("PayNow to {friend}", -600, -20), ("ATM withdrawal", -400, -50), ("PayNow from {friend}", 20, 300)],
        MY: [("Purchase at {shop}", -150, -6), ("DuitNow to {friend}", -500, -20), ("ATM withdrawal", -300, -50), ("DuitNow from {friend}", 20, 300)],
    },
}
HISTORY_DAYS = 91


def _money(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _monthly(day_of_month: int, until: int = 0) -> list[int]:
    """The days ago, within the history, on which something happens each month on this day (not after `until` days ago)."""
    out = []
    for n in range(HISTORY_DAYS - 1, until - 1, -1):
        if days_ago(n).day == day_of_month:
            out.append(n)
    return out


def _ordinary(number: str, customer: Customer, product: Product) -> list[tuple[int, str, Decimal]]:
    """Everyday postings: a business's suppliers, clients, payroll and charges; a person's salary, shopping and transfers;
    interest at each month's end on an account that pays it."""
    rng = random.Random(number)
    market, kind = customer.market, "business" if customer.customer_type is CustomerType.BUSINESS else "personal"
    names = _NAMES[market]
    out: list[tuple[int, str, Decimal]] = []
    if product.category in (ProductCategory.CURRENT, ProductCategory.SAVINGS) or (kind == "business" and product.category is ProductCategory.FOREIGN_CURRENCY):
        for n in sorted(rng.sample(range(3, HISTORY_DAYS), rng.randint(9, 14))):
            template, low, high = rng.choice(_ACTIVITY[kind][market])
            description = template.format(**{key: rng.choice(values) for key, values in names.items()})
            out.append((n, description, _money(rng.uniform(low, high))))
    if kind == "business" and product.category is ProductCategory.CURRENT and not product.is_acu:
        out += [(n, "Salary run" if market is SG else "Salary run and EPF", _money(-rng.uniform(9000, 42000))) for n in _monthly(25, 2)]
    if kind == "personal" and product.category is ProductCategory.SAVINGS and rng.random() < 0.7:
        employer = rng.choice(names["employer"])
        salary = _money(rng.uniform(3800, 9500))
        out += [(n, f"Salary credit from {employer}", salary) for n in _monthly(25)]
    if product.monthly_fee:
        out += [(n, "Service charge", -product.monthly_fee) for n in _monthly(28)]
    if product.interest_rate_pct:
        # a month's interest on about today's balance, at the product's rate
        interest = _money(account_balance(number) * product.interest_rate_pct / 100 / 12)
        if interest:
            out += [(n, "Interest credit", interest) for n in _monthly(28)]
    return out


def account_balance(number: str) -> Decimal:
    return next(D(ledger) for n, _cif, _p, _c, ledger, _o, _s in ACCOUNTS if n == number)


def _postings(account: Account, customer: Customer, product: Product, story: list[tuple[int, str, Decimal]]) -> list[tuple[date, str, Decimal]]:
    """The account's postings, oldest first, from a balance brought forward to exactly today's ledger balance. The
    postings of the story are always kept. Ordinary ones are left out where they do not fit: a credit when more came in
    than the account holds today, a debit that would take it below zero."""
    if account.status is AccountStatus.DORMANT:
        # nothing for years: the last thing was a cheque, long ago
        return [(days_ago(820), "Balance brought forward", account.ledger_balance + D("1250.00")), (days_ago(790), "Cheque 000118 cleared", D("-1250.00"))]
    if product.category is ProductCategory.FIXED_DEPOSIT:
        return []  # placed once (the deposit's own posting, below)
    ordinary = _ordinary(account.account_number, customer, product)
    while True:
        rows = sorted([(n, d, a, True) for n, d, a in story] + [(n, d, a, False) for n, d, a in ordinary], key=lambda r: -r[0])
        opening = account.ledger_balance - sum((a for _, _, a, _ in rows), D("0"))
        if opening < 0:
            # more came in than is there today: leave out the largest ordinary credit
            candidates = [(-a, n, d, a) for n, d, a, kept in rows if not kept and a > 0]
        else:
            balance, low_point, worst = opening, opening, -1
            for i, (_n, _d, a, _kept) in enumerate(rows):
                balance += a
                if balance < low_point:
                    low_point, worst = balance, i
            if low_point >= 0:
                break
            # overdrawn on the way: leave out the largest ordinary debit up to that point
            candidates = [(a, n, d, a) for n, d, a, kept in rows[: worst + 1] if not kept and a < 0]
        if not candidates:
            raise ValueError(f"{account.account_number}: its story alone does not add up to today's balance")
        _, n, d, amount = min(candidates)
        ordinary.remove((n, d, amount))
    return [(days_ago(HISTORY_DAYS), "Balance brought forward", opening)] + [(days_ago(n), d, a) for n, d, a, _ in rows]


def load(session: Session) -> None:
    """Add the starting data to an empty database."""
    session.add_all(
        BankIdentity(
            market=m,
            bank_name=bank,
            country_name=country,
            base_currency=currency,
            timezone=zone,
            dialling_code=code,
            trunk_prefix=trunk,
            local_number_pattern=pattern,
            account_number_digits=digits,
            giro_bank_code=giro,
            swift_bic=swift,
            branch_code_note=note,
        )
        for m, bank, country, currency, zone, code, trunk, pattern, digits, giro, swift, note in BANK_IDENTITY
    )
    session.add_all(Setting(market=m, name=n, value=v, description=d) for m, n, v, d in SETTINGS)
    session.add_all(Tariff(market=m, code=c, label=label, fee=D(f), currency=cur, working_days=w) for m, c, label, f, cur, w in TARIFFS)
    session.add_all(
        ContactPoint(market=m, code=c, label=label, display_number=shown, dial_number=dial, hours=hours, hours_label=said)
        for m, c, label, shown, dial, hours, said in CONTACT_POINTS
    )
    session.add_all(PublicHoliday(market=m, holiday_on=date.fromisoformat(d), name=n) for m, d, n in PUBLIC_HOLIDAYS)

    branches = {code: Branch(code=code, market=m, name=n, address=a, opening_hours=h, area=area, phone=p) for code, m, n, a, h, area, p in BRANCHES}
    managers = {code: ServiceManager(code=code, market=m, name=n, team=t, available=a) for code, m, n, t, a in SERVICE_MANAGERS}
    products = {
        code: Product(
            market=m,
            code=code,
            name=name,
            category=cat,
            for_business=biz,
            cheques=chq,
            is_acu=acu,
            is_islamic=isl,
            interest_rate_pct=D(rate) if rate else None,
            minimum_balance=D(minimum),
            fall_below_fee=D(below),
            monthly_fee=D(monthly),
            annual_fee=D(annual),
        )
        for m, code, name, cat, biz, chq, acu, isl, rate, minimum, below, monthly, annual in PRODUCTS
    }
    session.add_all([*branches.values(), *managers.values(), *products.values()])
    session.flush()

    people = {
        ref: Person(
            person_ref=ref,
            full_name=name,
            salutation=title,
            date_of_birth=date.fromisoformat(born),
            mobile=mobile,
            email=email,
            language=lang,
            nationality=country,
            favourite_transaction=favourite,
        )
        for ref, name, title, born, mobile, email, lang, country, favourite in PEOPLE
    }
    customers = {
        cif: Customer(
            cif=cif,
            market=m,
            name=name,
            customer_type=kind,
            registration_number=registration,
            access_level=access,
            segment=segment,
            customer_since=date.fromisoformat(since),
            home_branch_id=branches[branch].id,
            service_manager_id=managers[rm].id if rm else None,
            risk_rating=risk,
            kyc_review_due=date.fromisoformat(since).replace(year=TODAY.year + (1 if risk is LOW else 0)),
            business_internet_banking=internet,
            iq_member=iq,
        )
        for cif, m, name, kind, registration, access, segment, since, branch, rm, risk, internet, iq in CUSTOMERS
    }
    session.add_all([*people.values(), *customers.values()])
    session.flush()

    session.add_all(Relationship(person_id=people[ref].id, customer_id=customers[cif].id, role=role) for ref, cif, role in RELATIONSHIPS)
    for owner, kind, line1, line2, postal, city, country in ADDRESSES:
        whose = {"person_id": people[owner].id} if owner in people else {"customer_id": customers[owner].id}
        session.add(Address(**whose, kind=kind, line1=line1, line2=line2, postal_code=postal, city=city, country=country))
    for ref, market, kind, code in LOGIN_CODES:
        session.add(LoginIdentifier(person_id=people[ref].id, market=market, kind=kind, fingerprint=fingerprint(code), last4=last4(code)))
    for ref, kind, secret in SECRETS:
        session.add(Credential(person_id=people[ref].id, kind=kind, secret_hash=hash_secret(secret)))
    for ref, doc_type, number, tail in IDENTITY_DOCUMENTS:
        session.add(
            IdentityDocument(
                person_id=people[ref].id,
                document_type=doc_type,
                fingerprint=fingerprint(number) if number else None,
                last4=last4(number) if number else tail,
            )
        )

    accounts = {}
    for number, cif, product, currency, ledger, opened, status in ACCOUNTS:
        customer = customers[cif]
        accounts[number] = Account(
            account_number=number,
            customer_id=customer.id,
            market=customer.market,
            product_id=products[product].id,
            currency=currency,
            ledger_balance=D(ledger),
            status=status,
            opened_on=date.fromisoformat(opened),
            branch_id=customer.home_branch_id,
        )
    session.add_all(accounts.values())
    session.flush()

    # who may use each account: the people linked to its customer; two owners make it a joint account
    owners = {cif: [ref for ref, c, role in RELATIONSHIPS if c == cif and role is OWNER] for cif in customers}
    enquiry_only = set(ENQUIRY_ONLY)
    for number, cif, *_ in ACCOUNTS:
        for ref, linked_cif, role in RELATIONSHIPS:
            if linked_cif != cif:
                continue
            joint = len(owners[cif]) > 1
            holder_role = HolderRole.SIGNATORY if role is not OWNER else (HolderRole.JOINT if joint else HolderRole.PRIMARY)
            may_transact = (ref, cif) not in enquiry_only and customers[cif].access_level is not ENQUIRIES
            session.add(AccountHolder(account_id=accounts[number].id, person_id=people[ref].id, role=holder_role, can_transact=may_transact))

    _load_money_movements(session, customers, products, accounts)
    _load_cards_and_payments(session, customers, people, products, accounts)
    _load_contact_centre(session, people, customers, accounts, managers, branches)

    session.add_all(LendingRate(market=m, name=n, label=label, rate_pct=D(r)) for m, n, label, r in LENDING_RATES)
    session.add_all(DepositRate(market=m, currency=c, tenor_months=t, rate_pct=D(r)) for m, c, t, r in DEPOSIT_RATES)
    session.add_all(ExchangeRate(market=m, currency=c, bank_buys=D(b), bank_sells=D(s)) for m, c, b, s in EXCHANGE_RATES)
    session.add_all(Promotion(code=c, market=m, title=t, valid_from=days_ago(started), valid_until=days_ago(-ends)) for c, m, t, started, ends in PROMOTIONS)
    session.add_all(Form(code=c, market=m, title=t, purpose=p) for c, m, t, p in FORMS)
    session.add_all(ServiceCode(code=c, route=r, label=label) for c, r, label in SERVICE_CODES)


def _load_money_movements(session: Session, customers: dict, products: dict, accounts: dict) -> None:
    """Postings, holds, fixed deposits, loans, cheques and incoming funds, so that every one of them is on the account."""
    story: dict[str, list[tuple[int, str, Decimal]]] = {number: [] for number in accounts}

    def add(number: str, n: int, description: str, amount: str | Decimal) -> None:
        story[number].append((n, description, D(amount) if isinstance(amount, str) else amount))

    for number, n, description, amount in RECENT:
        add(number, n, description, amount)
    for number, n, remitter, _currency, amount, status, ref in INCOMING_FUNDS:
        if status is IncomingFundStatus.CREDITED:
            add(number, n, f"Inward TT from {remitter} ({ref})", amount)
    for number, cheque_no, status, amount, n, payee in ISSUED_CHEQUES:
        if status is ChequeStatus.PAID:
            add(number, n, f"Cheque {cheque_no} cleared ({payee})", f"-{amount}")
    for number, n, cheque_no, amount, status, settled, _reason in CHEQUE_DEPOSITS:
        add(number, n, f"Cheque deposit {cheque_no}", amount)
        if status is DepositStatus.RETURNED:
            add(number, settled, f"Returned cheque {cheque_no}", f"-{amount}")
    stopped = [(number, cheque_no, n) for number, cheque_no, status, _a, n, _p in ISSUED_CHEQUES if status is ChequeStatus.STOPPED]
    stop_fees = {}
    for number, cheque_no, n in stopped:
        fee = next(D(f) for m, c, _l, f, _cur, _w in TARIFFS if m is accounts[number].market and c == "stop_cheque")
        add(number, n, f"Stop payment fee, cheque {cheque_no}", -fee)
        stop_fees[(number, cheque_no)] = fee

    loans = []
    for number, cif, product, principal, outstanding, tenor, started, instalment, due, repay, arrears in LOANS:
        next_due = days_ago(-due)
        missed = D(arrears) > 0
        for n in _monthly(next_due.day, 1):
            if missed and n == min(_monthly(next_due.day, 1)):
                continue  # last month's instalment was not paid: it is in arrears
            add(repay, n, f"{products[product].name} instalment {number}", f"-{instalment}")
        loans.append(
            Loan(
                loan_number=number,
                customer_id=customers[cif].id,
                product_id=products[product].id,
                currency=CURRENCY[customers[cif].market],
                principal=D(principal),
                outstanding=D(outstanding),
                rate_pct=products[product].interest_rate_pct,
                tenor_months=tenor,
                started_on=months_ago(started, next_due.day),
                monthly_instalment=D(instalment),
                next_due_on=next_due,
                arrears=D(arrears),
                repayment_account_id=accounts[repay].id,
            )
        )
    for mandate, _cif, number, merchant, amount, status in DIRECT_DEBITS:
        if status is MandateStatus.ACTIVE:
            for n in _monthly(5):
                add(number, n, f"FPX direct debit {merchant} ({mandate})", f"-{amount}")
    for _cif, biller, ref, _nick, number, (low, high) in BILLS:
        rng = random.Random(ref)
        name = next(n for _m, c, n, _cat in BILLERS if c == biller)
        for n in _monthly(12):
            add(number, n, f"JomPAY {name} {ref}", -_money(rng.uniform(low, high)))
    # a credit card paid every month from the holder's savings
    add("7055667701", 20, "Credit card payment OCBC Platinum Visa ending 8765", "-2310.00")
    add("7055667701", 50, "Credit card payment OCBC Platinum Visa ending 8765", "-1860.40")

    for number, account in accounts.items():
        customer = next(c for c in customers.values() if c.id == account.customer_id)
        product = next(p for p in products.values() if p.id == account.product_id)
        balance = None
        for posted_on, description, amount in _postings(account, customer, product, story[number]):
            balance = amount if balance is None else balance + amount
            session.add(Transaction(account_id=account.id, posted_on=posted_on, description=description, amount=amount, balance_after=balance))
        assert balance is None or balance == account.ledger_balance, number

    for number, tenor, placed, maturity, credit_to in FIXED_DEPOSITS:
        account = accounts[number]
        product = next(p for p in products.values() if p.id == account.product_id)
        placed_on = months_ago(placed, 10)
        currency_rates = {(m, c, t): D(r) for m, c, t, r in DEPOSIT_RATES}
        rate = currency_rates[(account.market, account.currency, tenor)]
        session.add(
            FixedDeposit(
                account_id=account.id,
                principal=account.ledger_balance,
                rate_pct=rate,
                tenor_months=tenor,
                placed_on=placed_on,
                matures_on=months_ago(placed - tenor, 10),
                on_maturity=maturity,
                credit_account_id=accounts[credit_to].id if credit_to else None,
            )
        )
        session.add(
            Transaction(
                account_id=account.id,
                posted_on=placed_on,
                description=f"{product.name} placed for {tenor} months at {rate}% p.a.",
                amount=account.ledger_balance,
                balance_after=account.ledger_balance,
            )
        )
    session.add_all(loans)
    session.add_all(Hold(account_id=accounts[a].id, amount=D(v), reason=why, placed_on=TODAY, release_on=days_ago(-release)) for a, v, why, release in HOLDS)
    session.add_all(
        IncomingFund(account_id=accounts[a].id, received_on=days_ago(n), remitter=r, currency=c, amount=D(v), status=s, reference=ref)
        for a, n, r, c, v, s, ref in INCOMING_FUNDS
    )
    session.add_all(
        ChequeBook(account_id=accounts[a].id, first_cheque_no=first, last_cheque_no=last, sent_on=days_ago(n), delivery=how)
        for a, first, last, n, how in CHEQUE_BOOKS
    )
    for number, cheque_no, status, amount, n, _payee in ISSUED_CHEQUES:
        cheque = IssuedCheque(
            market=accounts[number].market,
            account_number=number,
            account_id=accounts[number].id,
            cheque_no=cheque_no,
            status=status,
            amount=D(amount) if amount else None,
            paid_on=days_ago(n) if status is ChequeStatus.PAID else None,
            stopped_on=days_ago(n) if status is ChequeStatus.STOPPED else None,
        )
        session.add(cheque)
        if status is ChequeStatus.STOPPED:
            currency = CURRENCY[accounts[number].market]
            session.add(StopPayment(cheque=cheque, reason="Lost in the post", fee=stop_fees[(number, cheque_no)], fee_currency=currency))
    session.add_all(
        ChequeDeposit(
            account_id=accounts[a].id,
            deposited_on=days_ago(n),
            cheque_no=no,
            amount=D(v),
            status=s,
            value_date=days_ago(settled) if s is DepositStatus.CLEARED else None,
            return_reason=reason,
        )
        for a, n, no, v, s, settled, reason in CHEQUE_DEPOSITS
    )


def _load_cards_and_payments(session: Session, customers: dict, people: dict, products: dict, accounts: dict) -> None:
    for tail, cif, holder, product, status, expiry, limit, owed, minimum, due, account in CARDS:
        session.add(
            Card(
                last4=tail,
                customer_id=customers[cif].id,
                holder_id=people[holder].id,
                product_id=products[product].id,
                account_id=accounts[account].id if account else None,
                expires_on=months_ago(-expiry, 28),
                status=status,
                credit_limit=D(limit),
                outstanding_balance=D(owed),
                minimum_due=D(minimum),
                due_on=days_ago(-due) if due is not None else None,
            )
        )
    session.add_all(
        CardApplication(id_fingerprint=fingerprint(ic), product_id=products[p].id, status=s, applied_on=days_ago(applied), sent_on=days_ago(sent))
        for ic, p, s, applied, sent in CARD_APPLICATIONS
    )
    billers = {code: Biller(market=m, code=code, name=n, category=cat) for m, code, n, cat in BILLERS}
    session.add_all(billers.values())
    session.flush()
    session.add_all(Bill(customer_id=customers[cif].id, biller_id=billers[b].id, biller_reference=ref, nickname=nick) for cif, b, ref, nick, _a, _r in BILLS)
    session.add_all(Payee(customer_id=customers[cif].id, nickname=nick, name=n, bank_name=bank, account_last4=tail) for cif, nick, n, bank, tail in PAYEES)
    session.add_all(
        DirectDebit(mandate_reference=ref, customer_id=customers[cif].id, account_id=accounts[a].id, merchant=m, amount=D(v), status=s)
        for ref, cif, a, m, v, s in DIRECT_DEBITS
    )


def _load_contact_centre(session: Session, people: dict, customers: dict, accounts: dict, managers: dict, branches: dict) -> None:
    session.add_all(
        Vip(
            person_id=people[ref].id,
            vip_check=check,
            account_id=accounts[a].id if a else None,
            customer_id=customers[cif].id if cif else None,
            service_manager_id=managers[sm].id,
        )
        for ref, check, a, cif, sm in VIPS
    )
    session.add_all(
        Investigation(case_reference=ref, account_id=accounts[a].id, topic=t, opened_on=days_ago(n), service_manager_id=managers[sm].id)
        for ref, a, t, n, sm in INVESTIGATIONS
    )
    # appointment slots for the next weeks, on working days only
    holidays = {date.fromisoformat(d) for m, d, _ in PUBLIC_HOLIDAYS if m is SG}
    number = 0
    for ahead in range(1, SLOT_WEEKS * 7 + 1):
        day = days_ago(-ahead)
        if day.weekday() >= 5 or day in holidays:
            continue
        for kind, branch, weekdays, times in SLOT_PLAN:
            if day.weekday() not in weekdays:
                continue
            for at in times:
                number += 1
                session.add(AppointmentSlot(code=f"S{number:03d}", appointment_type=kind, branch_id=branches[branch].id, slot_date=day, slot_time=at))


def reset(session: Session) -> None:
    """Empty every table (ids start again from 1) and load the starting data."""
    names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    session.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    load(session)


if __name__ == "__main__":
    with SessionLocal.begin() as session:
        reset(session)
    print(
        f"The bank's data is loaded as of {TODAY}: {len(PEOPLE)} people, {len(CUSTOMERS)} customers, {len(ACCOUNTS)} accounts,"
        f" {len(PRODUCTS)} products, {len(CARDS)} cards, {len(LOANS)} loans, and their history, cheques, rates, branches and lines."
    )
