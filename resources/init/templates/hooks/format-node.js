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

const exts = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.mts', '.cts', '.vue', '.svelte', '.astro', '.css', '.scss', '.html', '.json', '.yaml', '.yml', '.graphql'];
if (!exts.some(ext => filePath.endsWith(ext))) process.exit(0);

let dir = path.dirname(path.resolve(filePath));
while (dir !== path.dirname(dir)) {
  if (existsSync(path.join(dir, 'node_modules', 'prettier'))) {
    try {
      const pkgPath = path.join(dir, 'node_modules', 'prettier', 'package.json');
      const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
      const binEntry = typeof pkg.bin === 'string' ? pkg.bin : (pkg.bin || {}).prettier;
      if (!binEntry) break;
      const cli = path.resolve(dir, 'node_modules', 'prettier', binEntry);
      execSync(`"${process.execPath}" "${cli}" --write --log-level silent "${filePath}"`, {
        cwd: dir,
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    } catch (err) {
      const stderr = (err.stderr || Buffer.alloc(0)).toString().trim();
      const msg = stderr.split('\n')[0] || `exit code ${err.status}`;
      process.stderr.write(`[format-node] prettier failed: ${msg}\n`);
    }
    break;
  }
  dir = path.dirname(dir);
}
