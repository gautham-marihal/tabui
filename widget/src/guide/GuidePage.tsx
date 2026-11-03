import { useEffect, useMemo, useRef, useState } from "react";
import { MdCheck, MdChat, MdClose, MdContentCopy, MdLock, MdStorage, MdTune, MdAutoAwesome } from "react-icons/md";
import { loadCustomers, money, TABLES, type Customer } from "./bank";
import { AGENTS, CANNOT, LOGINS, SERVICES } from "./agents";
import "./guide.scss";

// The dev page behind the chat widget: what Weave Studio is, what each bank agent can and can't do (agents.ts), the
// test customers to try them with (read live from the bank database), other test logins, and the bank database and
// bank services for reference.

// the agent to start with: the one that does the most
const AGENT = AGENTS[0].name;

// DevHarness opens the chat when it hears this
const openChat = () => window.dispatchEvent(new Event("tab-open-chat"));

function Copy({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="gCopy"
      aria-label={`Copy ${label}`}
      title={`Copy ${label}`}
      onClick={() => {
        // the clipboard exists only on https or localhost; elsewhere the code is still there to select
        navigator.clipboard
          ?.writeText(text)
          .then(() => {
            setDone(true);
            window.setTimeout(() => setDone(false), 1400);
          })
          .catch(() => {});
      }}
    >
      <code>{text}</code>
      {done ? <MdCheck aria-hidden size={14} /> : <MdContentCopy aria-hidden size={14} />}
    </button>
  );
}

function SampleChat() {
  return (
    <div className="gPhone" aria-label="An example conversation">
      <div className="gPhoneHead">
        <span className="gDot" aria-hidden />
        <div>
          <strong>Bank assistant</strong>
          <small>Built in Weave Studio</small>
        </div>
      </div>
      <div className="gBubbles">
        <p className="gBot">Welcome to phone banking. How can I help you today?</p>
        <p className="gMe">What’s my balance?</p>
        <p className="gBot">Sure. What is your 7-digit phone code?</p>
        <p className="gMe">It’s 5409881</p>
        <p className="gBot">Thank you, Tan Wei Ming. Please say your TPIN.</p>
        <p className="gMe">1234</p>
        <p className="gBot">You have two accounts: Savings, SGD 17,068.92, and Current, SGD 8,650.00.</p>
      </div>
    </div>
  );
}

