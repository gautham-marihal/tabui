// Runs a command from the bank's own Python environment (bank/.venv), so the commands work the same on Windows,
// macOS and Linux. `setup` makes the environment and installs bank/requirements-dev.txt.
//   node bank/py.mjs setup
//   node bank/py.mjs <python arguments…>        e.g. -m bank.seed, -m alembic upgrade head, -m pytest
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const venvPython = join(here, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const run = (command, args) => spawnSync(command, args, { cwd: here, stdio: 'inherit' }).status ?? 1;

const args = process.argv.slice(2);
if (args[0] === 'setup') {
  if (!existsSync(venvPython)) {
    const status = run(process.platform === 'win32' ? 'python' : 'python3', ['-m', 'venv', '.venv']);
    if (status) process.exit(status);
  }
  process.exit(run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements-dev.txt']));
}
if (!existsSync(venvPython)) {
  console.error('The bank has no Python environment yet: run node bank/py.mjs setup first.');
  process.exit(1);
}
process.exit(run(venvPython, args));
