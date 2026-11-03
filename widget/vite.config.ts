import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// The guide page on the dev server shows the bank database's test customers live. The bank's API refuses calls from a
// web page (CORS), so the page posts to /bank-api here and this server asks the bank. Only the reading methods are
// passed on: nothing the page sends can insert or delete. BANK_API_URL points it at another copy of the API.
const BANK_URL = (process.env.BANK_API_URL || "http://16.79.174.151:3322").replace(/\/+$/, "");
const READS: Record<string, string[]> = {
  customer: ["getAllCustomers", "getCustomerDetails"],
  account: ["getCustomerAccounts", "getAccountDetails"],
  transaction: ["getTransactionHistory"],
};

function bankRead(): Plugin {
  return {
    name: "tab-bank-read",
    configureServer(server) {
      server.middlewares.use("/bank-api", (req, res) => {
        const send = (status: number, body: unknown) => {
          res.statusCode = status;
          res.setHeader("content-type", "application/json");
          res.end(typeof body === "string" ? body : JSON.stringify(body));
        };
        if (req.method !== "POST") return send(404, { errorDesc: "Only POST is passed on." });
        let raw = "";
        req.on("data", (chunk) => {
          raw += chunk;
          if (raw.length > 16_384) req.destroy();
        });
        req.on("end", async () => {
          let call: { entity?: string; method?: string; details?: unknown };
          try {
            call = JSON.parse(raw);
          } catch {
            return send(400, { errorDesc: "The request is not valid JSON." });
          }
          if (!call.entity || !call.method || !READS[call.entity]?.includes(call.method))
            return send(403, { errorDesc: "Only the reading methods are passed on." });
          try {
            const answer = await fetch(`${BANK_URL}/TetherfiDbRestApi/dboperations`, {
              method: "POST",
              headers: { "content-type": "application/json", Region: "DB2" },
              body: JSON.stringify({ ucid: "tab-guide", dnis: "default", channel: "WEB", entity: call.entity, method: call.method, details: call.details }),
              signal: AbortSignal.timeout(15_000),
            });
            send(answer.status, await answer.text());
          } catch (error) {
            send(502, { errorDesc: `The bank did not answer (${(error as Error).message}).` });
          }
        });
      });
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), bankRead()],
  server: {
    host: "localhost",
    port: 5174,
    strictPort: true,
    // the names the page may be opened on besides localhost (a server's domain, in Docker): comma separated
    ...(process.env.GUIDE_ALLOWED_HOSTS ? { allowedHosts: process.env.GUIDE_ALLOWED_HOSTS.split(",").map((h) => h.trim()).filter(Boolean) } : {}),
  },
  build: {
    lib: {
      entry: "src/main.tsx", // Widget's entry point
      name: "TABWidget", // Global variable name. TODO: Not needed now. Use in future if needed
      formats: ["iife"],
      fileName: (format) => `tab-widget.${format}.js`,
    },
    rollupOptions: {
      external: [],
      output: {
        globals: {},
      },
    },
    cssCodeSplit: false, // Bundle CSS into a single file,
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
