const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const requiredFiles = [
  "index.html",
  "styles.css",
  "script.js",
  "README.md",
  ".env.example",
  "package.json",
  "docs/deployment.md",
  "docs/seo-checklist.md",
];

const errors = [];

for (const file of requiredFiles) {
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath)) {
    errors.push(`Missing required file: ${file}`);
  }
}

const html = fs.readFileSync(path.join(root, "index.html"), "utf8");

if (!html.includes("<title>")) {
  errors.push("index.html is missing a <title> tag.");
}

if (!html.includes('name="description"')) {
  errors.push("index.html is missing a meta description.");
}

if (!html.includes("<h1>")) {
  errors.push("index.html is missing an h1.");
}

if (!html.includes("formsubmit.co")) {
  errors.push("index.html no longer contains the configured form endpoint.");
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("Project structure lint passed.");
