---
name: safe-ftp-deploy
description: >-
  Use this skill whenever uploading, deploying, or synchronizing files to an FTP, FTPS, or SFTP server —
  especially when using FTP MCP tools or deployment scripts. Enforces a strict pre-upload security audit:
  blocks accidental upload of sensitive artifacts (.env, .git, API tokens, passwords, private keys, brain
  transcripts, config files, temporary backups), scans file contents for leaked secrets, and verifies public
  staging boundaries before any byte is transferred to a remote server.
user-invocable: true
metadata:
  domain: >-
    Securing FTP, FTPS, and SFTP deployments against data leaks, exposed credentials,
    and accidental transmission of sensitive repository artifacts.
---

# Safe FTP Deployment & Security Audit

This skill establishes a strict, automated security boundary for any deployment to an FTP, FTPS, or SFTP server. It prevents the accidental publication of private keys, environment files, agent artifacts, or sensitive repository files to the public web.

---

## 1. When to Use This Skill

Trigger this skill immediately whenever:
- You are about to call an FTP MCP tool (`upload-file`, `create-directory`, or equivalent).
- You are writing, editing, or executing an FTP/SFTP upload script.
- The user requests to "deploy", "upload to FTP", "push to website", or "sync files to webspace".
- Reviewing an FTP deployment workflow to ensure sensitive files are not exposed.

---

## 2. Core Security Invariants (Never Bypass)

Before transferring any file to an FTP server, the following rules are non-negotiable:

1. **Strict Filename Blocklist**:
   - Never upload `.env` or `.env.*` files.
   - Never upload `.git/`, `.gitignore`, `.github/`, or other VCS internals.
   - Never upload private keys (`*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`) or certificates.
   - Never upload agent logs, transcripts (`*.jsonl`), or internal planning artifacts (`implementation_plan.md`, `walkthrough.md`, `scratch/`, `tasks/`).
   - Never upload database dumps (`*.sqlite`, `*.sql`, `*.dump`) or local backups (`*.bak`, `*.old`).
   - Never upload deployment scripts that contain hardcoded plaintext credentials (e.g. `deploy.py`, `upload.js`).

2. **Content Secret Scanning**:
   - Every text file intended for public deployment (`.html`, `.css`, `.js`, `.json`) must be checked for exposed tokens (`ghp_`, API keys, private key blocks, or plaintext passwords).

3. **Public Staging Boundary**:
   - Only files explicitly intended for public consumption (HTML, CSS, JS, images, fonts, web manifests) should ever be transferred.

---

## 3. The 3-Step Pre-Upload Workflow

Always follow this exact sequence:

```
[Target Files] ──> [Step 1: Security Scan] ──> [Step 2: Allowlist Check] ──> [Step 3: Transfer]
                          │ (fails if secrets found)   │ (only public assets)
                          ▼                            ▼
                      [ABORT]                       [DEPLOY]
```

### Step 1: Run the Pre-Upload Security Scanner
Run the bundled security scanner on the folder or files you intend to upload:

```bash
python scripts/safe_ftp_scan.py /path/to/upload-folder
```

* Flags:
  * `--enforce-web-allowlist`: Rejects any file that is not a standard web asset (`.html`, `.css`, `.js`, `.webp`, `.jpg`, `.png`, `.svg`, `.ico`, `.woff2`, etc.).
  * `--quiet`: Silences informational logs; prints only critical violations.
* If the script exits with code 1, **STOP IMMEDIATELY**. Do not proceed with the upload until all flagged files are removed or cleaned.

### Step 2: Verify Public Staging
Before sending files over the FTP MCP server:
- Confirm that the destination path on the FTP server matches the web root (e.g. `/` or `/html/`).
- If deploying from a project root that also contains private files, stage only the public assets into a separate clean build directory (e.g. `dist/` or `public/`) or upload files by explicit whitelist.

### Step 3: Perform the Transfer via FTP MCP
Once the scan passes cleanly:
1. Ensure the remote directory exists using the `create-directory` MCP tool.
2. Upload individual files using the `upload-file` MCP tool:
   - Use `encoding: "utf8"` for text files (`.html`, `.css`, `.js`, `.txt`, `.svg`).
   - Use `encoding: "base64"` for binary files (`.jpg`, `.webp`, `.png`, `.ico`, `.woff2`).

---

## 4. Bundled Resources

- **`scripts/safe_ftp_scan.py`**: Deterministic CLI scanner that detects sensitive filenames, parses text files for exposed credentials (API keys, RSA keys, passwords), and enforces allowlists.
- **`references/security_rules.md`**: Complete reference catalog of forbidden file extensions, secret regex patterns, and web security best practices.
