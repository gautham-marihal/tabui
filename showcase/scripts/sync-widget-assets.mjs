import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const showcaseDir = path.resolve(here, "..");
const widgetDist = path.resolve(showcaseDir, "../widget/dist");
const publicDir = path.join(showcaseDir, "public", "tab-widget");
mkdirSync(publicDir, { recursive: true });

for (const filename of ["tab-widget.iife.js", "tab-widget.css"]) {
  const source = path.join(widgetDist, filename);
  if (!existsSync(source)) {
    if (filename.endsWith(".css")) continue;
    throw new Error(`Widget build output missing: ${source}. Run npm install in widget and rebuild.`);
  }
  copyFileSync(source, path.join(publicDir, filename));
  console.log(`[widget-export] Updated public/tab-widget/${filename}`);
}
