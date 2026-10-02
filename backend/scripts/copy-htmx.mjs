import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const destination = resolve(root, "app/static/js");
await mkdir(destination, { recursive: true });
await copyFile(resolve(root, "node_modules/htmx.org/dist/htmx.min.js"), resolve(destination, "htmx.min.js"));
await copyFile(resolve(root, "node_modules/htmx.org/LICENSE"), resolve(destination, "HTMX-LICENSE.txt"));
