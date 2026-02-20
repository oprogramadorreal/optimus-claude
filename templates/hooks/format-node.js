/**
 * PostToolUse hook: run prettier on web files after Edit/Write.
 * Walks up from the file to find the nearest node_modules with prettier,
 * so it works in both single projects and monorepos without workspaces.
 */
const { readFileSync, existsSync } = require('fs');
const { execSync } = require('child_process');
const path = require('path');

const data = JSON.parse(readFileSync(0, 'utf8'));
const filePath = (data.tool_input || {}).file_path || '';
if (!filePath) process.exit(0);

const exts = ['.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.css', '.scss', '.html'];
if (!exts.some(ext => filePath.endsWith(ext))) process.exit(0);

let dir = path.dirname(path.resolve(filePath));
while (dir !== path.dirname(dir)) {
  if (existsSync(path.join(dir, 'node_modules', 'prettier'))) {
    try { execSync(`npx prettier --write --log-level silent "${filePath}"`, { cwd: dir, stdio: 'ignore' }); } catch {}
    break;
  }
  dir = path.dirname(dir);
}
