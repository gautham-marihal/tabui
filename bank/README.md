# The bank and its CRM

A made-up bank (every customer, account and number is invented) in a PostgreSQL database, with its API: the bank systems
the business-banking phone agents call, and a **CRM** that the showcase and other apps read. Built with SQLAlchemy
(tables), Alembic (versioned changes to them) and FastAPI (the API). It runs beside the showcase:

```
PostgreSQL (port 5434)  ←  bank API (bank/, port 4310)  ←  showcase: /crm page and /api/crm  ←  Weave Studio's Integrations, agents' tools
```

## Run it

You need Docker Desktop (for the database) and Python 3.12 or newer. From the `tabui` folder:

```bash
node bank/py.mjs setup                                   # once: a Python environment in bank/.venv with the packages
docker compose -f bank/docker-compose.yml up -d --wait   # the database
cd bank
node py.mjs -m alembic upgrade head                      # create or update the tables
node py.mjs -m bank.seed                                 # load the made-up customers (also resets the bank)
node py.mjs -m bank                                      # the API on http://localhost:4310
```

Settings are in `bank/.env` (copy `bank/.env.example`; environment variables win): `BANK_DATABASE_URL`, `PORT`,
`BANK_API_KEY` (the key the CRM routes ask for) and `BANK_PEPPER`. Tests and checks: `node py.mjs -m pytest`,
`node py.mjs -m ruff check .`.

## The CRM

Every `/crm` route asks for `Authorization: Bearer <BANK_API_KEY>`. The showcase serves the same routes to other apps at
`/api/crm/…`, for callers that send `CRM_API_KEY` (set in `showcase/.env.local` with `BANK_API_URL`, `BANK_API_KEY`
and `CRM_ALLOWED_ORIGINS`).

| Route                                                  | What it does                                                                   |
| ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `GET health`, `GET summary`                            | Whether it answers; how many customers, accounts, open call-backs…             |
| `GET customers?q=&market=`                             | Customers, by name, CIF, or the last digits of a mobile or account             |
| `GET customers/{cif}`                                  | One customer: accounts, cards, loans, direct debits, cases, what calls left    |
| `GET customers/{cif}/transactions?account=`            | Recent postings, on one account (last four digits) or all                      |
| `GET lookup?phone=`                                    | Who is calling, from their number: customer, language, VIP, service manager    |
| `POST verify` `{code or cif, secret}`                  | Checks a phone code / key code / IC and the PIN or TPIN; three wrong tries lock |
| `POST otp/send`, `POST otp/verify`                     | A one-time password by SMS (the mock's is always 123456)                       |
| `POST hand-overs` `{cif, queue, reason, summary}`      | Passes the caller to people, with a summary so nobody asks again               |
| `POST callbacks`, `POST service-requests`              | A call-back, or a request for the back office, kept with the customer          |
| `GET activity`                                         | The audit log, newest first                                                    |

Account and card numbers come back as `****1234`, phone numbers with only their last four digits. PINs, TPINs, codes
and one-time passwords are stored only as salted hashes, and login codes and ID numbers as keyed fingerprints: the
database never holds them readable, and no route hands them out.

## How the data holds together

The bank is modelled the way a bank keeps its books:

- **People and customers.** A person (one human) banks through customer records (CIFs): their own, a joint one shared
  with a spouse, and the companies they act for as director or signatory. Who may use each account, and whether only
  for enquiries, is in `account_holders`. A name, mobile or language is kept once, on the person.
- **Products.** Every account, fixed deposit, loan and card is one of the bank's products, which says what it is
  called, what it pays or charges, and whether it writes cheques, is ACU or Islamic.
- **Money.** An account's balance is a "balance brought forward" plus every posting since, and each posting keeps the
  balance it left. What cannot be spent yet is a hold (a cheque in clearing, a payment earmarked for a date). A paid
  cheque, a cheque paid in, a transfer, an instalment, a direct debit or a bill is always a posting too. Fixed deposits
  keep their terms; loans their principal, outstanding amount, instalment, arrears and repayment account.
- **Rules.** Settings, the price list (fees and working days), phone lines and their hours, public holidays, rates,
  promotions and forms are tables: no route holds a number of its own. "Today" is the country's own (its time zone).
  `GET /hub/reference` gives the agents all of it, so they are built from the bank.
- **Safety.** Every change names the person asking (`person`), and is refused unless they hold the account, it is
  active, they may transact, and money is paid only from an account that can pay. Nothing is stopped, charged or
  booked twice. Every change goes to the audit log.

`tests/test_data.py` checks all of this on the starting data.

## Test customers

Twelve people in both countries; the full list with what each one sees is in Weave Studio's `mock-bank/README.md`.

| Who                                       | Logs in with                                                                         |
| ----------------------------------------- | ------------------------------------------------------------------------------------ |
| Mr Tan (Acme Trading, SG; also Malaysia)  | phone code `1234567`, PIN `246810`; Malaysia phone code `55667788`, TPIN `135246`   |
| Ms Lim (Lim & Co Logistics, SG)           | phone code `7654321`, PIN `135790`; or account `502468013579`, NRIC `321B`, OTP `123456` |
| Mr Ong (Old Harbour Traders, SG)          | phone code `4433221`, PIN `556677` (enquiries only; one dormant account)              |
| Encik Ahmad (Syarikat Maju Jaya, MY)      | key code `12345678` or phone code `22446688`, TPIN `123456`                           |
| Puan Aisyah (MY consumer, iQ)             | phone code `87654321` (or IC `880101145678`), TPIN `654321`                           |

The bank used to live in Weave Studio (`mock-bank/`); it is kept only here now, and the studio keeps the agents.
