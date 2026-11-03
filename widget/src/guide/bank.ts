// The bank database the guide describes: Ashwin's TetherfiDbRestApi (three tables, one dboperations call). The page
// reads it through the dev server's /bank-api route (vite.config.ts), which passes on the reading methods only.

export type Row = Record<string, string>;

export type Account = { accountId: string; type: string; balance: string; currency: string };
export type Customer = { customerId: string; name: string; tpin: string; country: "SG" | "MY"; accounts: Account[] };

type Answer = { responseList?: { tableDetails?: { columnMap?: Row } | null }[] | null; errorDesc?: string | null };

export async function bankRows(entity: string, method: string, columnMap: Row = {}): Promise<Row[]> {
  const response = await fetch("/bank-api", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ entity, method, details: [{ columnMap }] }),
  });
  const answer = (await response.json().catch(() => ({}))) as Answer;
  if (!response.ok) throw new Error(answer.errorDesc || `The bank answered ${response.status}.`);
  return (answer.responseList || []).flatMap((item) => (item.tableDetails?.columnMap ? [item.tableDetails.columnMap] : []));
}

/** Every customer with their accounts (type, balance and currency), sorted by name. */
export async function loadCustomers(): Promise<Customer[]> {
  const customers = await bankRows("customer", "getAllCustomers");
  const filled = await Promise.all(
    customers.map(async (row) => {
      const listed = await bankRows("account", "getCustomerAccounts", { customerId: row.customerId });
      // the list leaves the currency out; each account's own details have it
      const accounts = await Promise.all(
        listed.map(async (account) => {
          const [detail] = await bankRows("account", "getAccountDetails", { accountId: account.accountId });
          return { accountId: account.accountId, type: account.accountType, balance: account.balance, currency: detail?.currency || "" };
        }),
      );
      return {
        customerId: row.customerId,
        name: row.name,
        tpin: row.passcode,
        country: String(row.phone || "").startsWith("+65") ? ("SG" as const) : ("MY" as const),
        accounts,
      };
    }),
  );
  return filled.sort((a, b) => a.name.localeCompare(b.name));
}

export const money = (amount: string, currency: string) => {
  const value = Number(amount);
  const text = Number.isFinite(value) ? value.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : amount;
  return `${currency} ${text}`.trim();
};

// What each table holds, in the bank's words and the database's
export const TABLES = [
  {
    name: "customer",
    about: "Who the customer is. One row per person.",
    columns: [
      ["customerId", "Phone code", "7 digits. What the caller says to identify themselves."],
      ["passcode", "TPIN", "The telephone PIN. The assistant checks it and never says it."],
      ["name", "Name", "As the bank addresses them."],
      ["dob", "Date of birth", "YYYY-MM-DD."],
      ["phone", "Mobile number", "+65 for Singapore, +60 for Malaysia."],
      ["email", "Email", ""],
      ["address", "Address", ""],
    ],
    methods: [
      ["getAllCustomers", "nothing", "every customer", false],
      ["getCustomerDetails", "customerId", "name and passcode, used to check the TPIN", true],
      ["insertCustomer", "name, passcode, dob, phone, email, address", "a new customer and their first account", false],
      ["deleteCustomer", "customerId", "removes the customer, their accounts and transactions", false],
    ],
  },
  {
    name: "account",
    about: "What the customer holds. A customer can have several.",
    columns: [
      ["accountId", "Account number", "12 digits."],
      ["customerId", "Phone code", "Whose account it is."],
      ["accountType", "Account type", "Savings Account, Current Account, Fixed Deposit…"],
      ["balance", "Balance", "Moves with every transaction."],
      ["currency", "Currency", "SGD or MYR."],
    ],
    methods: [
      ["getCustomerAccounts", "customerId", "every account of that customer, with balances", true],
      ["getAccountDetails", "accountId", "one account, with its currency", true],
      ["insertAccount", "customerId, accountType, balance, currency", "a new account", false],
      ["deleteAccount", "accountId", "removes the account", false],
    ],
  },
  {
    name: "transaction",
    about: "Money in and out of an account, newest first.",
    columns: [
      ["txnId", "Reference", "Given by the bank."],
      ["accountId", "Account number", "Which account it moved."],
      ["type", "Credit or debit", "CREDIT is money in, DEBIT is money out."],
      ["amount", "Amount", "In the account's currency."],
      ["balanceAfterTxn", "Balance after", "The balance once it went through."],
      ["description", "Description", "e.g. Salary, PayNow transfer, GIRO bill."],
      ["date", "Date", "When it was recorded."],
    ],
    methods: [
      ["getTransactionHistory", "accountId", "the account's transactions, newest first", true],
      ["insertTransaction", "accountId, type, amount, description", "records it and moves the balance", false],
    ],
  },
] as const;
