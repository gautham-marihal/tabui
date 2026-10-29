import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const showcaseDir = path.resolve(here, "..");
const widgetDir = path.resolve(showcaseDir, "../widget");
const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";

console.log("[widget-export] Building the embeddable widget from ../widget ...");
execFileSync(npmCommand, ["run", "build"], {
  cwd: widgetDir,
  stdio: "inherit",
  env: { ...process.env, VITE_ENVIRONMENT: "production" },
});

const distDir = path.join(widgetDir, "dist");
const outputDir = path.join(showcaseDir, "public", "tab-widget");
mkdirSync(outputDir, { recursive: true });
for (const filename of ["tab-widget.iife.js", "tab-widget.css"]) {
  const source = path.join(distDir, filename);
  if (!existsSync(source)) {
    if (filename.endsWith(".css")) continue;
    throw new Error(`Expected widget build output was not found: ${source}`);
  }
  copyFileSync(source, path.join(outputDir, filename));
  console.log(`[widget-export] Updated public/tab-widget/${filename}`);
}
