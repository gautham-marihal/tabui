// The bank database (Ashwin's API), as the showcase reads it: on the server,
// POST <BANK_API_URL>/TetherfiDbRestApi/dboperations with the header Region: <BANK_REGION>. From showcase/.env.local:
//   BANK_API_URL   where the bank API runs (e.g. http://16.79.174.151:3322)
//   BANK_REGION    the Region header (default DB2)

export type Row = Record<string, string>;
export type BankResult = { rows: Row[]; failed?: string };

type Item = { tableDetails: { columnMap: Row } | null; status: string; description: string | null };
type Answer = { responseCode: number; errorDesc: string | null; responseList: Item[] | null };

export class CrmNotConfigured extends Error {}

function bankSettings() {
  const url = (process.env.BANK_API_URL || "").trim().replace(/\/+$/, "");
  if (!url) throw new CrmNotConfigured("The bank is not set up: add BANK_API_URL to showcase/.env.local.");
  return { url, region: (process.env.BANK_REGION || "DB2").trim() };
}

/** One dboperations call. Rows found come back in `rows`; a call that found nothing or was refused says why in `failed`. */
export async function bankCall(entity: string, method: string, columnMap: Row = {}): Promise<BankResult> {
  const { url, region } = bankSettings();
  const response = await fetch(`${url}/TetherfiDbRestApi/dboperations`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", Region: region },
    body: JSON.stringify({ ucid: "tabui-crm", dnis: "default", channel: "chat", entity, method, details: [{ columnMap }] }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  let answer: Answer;
  try {
    answer = (await response.json()) as Answer;
  } catch {
    throw new Error(`The bank answered with something that is not JSON (HTTP ${response.status}).`);
  }
  if (answer.responseCode !== 200) throw new Error(answer.errorDesc || `HTTP ${response.status}`);
  const items = answer.responseList || [];
  const rows = items.flatMap((item) => (item.tableDetails ? [item.tableDetails.columnMap] : []));
  const failure = items.find((item) => item.status !== "SUCCESS");
  return { rows, failed: failure ? failure.description || "Failed." : undefined };
}
