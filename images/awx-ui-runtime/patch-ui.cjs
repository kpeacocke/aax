// The pinned UI probes a legacy notification role that the devel API removed.
// A failed optional probe must not prevent reading projects or job templates.
const fs = require('node:fs');
const path = require('node:path');

const file = path.join(process.argv[2] || '/src', 'frontend/common/crud/useGet.tsx');
const original = fs.readFileSync(file, 'utf8');
const marker = '    if (!response.ok) {\n      throw await createRequestError(response);\n    }';
if (original.split(marker).length !== 2) {
  throw new Error('Pinned UI request handler changed; review compatibility patch');
}
const replacement = `    if (!response.ok) {
      // AAX: fail closed for this unsupported optional role probe only.
      const parsedUrl = new URL(url, window.location.origin);
      if (
        response.status === 400 &&
        parsedUrl.pathname === '/api/v2/organizations/' &&
        parsedUrl.searchParams.get('role_level') === 'notification_admin_role'
      ) {
        const body = await response.clone().json().catch(() => null);
        if (body?.detail === 'The permission notification_admin_role is not valid for model organization') {
          return { count: 0, next: null, previous: null, results: [] } as ResponseBody;
        }
      }
      throw await createRequestError(response);
    }`;
fs.writeFileSync(file, original.replace(marker, replacement));
