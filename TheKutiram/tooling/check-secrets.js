const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const includeExtensions = new Set([".html", ".css", ".js", ".md", ".json", ".example"]);
const blockedFileNames = new Set([".env"]);
const secretPatterns = [
  /sk-[a-zA-Z0-9]{20,}/,
  /ghp_[a-zA-Z0-9]{20,}/,
  /github_pat_[a-zA-Z0-9_]{20,}/,
  /AKIA[0-9A-Z]{16}/,
  /-----BEGIN (RSA|EC|OPENSSH|DSA|PRIVATE) KEY-----/,
];

const findings = [];

const walk = (dir) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === "dist" || entry.name === ".git") {
      continue;
    }

    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      walk(fullPath);
      continue;
    }

    if (blockedFileNames.has(entry.name)) {
      findings.push(`Blocked file present in project: ${path.relative(root, fullPath)}`);
      continue;
    }

    const extension = path.extname(entry.name);
    const pseudoExtension = entry.name.endsWith(".example") ? ".example" : extension;

    if (!includeExtensions.has(pseudoExtension)) {
      continue;
    }

    const content = fs.readFileSync(fullPath, "utf8");

    for (const pattern of secretPatterns) {
      if (pattern.test(content)) {
        findings.push(`Potential secret found in ${path.relative(root, fullPath)}`);
        break;
      }
    }
  }
};

walk(root);

if (findings.length) {
  console.error(findings.join("\n"));
  process.exit(1);
}

console.log("No obvious committed secrets found in project files.");
