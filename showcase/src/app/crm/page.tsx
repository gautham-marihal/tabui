import Link from "next/link";

import Footer from "../components/Footer";
import Header from "../components/Header";
import { bankCall, CrmNotConfigured, type Row } from "@/lib/crm";

import styles from "./page.module.scss";

// The bank's three tables (Region DB2): its customers, and one customer's accounts and each account's transactions.
// Read on the server from the bank (BANK_API_URL). The TPIN and OTP never leave the bank, so they are never shown.

export const dynamic = "force-dynamic";

type Search = { q?: string; phone?: string };
type Account = { account: Row; transactions: Row[]; noTransactions?: string };

const money = (value: string | undefined, currency = "") =>
  value ? `${currency ? `${currency} ` : ""}${Number(value).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—";

async function read<T>(load: () => Promise<T>): Promise<{ data?: T; problem?: string }> {
  try {
    return { data: await load() };
  } catch (error) {
    if (error instanceof CrmNotConfigured) return { problem: error.message };
    return { problem: `The bank did not answer. Is it running? (${error instanceof Error ? error.message : "unknown error"})` };
  }
}

async function loadCustomer(phone: string) {
  const details = await bankCall("customer", "getCustomerDetails", { phoneNumber: phone });
  if (!details.rows.length) return { problem: details.failed || "Customer not found." };
  const accounts = await bankCall("account", "getCustomerAccounts", { phoneNumber: phone });
  const withHistory: Account[] = await Promise.all(
    accounts.rows.map(async (account) => {
      const history = await bankCall("transaction", "getTransactionHistory", { accountNumber: account.accountNumber });
      return { account, transactions: history.rows, noTransactions: history.rows.length ? undefined : history.failed };
    }),
  );
  return { customer: details.rows[0], accounts: withHistory };
}

export default async function CrmPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q = "", phone = "" } = await searchParams;
  const list = await read(() => bankCall("customer", "getAllCustomers"));
  const detail = phone ? await read(() => loadCustomer(phone)) : null;
  const needle = q.trim().toLowerCase();
  const customers = (list.data?.rows || []).filter(
    (c) => !needle || [c.name, c.phoneNumber, c.accountNumbers, c.email].some((value) => (value || "").toLowerCase().includes(needle)),
  );
  const backTo = `/crm${q ? `?${new URLSearchParams({ q })}` : ""}`;

  return (
    <div className={styles.page}>
      <Header />
      <div className="main-content">
        <main className={styles.main}>
          <div className={styles.intro}>
            <h1>Bank CRM</h1>
            <p>The customer, account and transaction tables behind the phone agents (Region DB2). TPINs and OTPs are never shown.</p>
          </div>

          <form className={styles.search} action="/crm">
            <input name="q" defaultValue={q} placeholder="Name, phone number, account number or email" aria-label="Search customers" />
            <button type="submit">Search</button>
          </form>

          {list.problem && <p className={styles.problem}>{list.problem}</p>}

          <div className={styles.layout}>
            {list.data && (
              <section className={styles.list} aria-label="Customers">
                <p className={styles.count}>
                  {customers.length} {customers.length === 1 ? "customer" : "customers"}
                </p>
                <ul>
                  {customers.map((c) => {
                    const href = `/crm?${new URLSearchParams({ ...(q ? { q } : {}), phone: c.phoneNumber })}`;
                    const count = c.accountNumbers ? c.accountNumbers.split(",").length : 0;
                    return (
                      <li key={c.phoneNumber} className={c.phoneNumber === phone ? styles.active : ""}>
                        <Link href={href}>
                          <strong>{c.name}</strong>
                          <span>
                            {c.phoneNumber} · {count} {count === 1 ? "account" : "accounts"}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}

            <section className={styles.detail} aria-label="Customer">
              {!phone && <p className={styles.hint}>Choose a customer to see their accounts and transactions.</p>}
              {detail?.problem && <p className={styles.problem}>{detail.problem}</p>}
              {detail?.data?.problem && <p className={styles.problem}>{detail.data.problem}</p>}
              {detail?.data?.customer && <CustomerDetail customer={detail.data.customer} accounts={detail.data.accounts} backTo={backTo} />}
            </section>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  );
}

function CustomerDetail({ customer: c, accounts, backTo }: { customer: Row; accounts: Account[]; backTo: string }) {
  return (
    <article>
      <div className={styles.detailHead}>
        <div>
          <h2>{c.name}</h2>
          <p>
            Phone number {c.phoneNumber} · born {c.dob} · can be deleted: {c.allowDelete === "Y" ? "yes" : "no"}
          </p>
          <p>
            {c.phone} · {c.email} · {c.address}
          </p>
        </div>
        <Link href={backTo} className={styles.close}>
          Close
        </Link>
      </div>

      <Table
        title="Accounts"
        rows={accounts.map(({ account }) => account)}
        columns={[
          ["Account number", (r) => r.accountNumber],
          ["Type", (r) => r.accountType],
          ["Balance", (r) => money(r.balance, r.currency)],
        ]}
      />
      {accounts.map(({ account, transactions, noTransactions }) => (
        <Table
          key={account.accountNumber}
          title={`Transactions on ${account.accountNumber}`}
          rows={transactions}
          empty={noTransactions}
          columns={[
            ["Type", (r) => r.type],
            ["Amount", (r) => money(r.amount, account.currency)],
            ["Description", (r) => r.description],
          ]}
        />
      ))}
    </article>
  );
}

function Table({ title, rows, columns, empty }: { title: string; rows: Row[]; columns: [string, (row: Row) => string][]; empty?: string }) {
  return (
    <section className={styles.block}>
      <h3>
        {title} <small>({rows.length})</small>
      </h3>
      {rows.length === 0 ? (
        <p className={styles.none}>{empty || "None."}</p>
      ) : (
        <div className={styles.scroll}>
          <table>
            <thead>
              <tr>
                {columns.map(([label]) => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {columns.map(([label, cell]) => (
                    <td key={label}>{cell(row)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
