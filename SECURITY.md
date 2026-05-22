# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in FinSentinelAI, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainers with a detailed description of the vulnerability.
3. Include steps to reproduce the issue if possible.
4. Allow reasonable time for a fix before public disclosure.

## Security Architecture

- All data processing runs 100% locally (no external API calls).
- Passwords are hashed with bcrypt via passlib.
- Sessions use stateless JWT tokens with configurable expiry.
- ChromaDB vector store enforces user-level data isolation via session filtering.
- File uploads are sanitized to prevent path traversal attacks.
- CORS origins are configurable via environment variables.
