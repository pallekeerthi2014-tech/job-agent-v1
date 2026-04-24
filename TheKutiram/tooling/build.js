const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const dist = path.join(root, "dist");
const assetsSrc = path.join(root, "assets");
const assetsDest = path.join(dist, "assets");
const filesToCopy = ["index.html", "styles.css", "script.js"];

const removeDir = (target) => {
  if (fs.existsSync(target)) {
    fs.rmSync(target, { recursive: true, force: true });
  }
};

const copyDir = (source, destination) => {
  fs.mkdirSync(destination, { recursive: true });

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);

    if (entry.isDirectory()) {
      copyDir(sourcePath, destinationPath);
    } else {
      fs.copyFileSync(sourcePath, destinationPath);
    }
  }
};

removeDir(dist);
fs.mkdirSync(dist, { recursive: true });

for (const file of filesToCopy) {
  fs.copyFileSync(path.join(root, file), path.join(dist, file));
}

copyDir(assetsSrc, assetsDest);

console.log("Built static site into dist/");
