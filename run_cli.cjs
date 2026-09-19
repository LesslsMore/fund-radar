const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

// find big electron exe
const dir = "C:\\Program Files (x86)\\Tencent\\微信web开发者工具";
const exe = fs.readdirSync(dir)
  .map((f) => path.join(dir, f))
  .filter((f) => f.toLowerCase().endsWith(".exe"))
  .find((f) => { try { return fs.statSync(f).size > 50000000 && !/node/i.test(path.basename(f)); } catch (e) { return false; } });

const CLI = path.join(dir, "resources", "app.asar.unpacked", "js", "common", "cli", "index.js");
const bootstrap = `const e=process.argv[1];process.env.cwd=process.cwd();process.argv=[process.execPath,'--ms-enable-electron-run-as-node',e,'--electron'].concat(process.argv.slice(2));require(e)`;

const args = process.argv.slice(2); // e.g. ["islogin"] or ["upload","--project",...]
const fullArgs = ["-e", bootstrap, CLI].concat(args);

const child = spawn(exe, fullArgs, {
  env: Object.assign({}, process.env, { ELECTRON_RUN_AS_NODE: "1" }),
  stdio: ["pipe", "pipe", "pipe"],
});

let out = "", err = "";
child.stdout.on("data", (d) => { out += d; });
child.stderr.on("data", (d) => { err += d; });

// after a short delay, send "y" in case the enable-CLI prompt appears
setTimeout(() => {
  try { child.stdin.write("y\n"); } catch (e) {}
}, 4000);
setTimeout(() => {
  try { child.stdin.end(); } catch (e) {}
}, 8000);

child.on("close", (code) => {
  console.log("EXITCODE=" + code);
  console.log("===STDOUT===");
  console.log(out);
  console.log("===STDERR===");
  console.log(err);
  process.exit(0);
});
