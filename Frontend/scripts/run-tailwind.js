process.env.BROWSERSLIST_IGNORE_OLD_DATA = "1";

const { spawnSync } = require("node:child_process");

const cliPath = require.resolve("tailwindcss/lib/cli.js");
const result = spawnSync(process.execPath, [cliPath, ...process.argv.slice(2)], {
  stdio: "inherit",
  env: process.env,
});

process.exit(result.status === null ? 1 : result.status);
