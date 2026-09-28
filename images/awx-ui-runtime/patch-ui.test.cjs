const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');

test('unsupported notification probe fails closed; other API errors remain errors', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'aax-ui-test-'));
  try {
    const file = path.join(root, 'frontend/common/crud/useGet.tsx');
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, '    if (!response.ok) {\n      throw await createRequestError(response);\n    }');
    execFileSync(process.execPath, [path.join(__dirname, 'patch-ui.cjs'), root]);
    const code = fs.readFileSync(file, 'utf8').replace(' as ResponseBody', '');
    const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
    const run = new AsyncFunction('url', 'response', 'window', 'createRequestError', code);
    const detail = 'The permission notification_admin_role is not valid for model organization';
    const url = '/api/v2/organizations/?role_level=notification_admin_role';
    const invoke = (target, status, message) => run(
      target, new Response(JSON.stringify({ detail: message }), { status }),
      { location: { origin: 'https://awx.example.test' } },
      async () => new Error('API request failed')
    );
    assert.deepEqual(await invoke(url, 400, detail), { count: 0, next: null, previous: null, results: [] });
    for (const status of [401, 403, 500]) {
      await assert.rejects(invoke(url, status, detail), /API request failed/);
    }
    await assert.rejects(invoke(url, 400, 'Unrelated validation error'), /API request failed/);
    await assert.rejects(invoke('/api/v2/projects/16/', 400, detail), /API request failed/);
    await assert.rejects(invoke('/api/v2/organizations/?role_level=admin_role', 400, detail), /API request failed/);
    assert.throws(() => execFileSync(process.execPath, [path.join(__dirname, 'patch-ui.cjs'), root], { stdio: 'pipe' }));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
