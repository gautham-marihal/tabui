import Link from "next/link";

import Footer from "../components/Footer";
import Header from "../components/Header";
import { bankFetch, CrmNotConfigured } from "@/lib/crm";

import styles from "./page.module.scss";

// The bank's CRM: its customers, and one customer's whole picture (accounts, cards, loans, cases, and what calls left
// behind). Read on the server from the bank (BANK_API_URL), so the bank's key never reaches the browser. Account and
// card numbers come masked from the bank; a PIN or code is never shown.

export const dynamic = "force-dynamic";

type Search = { q?: string; market?: string; cif?: string };
type Row = Record<string, string | number | boolean | null>;
type Customer = Row & {
  accounts: Row[];
  cards: Row[];
  loans: Row[];
  direct_debits: Row[];
  cases: Row[];
  callbacks: Row[];
  hand_overs: Row[];
  service_requests: Row[];
};

const money = (value: unknown, currency = "") =>
  typeof value === "number" ? `${currency ? `${currency} ` : ""}${value.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—";
const when = (value: unknown) => (typeof value === "string" ? new Date(value).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "");

async function read<T>(path: string, search = ""): Promise<{ data?: T; problem?: string }> {
  try {
    const answer = await bankFetch(path, { search });
    if (answer.status === 404) return { problem: "There is no customer with that CIF." };
    if (answer.status !== 200) {
      const error = (answer.body as { error?: string })?.error || `HTTP ${answer.status}`;
      return { problem: `The bank's CRM answered with an error: ${error}.` };
    }
    return { data: answer.body as T };
  } catch (error) {
    if (error instanceof CrmNotConfigured) return { problem: error.message };
    return { problem: `The bank's CRM did not answer. Is the bank running? (${error instanceof Error ? error.message : "unknown error"})` };
  }
}

