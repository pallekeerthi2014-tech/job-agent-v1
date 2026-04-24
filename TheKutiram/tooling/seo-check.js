const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");

const checks = [
  { label: "title tag", test: /<title>[^<]+<\/title>/i },
  { label: "meta description", test: /<meta\s+name="description"\s+content="[^"]+"/i },
  { label: "viewport tag", test: /<meta\s+name="viewport"/i },
  { label: "hero h1", test: /<h1>[^<]+<\/h1>/i },
  { label: "image alt text", test: /<img[^>]+alt="[^"]+"/i },
];

const missing = checks.filter((item) => !item.test.test(html)).map((item) => item.label);

if (missing.length) {
  console.error(`SEO check failed. Missing: ${missing.join(", ")}`);
  process.exit(1);
}

console.log("Basic SEO checks passed.");
