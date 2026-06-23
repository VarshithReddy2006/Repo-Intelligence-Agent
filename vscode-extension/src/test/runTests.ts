/**
 * Test runner — uses Mocha directly (no VS Code electron host required).
 *
 * Run: node out/test/runTests.js
 */

import * as path from 'path';
import Mocha from 'mocha';
import * as glob from 'glob';

export function run(): Promise<void> {
  const mocha = new Mocha({ ui: 'bdd', color: true, timeout: 10000 });

  const testsRoot = path.resolve(__dirname, '.');
  const files = glob.sync('**/*.test.js', { cwd: testsRoot });

  for (const f of files) {
    mocha.addFile(path.resolve(testsRoot, f));
  }

  return new Promise((resolve, reject) => {
    mocha.run((failures) => {
      if (failures > 0) {
        reject(new Error(`${failures} test(s) failed.`));
      } else {
        resolve();
      }
    });
  });
}

// Allow direct execution
void run().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
