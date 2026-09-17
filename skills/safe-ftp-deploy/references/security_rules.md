# FTP Deployment Security Rules & Guardrails

This document defines the security boundary and policies required for uploading files to any FTP, FTPS, or SFTP server.

---

## 1. Threat Model & Risk Categories

Uploading files to a public web server via FTP carries specific security risks:
1. **Accidental Exposure of Secrets**: Committing or uploading `.env` files, API keys, or private keys turns private credentials into publicly accessible files on the web.
2. **Version Control Leakage**: Uploading `.git` directories allows anyone to download the entire Git repository, commit history, and hidden branches using tools like `git-dumper`.
3. **Internal Agent / LLM Artifacts**: Uploading `implementation_plan.md`, `walkthrough.md`, transcripts, or scratch files exposes system instructions, private thought processes, and internal directory layouts.
4. **Backup & Database Exposure**: Uploading `.bak`, `.sql`, `.sqlite`, or `.dump` files risks exposing customer data or application logic.

---

## 2. Blocklist Classifications

The following files and directories must **NEVER** be uploaded to an FTP web server:

| Category | Patterns / Filenames | Risk |
| :--- | :--- | :--- |
| **Credentials & Env** | `.env`, `.env.*`, `secrets.json`, `credentials.json`, `mcp_config.json` | Direct credential theft |
| **Keys & Certs** | `*.pem`, `*.key`, `*.pfx`, `*.p12`, `id_rsa*`, `id_ed25519*` | Server compromise, private key leak |
| **VCS Metadata** | `.git`, `.gitignore`, `.github/`, `.gitlab-ci.yml`, `.svn/` | Source code & history extraction |
| **Agent / Brain Files** | `.gemini/`, `.agent/`, `tasks/`, `scratch/`, `implementation_plan.md`, `walkthrough.md`, `*.jsonl`, `*.log` | Internal agent state leak |
| **Databases & Dumps** | `*.sqlite`, `*.db`, `*.sql`, `*.dump`, `*.tar`, `*.zip` | Database / data dump exposure |
| **Build & Dependencies** | `node_modules/`, `venv/`, `__pycache__/`, `package-lock.json` | Code bloat, vulnerability disclosure |
| **Deployment Scripts** | `deploy.py`, `push-via-mcp.js`, `*.bat` with raw passwords | Plaintext FTP credentials exposure |

---

## 3. The Safe Staging Protocol (3 Steps)

Before invoking any FTP upload tool (`upload-file`, `upload_directory`, etc.):

### Step 1: Pre-Upload Scan
Run the automated security scanner:
```bash
python scripts/safe_ftp_scan.py /path/to/public/files
```
The scanner:
- Recursively checks all filenames against the blocklist.
- Reads text files to detect regex patterns for API keys (`ghp_`, `AKIA`, `sk-`), RSA private keys, and plaintext passwords.
- Exits with non-zero code if any security policy is violated.

### Step 2: Public Allowlist Verification
Ensure only standard web assets are staged for upload:
* **HTML/Markup**: `.html`, `.htm`
* **Styling**: `.css`
* **Scripts**: `.js`, `.mjs`, `.map`
* **Images**: `.webp`, `.jpg`, `.jpeg`, `.png`, `.svg`, `.ico`, `.gif`, `.avif`
* **Fonts**: `.woff`, `.woff2`, `.ttf`, `.eot`
* **Data / Metadata**: `.webmanifest`, `.xml`, `.txt`

### Step 3: Destination Isolation
* Ensure uploads only target the intended web root (e.g. `/` or `/public_html/` or `/htdocs/`).
* Never upload parent directories or the repository root directly if it contains non-public files.
