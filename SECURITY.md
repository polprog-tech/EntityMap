# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | ✅ Current release |

## Reporting a Vulnerability

If you discover a security vulnerability in EntityMap, please report it responsibly.

**Do not open a public issue.**

Instead, please email **contact@polprog.pl** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge your report within **48 hours** and aim to provide a fix or mitigation within **7 days** for critical issues.

## Scope

Security concerns relevant to EntityMap include:

- **Sensitive data leakage** - entity IDs, device identifiers, or config values exposed through logs, diagnostics, or the WebSocket API
- **Unsafe template evaluation** - any code path in the template adapter that could execute attacker-controlled Jinja2
- **Panel / frontend injection** - XSS or CSP bypass in the panel HTML loader or the LitElement frontend
- **Registry / config tampering** - any write path that could mutate device, entity, or automation registries (EntityMap is read-only by design)
- **Dependency vulnerabilities** in bundled Home Assistant or frontend dependencies

## Disclosure Policy

We follow coordinated disclosure:

1. Report the issue privately via the contact above.
2. We confirm receipt and begin investigation.
3. Once a fix is released, we publicly acknowledge the reporter (with their consent).