export default async function CrmPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q = "", market = "", cif = "" } = await searchParams;
  const query = new URLSearchParams({ ...(q ? { q } : {}), ...(market ? { market } : {}) }).toString();
  const list = await read<{ items: Row[] }>("customers", query ? `?${query}` : "");
  const detail = cif ? await read<Customer>(`customers/${encodeURIComponent(cif)}`) : null;
  const backTo = `/crm${query ? `?${query}` : ""}`;

  return (
    <div className={styles.page}>
      <Header />
      <div className="main-content">
        <main className={styles.main}>
          <div className={styles.intro}>
            <h1>Bank CRM</h1>
            <p>Customers of the bank behind the phone agents, and what each call left behind. Numbers are masked; PINs and codes are never shown.</p>
          </div>

          <form className={styles.search} action="/crm">
            <input name="q" defaultValue={q} placeholder="Name, CIF, or the last digits of a mobile or account" aria-label="Search customers" />
            <select name="market" defaultValue={market} aria-label="Market">
              <option value="">Both markets</option>
              <option value="sg">Singapore</option>
              <option value="my">Malaysia</option>
            </select>
            <button type="submit">Search</button>
          </form>

          {list.problem && <p className={styles.problem}>{list.problem}</p>}

          <div className={styles.layout}>
            {list.data && (
              <section className={styles.list} aria-label="Customers">
                <p className={styles.count}>
                  {list.data.items.length} {list.data.items.length === 1 ? "customer" : "customers"}
                </p>
                <ul>
                  {list.data.items.map((c) => {
                    const href = `/crm?${new URLSearchParams({ ...(q ? { q } : {}), ...(market ? { market } : {}), cif: String(c.cif) })}`;
                    return (
                      <li key={String(c.cif)} className={c.cif === cif ? styles.active : ""}>
                        <Link href={href}>
                          <strong>{c.name}</strong>
                          <span>
                            {c.cif} · {String(c.market).toUpperCase()} · {c.type} · {c.accounts} {c.accounts === 1 ? "account" : "accounts"}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}

            <section className={styles.detail} aria-label="Customer">
              {!cif && <p className={styles.hint}>Choose a customer to see their accounts, cards, cases and recent dealings.</p>}
              {detail?.problem && <p className={styles.problem}>{detail.problem}</p>}
              {detail?.data && <CustomerDetail customer={detail.data} backTo={backTo} />}
            </section>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  );
}

function CustomerDetail({ customer: c, backTo }: { customer: Customer; backTo: string }) {
  return (
    <article>
      <div className={styles.detailHead}>
        <div>
          <h2>{c.name}</h2>
          <p>
            {c.cif} · {String(c.market).toUpperCase()} · {c.type}
            {c.segment ? ` · ${c.segment}` : ""}
            {c.access_level ? ` · access ${c.access_level}` : ""}
            {c.iq_member ? " · iQ member" : ""}
          </p>
          {(c.contact || c.mobile) && (
            <p>
              {c.contact}
              {c.contact && c.mobile ? " · " : ""}
              {c.mobile}
            </p>
          )}
        </div>
        <Link href={backTo} className={styles.close}>
          Close
        </Link>
      </div>

      <Table
        title="Accounts"
        rows={c.accounts}
        columns={[
          ["Account", (r) => r.number],
          ["Product", (r) => r.product],
          ["Balance", (r) => money(r.ledger_balance, String(r.currency))],
          ["Available", (r) => (r.available_balance === null ? "—" : money(r.available_balance, String(r.currency)))],
          ["Status", (r) => r.status],
        ]}
      />
      <Table
        title="Cards"
        rows={c.cards}
        columns={[
          ["Card", (r) => r.number],
          ["Product", (r) => r.product],
          ["Status", (r) => r.status],
          ["Limit", (r) => money(r.limit)],
          ["Owed", (r) => money(r.balance)],
          ["Due", (r) => r.due],
        ]}
      />
      <Table
        title="Loans"
        rows={c.loans}
        columns={[
          ["Loan", (r) => r.id],
          ["Product", (r) => r.product],
          ["Monthly", (r) => money(r.monthly)],
          ["Next due", (r) => r.due],
        ]}
      />
      <Table
        title="Direct debits"
        rows={c.direct_debits}
        columns={[
          ["Mandate", (r) => r.id],
          ["Merchant", (r) => r.merchant],
          ["Amount", (r) => money(r.amount)],
          ["Status", (r) => r.status],
        ]}
      />
      <Table
        title="Open cases"
        rows={c.cases}
        columns={[
          ["Case", (r) => r.id],
          ["Topic", (r) => r.topic],
          ["Account", (r) => r.account],
          ["Service manager", (r) => r.service_manager],
        ]}
      />
      <Table
        title="Hand-overs to people"
        rows={c.hand_overs}
        columns={[
          ["Reference", (r) => r.id],
          ["Queue", (r) => r.queue],
          ["Why", (r) => r.reason],
          ["Summary for the person", (r) => r.summary],
          ["When", (r) => when(r.at)],
        ]}
      />
      <Table
        title="Call-backs"
        rows={c.callbacks}
        columns={[
          ["Reference", (r) => r.id],
          ["Number", (r) => r.number],
          ["Reason", (r) => r.reason],
          ["Status", (r) => r.status],
          ["When", (r) => when(r.at)],
        ]}
      />
      <Table
        title="Service requests"
        rows={c.service_requests}
        columns={[
          ["Request", (r) => r.id],
          ["Type", (r) => r.type],
          ["Notes", (r) => r.notes],
          ["When", (r) => when(r.at)],
        ]}
      />
    </article>
  );
}

function Table({ title, rows, columns }: { title: string; rows: Row[]; columns: [string, (row: Row) => unknown][] }) {
  return (
    <section className={styles.block}>
      <h3>
        {title} <small>({rows.length})</small>
      </h3>
      {rows.length === 0 ? (
        <p className={styles.none}>None.</p>
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
                    <td key={label}>{String(cell(row) ?? "")}</td>
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
