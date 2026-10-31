const fs = require('node:fs');

const title = '🔒 Security: Vulnerable dependencies detected';

function readAudit(path, status) {
  const audit = JSON.parse(fs.readFileSync(path, 'utf8'));
  if (!audit || !Array.isArray(audit.dependencies) || audit.dependencies.length === 0) {
    throw new Error('Dependency audit has no valid dependency inventory');
  }
  const findings = [];
  for (const dependency of audit.dependencies) {
    if (!dependency || typeof dependency.name !== 'string' || !dependency.name.trim() ||
        typeof dependency.version !== 'string' || !dependency.version.trim() ||
        !Array.isArray(dependency.vulns) ||
        dependency.skip_reason) {
      throw new Error('Dependency audit contains an invalid or unaudited dependency');
    }
    for (const vulnerability of dependency.vulns) {
      if (!vulnerability || typeof vulnerability.id !== 'string' || !vulnerability.id.trim() ||
          !Array.isArray(vulnerability.fix_versions) ||
          vulnerability.fix_versions.some(version => typeof version !== 'string')) {
        throw new Error('Dependency audit contains an invalid vulnerability');
      }
      findings.push({
        package: dependency.name,
        version: dependency.version,
        id: vulnerability.id,
        fix_versions: vulnerability.fix_versions
      });
    }
  }
  if (status !== (findings.length > 0 ? '1' : '0')) {
    throw new Error('Dependency audit exit status disagrees with its findings');
  }
  return { audit, findings };
}

module.exports = async ({ github, context, core }) => {
  const resolved = readAudit('audit-results.json', process.env.AUDIT_EXIT_STATUS);
  const direct = readAudit('audit-direct-results.json', process.env.AUDIT_DIRECT_EXIT_STATUS);
  const normalize = name => name.toLowerCase().replace(/[-_.]+/g, '-');
  for (const image of ['ee-base', 'ee-builder', 'dev-tools']) {
    const requirements = fs.readFileSync(`images/${image}/requirements.txt`, 'utf8');
    for (const line of requirements.split('\n').map(line => line.trim())) {
      if (!line || line.startsWith('#')) continue;
      const pin = /^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$/.exec(line);
      if (!pin) throw new Error('Dependency reporting requires exact auditable requirement pins');
      if (!direct.audit.dependencies.some(dependency =>
        normalize(dependency.name) === normalize(pin[1]) && dependency.version === pin[2])) {
        throw new Error(`Direct audit omitted required pin ${pin[1]}==${pin[2]}`);
      }
    }
  }
  const findings = [...new Map([...resolved.findings, ...direct.findings].map(finding =>
    [JSON.stringify([normalize(finding.package), finding.version, finding.id]), finding])).values()];
  const vulnerable = findings.length > 0;
  core.setOutput('vulnerabilities', String(vulnerable));
  if (context.ref !== 'refs/heads/main') return;
  const repo = { owner: context.repo.owner, repo: context.repo.repo };
  const runUrl = `${context.serverUrl}/${repo.owner}/${repo.repo}/actions/runs/${context.runId}`;
  const scope = 'ee-base, ee-builder and dev-tools Python requirements with ee-base constraints';
  const issues = (await github.paginate(github.rest.issues.listForRepo, {
    ...repo, state: 'open', labels: 'security,dependencies', per_page: 100
  })).filter(issue => !issue.pull_request && issue.title === title)
    .sort((a, b) => b.number - a.number);

  if (!vulnerable) {
    for (const issue of issues) {
      await github.rest.issues.createComment({
        ...repo, issue_number: issue.number,
        body: `The current audit of ${scope} found no known vulnerabilities. ` +
          `Closing this historical dependency report; this does not certify other ` +
          `images or application dependencies. Evidence: [workflow run](${runUrl}), ` +
          `dependency-audit artifact (resolved and direct-pin reports), commit \`${context.sha}\`.`
      });
      await github.rest.issues.update({
        ...repo, issue_number: issue.number, state: 'closed', state_reason: 'completed'
      });
    }
    return;
  }

  const body = `## 🔒 Security Vulnerabilities Detected\n\n` +
    `The current audit of ${scope} found vulnerable dependencies.\n\n` +
    `\`\`\`json\n${JSON.stringify(findings, null, 2)}\n\`\`\`\n\n` +
    `Evidence: [workflow run](${runUrl}), dependency-audit artifact, ` +
    `commit \`${context.sha}\`. Update affected packages; the workflow remains failing.`;
  const params = { ...repo, title, body, labels: ['security', 'dependencies'] };
  const canonical = issues[0];
  let number;
  if (canonical) {
    number = canonical.number;
    await github.rest.issues.update({ ...params, issue_number: number });
  } else {
    const created = await github.rest.issues.create(params);
    number = created.data.number;
  }
  for (const duplicate of issues.slice(1)) {
    await github.rest.issues.createComment({
      ...repo, issue_number: duplicate.number,
      body: `Consolidated into #${number}, which tracks the current dependency audit. ` +
        `This duplicate closure is not a claim that its vulnerabilities were fixed.`
    });
    await github.rest.issues.update({
      ...repo, issue_number: duplicate.number, state: 'closed', state_reason: 'not_planned'
    });
  }
};
