// What each bank agent in the chat's list can do, as their live versions do it (development, November 2026). The six
// OCBC agents follow the bank's IVR call flows; they read the bank database and the mock bank services
// (https://weave-mock-api.vercel.app) for everything the database doesn't hold.

export type Agent = { name: string; line: string; can: string[]; ask: string[] };

export const AGENTS: Agent[] = [
  {
    name: "SG Business Banking",
    line: "Singapore business banking, 6538 1111. The widest of them: start here.",
    can: [
      "Balances with the available balance, holds, cheques pending clearance and overdraft limit",
      "Incoming funds of the last 7 days, recent transactions and statement copies",
      "Cheques: status, stop one or a range, deposited and returned cheques, order a cheque book",
      "Change your phone PIN",
      "Book or cancel foreign worker account opening and Velocity training",
      "Rates, branches by region, forms and promotions by fax, GIRO and SWIFT codes",
      "Block a lost card, service code 328, the trade hotline, a call-back from a service manager",
      "The three-question phone survey",
    ],
    ask: [
      "What’s my balance?",
      "Any incoming funds this week?",
      "Stop cheque 772663",
      "I need a new cheque book",
      "Book Velocity Payment training",
      "What’s the US dollar rate?",
      "Which branches are in the North?",
      "I want to give feedback",
    ],
  },
  {
    name: "MY Business Banking",
    line: "Malaysia business banking: log in with your key code or phone code, then TPIN.",
    can: [
      "Balances, recent transactions and statement copies",
      "Transfers between your own accounts and OCBC loan payments (after 8 pm, effective tomorrow)",
      "FPX direct debits: list them and end one",
      "Cheques: status, stop payment, cheque book request",
      "Change your TPIN",
      "Branches, forms by fax, and FX, deposit, foreign currency, Islamic and prime rates",
    ],
    ask: ["What’s my balance?", "I want to pay my loan", "Show my FPX direct debits", "Stop cheque 116308", "What are your deposit rates?"],
  },
  {
    name: "MY Consumer Banking",
    line: "Malaysia consumer and iQ: log in with your phone code or 12-digit IC number, then TPIN.",
    can: [
      "Cards: block a lost card, activate, fee waiver, credit limit, balance transfer, balance and transactions, statement, application status",
      "Banking: balance, cheques, statements, rates, branches, TPIN change",
      "Payments: own accounts, OCBC loan or financing, credit card, utility bills, Interbank GIRO",
      "A call-back from your iQ service executive",
    ],
    ask: ["What are my recent credit card transactions?", "I lost my credit card", "Pay my electricity bill", "I want my iQ service executive"],
  },
  {
    name: "SG Business Banking VIP",
    line: "Singapore VIP line, 6538 2222: found by the mobile number registered with the bank.",
    can: [
      "Find the VIP by mobile number and check them as their VIP entry says (account number, or phone code and TPIN)",
      "Arrange a call-back from their own service manager, or another in the same group",
      "Balances and transactions after the phone code and TPIN",
    ],
    ask: ["Hello", "I’d like my service manager to call me"],
  },
  {
    name: "SG Investigations",
    line: "Singapore investigations line, 6586 5292.",
    can: [
      "Take the account number of the case and arrange a call-back from the service manager handling it",
      "After the phone code and TPIN: go through recent transactions and open a case",
    ],
    ask: ["I am calling about my case", "There’s a payment I don’t recognise"],
  },
  {
    name: "SG Service Manager Survey",
    line: "Reached after a service manager’s call.",
    can: ["Three questions about the service manager, each 1 Excellent, 2 Satisfactory or 3 Poor, saved at the end"],
    ask: ["Hi"],
  },
  {
    name: "DB2 Phone Banking Test",
    line: "The first test agent: the bank database only.",
    can: ["Balances and recent transactions, after your phone code and TPIN"],
    ask: ["What’s my balance?", "Show my last transactions"],
  },
];

// What none of them do
export const CANNOT = [
  "Put you through to a person live: they arrange a call-back instead",
  "Move real money: payments, stops and bookings answer with a reference, but no balance changes, and they may be forgotten",
  "Open accounts or approve loans and cards",
  "Tell you about another customer, or anything before you are verified",
  "Say your TPIN or one-time password back to you, even if you ask",
];

// Logins and numbers besides a phone code and TPIN, from the bank services' test data
export const LOGINS: [string, string, string][] = [
  ["Account number + NRIC + one-time password", "SG Business Banking", "Tan Wei Ming: account 897350869921, NRIC ending 095Z, password 123456"],
  ["Key code + TPIN", "MY Business Banking", "Lim Chee Keong: key code 77046976, TPIN 1234"],
  ["IC number + TPIN", "MY Consumer Banking", "Nur Aisyah binti Ahmad: IC 850512023052, TPIN 1234"],
  ["Registered mobile (VIP)", "SG Business Banking VIP", "Goh Kian Hock: mobile +65 9008 1145, then account 195166925799"],
  ["Case account number", "SG Investigations", "Account 897350869921"],
  ["Card application (no login)", "MY Consumer Banking", "Applicant IC 900101145566 (approved), 880512106789 (in review)"],
];

// The bank services' areas, for the reference section
export const SERVICES: [string, string][] = [
  ["Logins", "Account number + NRIC + one-time password, key code, IC number; phone PIN change"],
  ["Accounts", "Balance details (holds, pending cheques, overdraft), incoming funds, statements"],
  ["Cheques", "Status, stop one or a range, cheque books with delivery options, deposited and returned cheques"],
  ["Cards", "List, block, activate, fee waiver, credit limit, balance transfer, transactions, statement, applications"],
  ["Payments", "Payees, loan, card and bill payments, own-account transfers, FPX direct debits"],
  ["Appointments", "Foreign worker account opening and Velocity training slots, bookings, cancelling"],
  ["Service managers", "Service centre hours, VIP table, last service manager, service codes, call-backs"],
  ["Information", "Rates, branches, forms and promotions by fax, bank codes, contacts; surveys"],
];