function Customers() {
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [problem, setProblem] = useState("");
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState<"All" | "SG" | "MY">("All");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    setProblem("");
    loadCustomers()
      .then((list) => live && setCustomers(list))
      .catch((error: Error) => live && setProblem(error.message));
    return () => {
      live = false;
    };
  }, [attempt]);
  const shown = useMemo(
    () =>
      (customers || []).filter(
        (c) => (country === "All" || c.country === country) && `${c.name} ${c.customerId}`.toLowerCase().includes(query.trim().toLowerCase()),
      ),
    [customers, country, query],
  );

  return (
    <section className="gSection" id="customers" aria-labelledby="customers-title">
      <div className="gSectionHead">
        <span className="gEyebrow">Step 4 needs one of these</span>
        <h2 id="customers-title">Test customers</h2>
        <p>
          Made-up people in the bank database, read live. Pick anyone: give the assistant their phone code, then their TPIN. Click a
          code to copy it.
        </p>
      </div>
      <div className="gToolbar">
        <input className="gSearch" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by name or phone code" aria-label="Search customers" />
        <div className="gPills" role="group" aria-label="Country">
          {(["All", "SG", "MY"] as const).map((c) => (
            <button key={c} type="button" className={country === c ? "on" : ""} aria-pressed={country === c} onClick={() => setCountry(c)}>
              {c === "All" ? "All" : c === "SG" ? "Singapore" : "Malaysia"}
            </button>
          ))}
        </div>
      </div>
      {problem ? (
        <div className="gNotice" role="alert">
          <p>The bank database didn’t answer: {problem}</p>
          <button type="button" className="gButton" onClick={() => setAttempt((n) => n + 1)}>
            Try again
          </button>
        </div>
      ) : !customers ? (
        <p className="gMuted" role="status">
          Reading the customers from the bank database…
        </p>
      ) : (
        <div className="gTableWrap">
          <table className="gTable">
            <thead>
              <tr>
                <th scope="col">Customer</th>
                <th scope="col">Phone code</th>
                <th scope="col">TPIN</th>
                <th scope="col">Accounts</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((c) => (
                <tr key={c.customerId}>
                  <td>
                    <strong>{c.name}</strong>
                    <span className="gFlag">{c.country === "SG" ? "Singapore" : "Malaysia"}</span>
                  </td>
                  <td>
                    <Copy text={c.customerId} label={`${c.name}’s phone code`} />
                  </td>
                  <td>
                    <Copy text={c.tpin} label={`${c.name}’s TPIN`} />
                  </td>
                  <td>
                    <ul className="gAccounts">
                      {c.accounts.map((a) => (
                        <li key={a.accountId}>
                          <span>{a.type}</span>
                          <b>{money(a.balance, a.currency)}</b>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
              {!shown.length && (
                <tr>
                  <td colSpan={4} className="gMuted">
                    No customer matches that.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <div className="gCard gLogins">
        <h3>Other ways to log in</h3>
        <p className="gMuted">Some lines check you differently. These test customers work for them.</p>
        <table className="gTable">
          <thead>
            <tr>
              <th scope="col">Login</th>
              <th scope="col">Agent</th>
              <th scope="col">Try with</th>
            </tr>
          </thead>
          <tbody>
            {LOGINS.map(([login, agent, details]) => (
              <tr key={login}>
                <td>
                  <strong>{login}</strong>
                </td>
                <td>{agent}</td>
                <td>{details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Database() {
  return (
    <section className="gSection" id="database" aria-labelledby="database-title">
      <div className="gSectionHead">
        <span className="gEyebrow">For reference</span>
        <h2 id="database-title">The bank database</h2>
        <p>
          Three tables behind one API. The assistant asks in the bank’s words (phone code, TPIN, account number) and the database
          stores them under its own column names. Methods marked <span className="gTag">Assistant</span> are the ones the assistant
          calls.
        </p>
      </div>
      <div className="gTables">
        {TABLES.map((table) => (
          <article className="gCard gTableCard" key={table.name}>
            <header>
              <MdStorage aria-hidden size={18} />
              <h3>
                <code>{table.name}</code>
              </h3>
            </header>
            <p className="gMuted">{table.about}</p>
            <h4>Columns</h4>
            <dl className="gColumns">
              {table.columns.map(([column, word, note]) => (
                <div key={column}>
                  <dt>
                    <code>{column}</code>
                    <span>{word}</span>
                  </dt>
                  {note && <dd>{note}</dd>}
                </div>
              ))}
            </dl>
            <h4>Methods</h4>
            <ul className="gMethods">
              {table.methods.map(([method, send, get, used]) => (
                <li key={method}>
                  <div>
                    <code>{method}</code>
                    {used && <span className="gTag">Assistant</span>}
                  </div>
                  <small>
                    Send <b>{send}</b>, get {get}.
                  </small>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
      <div className="gCard gApi">
        <div>
          <h3>Calling it</h3>
          <p className="gMuted">
            Every method is the same call: <code>POST /TetherfiDbRestApi/dboperations</code> with the header <code>Region: DB2</code>.
            Rows come back in <code>responseList[].tableDetails.columnMap</code>.
          </p>
        </div>
        <pre aria-label="An example request">{`{
  "ucid": "any-call-id",
  "dnis": "default",
  "channel": "IVR",
  "entity": "account",
  "method": "getCustomerAccounts",
  "details": [{ "columnMap": { "customerId": "5409881" } }]
}`}</pre>
      </div>
      <div className="gCard gApi">
        <div>
          <h3>The bank services</h3>
          <p className="gMuted">
            What the database doesn’t hold comes from a test API that follows the bank’s call flows, at{" "}
            <code>https://weave-mock-api.vercel.app</code> (<code>GET /routes</code> lists every route). Its records belong to the same
            customers and account numbers. Actions answer with a reference but change no balance.
          </p>
        </div>
        <dl className="gColumns">
          {SERVICES.map(([area, what]) => (
            <div key={area}>
              <dt>
                <span>{area}</span>
              </dt>
              <dd>{what}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

// Sections fade up as they come into view. Only when the browser can watch for that and the person hasn't asked for
// less motion; otherwise (and until this runs) everything simply shows.
function useReveal() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const page = root.current;
    if (!page || !("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const parts = [...page.querySelectorAll<HTMLElement>(".gSection, .gHero")];
    const watch = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("gIn");
          watch.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    // what is already in view shows at once; the rest waits for its turn
    parts.forEach((part) => {
      if (part.getBoundingClientRect().top < window.innerHeight) part.classList.add("gIn");
      watch.observe(part);
    });
    page.classList.add("gMoving");
    return () => watch.disconnect();
  }, []);
  return root;
}

export default function GuidePage() {
  const root = useReveal();
  return (
    <div className="guide" ref={root}>
      <header className="gTop">
        <div className="gBrand">
          <span className="gLogo" aria-hidden>
            W
          </span>
          Weave Studio
        </div>
        <nav aria-label="On this page">
          <a href="#how">How to try it</a>
          <a href="#scope">What they can do</a>
          <a href="#customers">Test customers</a>
          <a href="#database">Database</a>
        </nav>
      </header>

      <section className="gHero">
        <div>
          <span className="gEyebrow">Try it yourself</span>
          <h1>Talk to bank agents built in Weave Studio</h1>
          <p className="gLead">
            Phone-banking agents for OCBC Singapore and Malaysia. They check who you are, then help with accounts, cheques, cards,
            payments, appointments and more, from a bank database and the bank’s services. No set-up: open the chat, pick an agent and
            a test customer below, and ask.
          </p>
          <div className="gActions">
            <button type="button" className="gButton gPrimary" onClick={openChat}>
              <MdChat aria-hidden size={18} /> Open the chat
            </button>
            <a className="gButton" href="#customers">
              See test customers
            </a>
          </div>
        </div>
        <SampleChat />
      </section>

      <section className="gSection" aria-labelledby="what-title">
        <div className="gSectionHead">
          <span className="gEyebrow">What it is</span>
          <h2 id="what-title">Weave Studio builds AI agents for calls and chats</h2>
        </div>
        <div className="gGrid3">
          <article className="gCard">
            <MdAutoAwesome aria-hidden size={22} className="gIcon" />
            <h3>Build without code</h3>
            <p>Describe the agent, choose its voice and language, and set what it may say and do.</p>
          </article>
          <article className="gCard">
            <MdTune aria-hidden size={22} className="gIcon" />
            <h3>Connect your systems</h3>
            <p>Plug in a database or an API. These agents read the bank database and the bank services for everything else.</p>
          </article>
          <article className="gCard">
            <MdLock aria-hidden size={22} className="gIcon" />
            <h3>Safe by design</h3>
            <p>They verify callers before sharing anything, never say a code back, and read back every change before making it.</p>
          </article>
        </div>
      </section>

      <section className="gSection" id="how" aria-labelledby="how-title">
        <div className="gSectionHead">
          <span className="gEyebrow">How to try it</span>
          <h2 id="how-title">Four steps, about a minute</h2>
        </div>
        <ol className="gSteps">
          <li>
            <b>Open the chat</b>
            <span>
              The purple button at the bottom right, or{" "}
              <button type="button" className="gLink" onClick={openChat}>
                open it here
              </button>
              .
            </span>
          </li>
          <li>
            <b>Choose “{AGENT}”</b>
            <span>It does the most; the others are <a href="#scope">below</a>. Then start a chat or a voice call.</span>
          </li>
          <li>
            <b>Ask for something</b>
            <span>For example “What’s my balance?” or “Stop a cheque”. It asks who you are when it needs to.</span>
          </li>
          <li>
            <b>Give a test customer’s codes</b>
            <span>
              The phone code, then the TPIN, from <a href="#customers">the table below</a>. Then ask anything from the list.
            </span>
          </li>
        </ol>
      </section>

      <section className="gSection" id="scope" aria-labelledby="scope-title">
        <div className="gSectionHead">
          <span className="gEyebrow">What they can do</span>
          <h2 id="scope-title">The agents in the chat, and what each one does</h2>
        </div>
        <div className="gAgents">
          {AGENTS.map((agent) => (
            <article className="gCard gYes gAgent" key={agent.name}>
              <h3>{agent.name}</h3>
              <p className="gMuted">{agent.line}</p>
              <ul>
                {agent.can.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <div className="gChips" role="group" aria-label={`Things to ask ${agent.name}`}>
                {agent.ask.map((line) => (
                  <Copy key={line} text={line} label={`“${line}”`} />
                ))}
              </div>
            </article>
          ))}
          <article className="gCard gNo">
            <h3>
              <MdClose aria-hidden size={20} /> None of them
            </h3>
            <ul>
              {CANNOT.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </article>
        </div>
        <p className="gMuted gNote">Try a wrong TPIN too: they ask again, and after three wrong tries they offer a call-back instead.</p>
      </section>

      <Customers />
      <Database />

      <footer className="gFoot">Every customer, account and transaction here is made up, for trying the assistant.</footer>
    </div>
  );
}
