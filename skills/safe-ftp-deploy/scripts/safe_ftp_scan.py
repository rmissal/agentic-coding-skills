#!/usr/bin/env python3
"""
safe_ftp_scan.py - Pre-upload Security Audit Scanner for FTP/FTPS/SFTP Deployments

Scans files or directories before they are transmitted to an FTP server:
1. Blocks forbidden sensitive filenames (.env, .git, keys, logs, credentials, etc.)
2. Scans text content for exposed credentials (API keys, private keys, passwords)
3. Enforces public staging boundary rules

Exit code:
  0 = All clear (safe to deploy)
  1 = Security violation detected (deployment must be aborted)
"""

import os
import sys
import re
import argparse
from pathlib import Path

# ==============================================================================
# FORBIDDEN FILENAME PATTERNS (Case-Insensitive)
# ==============================================================================
FORBIDDEN_EXACT_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".env.staging",
    ".gitignore", ".gitattributes", ".gitmodules",
    "mcp_config.json", "config.json", "secrets.json", "credentials.json",
    "id_rsa", "id_ed25519", "known_hosts",
    "implementation_plan.md", "walkthrough.md",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    ".ds_store", "thumbs.db"
}

FORBIDDEN_DIRECTORY_NAMES = {
    ".git", ".github", ".gitlab", ".svn", ".hg",
    "node_modules", "venv", ".venv", "__pycache__",
    ".gemini", ".agent", ".agents", "_agent", "_agents",
    "tasks", "scratch", ".system_generated"
}

FORBIDDEN_EXTENSIONS = {
    ".pem", ".key", ".pfx", ".p12", ".cer", ".crt",
    ".sqlite", ".sqlite3", ".db", ".sql", ".dump",
    ".bak", ".backup", ".old", ".orig", ".swp",
    ".log", ".jsonl"
}

# ==============================================================================
# CONTENT REGEX SCAN PATTERNS
# ==============================================================================
SECRET_PATTERNS = [
    (r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", "Private cryptographic key block"),
    (r"ghp_[a-zA-Z0-9_]{36,}", "GitHub Personal Access Token"),
    (r"github_pat_[a-zA-Z0-9_]{40,}", "GitHub Fine-Grained Personal Access Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", "API / Secret Key assignment"),
    (r"(?:FTP_PASSWORD|ftp_password|password|passwd)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]", "Plaintext password assignment"),
    (r"xox[baprs]-[0-9a-zA-Z]{10,}", "Slack Token"),
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI API Key")
]

# Safe public web file extensions
SAFE_WEB_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".mjs", ".map",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".ico", ".avif",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".xml", ".txt", ".json", ".webmanifest"
}

def is_text_file(filepath):
    """Determine if a file is plain text based on extension and null bytes."""
    text_exts = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".xml", ".txt", ".svg", ".webmanifest", ".md"}
    if filepath.suffix.lower() in text_exts:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            return b"\0" not in chunk
    except Exception:
        return False

def check_filename(filepath, base_dir=None):
    """Check if a file path violates any naming security rules."""
    violations = []
    path_obj = Path(filepath)
    name_lower = path_obj.name.lower()

    # 1. Check forbidden directory components
    for part in path_obj.parts:
        if part.lower() in FORBIDDEN_DIRECTORY_NAMES:
            violations.append(f"Forbidden directory component: '{part}' in path '{filepath}'")

    # 2. Check exact forbidden filenames
    if name_lower in FORBIDDEN_EXACT_NAMES or name_lower.startswith(".env"):
        violations.append(f"Sensitive configuration file: '{name_lower}'")

    # 3. Check forbidden extensions
    if path_obj.suffix.lower() in FORBIDDEN_EXTENSIONS:
        violations.append(f"Forbidden sensitive extension '{path_obj.suffix}': '{name_lower}'")

    # 4. Check for deployment scripts containing credentials
    if name_lower in {"deploy.py", "push-via-mcp.js", "ftp-deploy.js", "upload.py"}:
        violations.append(f"Deployment script containing potential credentials: '{name_lower}'")

    return violations

def check_file_content(filepath):
    """Check if the text content of a file contains exposed secrets."""
    violations = []
    if not is_text_file(filepath):
        return violations

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                for pattern, desc in SECRET_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        snippet = line.strip()
                        if len(snippet) > 80:
                            snippet = snippet[:77] + "..."
                        violations.append(
                            f"{filepath}:{line_no} — Detected {desc}: '{snippet}'"
                        )
    except Exception as e:
        violations.append(f"{filepath} — Could not read file content for scanning: {e}")

    return violations

def scan_path(target_path, check_allowlist=False):
    """Scan a file or directory tree for security violations."""
    target = Path(target_path).resolve()
    if not target.exists():
        print(f"[!] Path does not exist: {target}", file=sys.stderr)
        return False, []

    files_to_scan = []
    if target.is_file():
        files_to_scan.append(target)
    else:
        for root, dirs, files in os.walk(target):
            # Prune forbidden directories early
            dirs[:] = [d for d in dirs if d.lower() not in FORBIDDEN_DIRECTORY_NAMES]
            for file in files:
                files_to_scan.append(Path(root) / file)

    all_violations = []

    for f in files_to_scan:
        rel = f.relative_to(target.parent if target.is_file() else target)
        
        # 1. Filename checks
        name_issues = check_filename(f)
        for issue in name_issues:
            all_violations.append(f"[FILENAME VIOLATION] {rel} => {issue}")

        # 2. Allowlist checks (if enabled)
        if check_allowlist and f.suffix.lower() not in SAFE_WEB_EXTENSIONS:
            all_violations.append(
                f"[ALLOWLIST VIOLATION] {rel} => Non-standard public web asset extension: '{f.suffix}'"
            )

        # 3. Content scanning
        content_issues = check_file_content(f)
        for issue in content_issues:
            all_violations.append(f"[SECRET VIOLATION] {issue}")

    is_clean = len(all_violations) == 0
    return is_clean, all_violations, len(files_to_scan)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Pre-upload Security Scanner for FTP Deployments"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory or file to scan (default: current directory)"
    )
    parser.add_argument(
        "--enforce-web-allowlist",
        action="store_true",
        help="Flag any file whose extension is not in the safe public web asset allowlist"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors if violations are found"
    )

    args = parser.parse_args()

    if not args.quiet:
        print("=" * 65)
        print("SAFE FTP PRE-UPLOAD SECURITY SCANNER")
        print(f"Target: {os.path.abspath(args.path)}")
        print("=" * 65)

    is_clean, violations, file_count = scan_path(args.path, check_allowlist=args.enforce_web_allowlist)

    if not args.quiet:
        print(f"[*] Scanned {file_count} file(s).")

    if not is_clean:
        print("\n[!] CRITICAL SECURITY VIOLATIONS DETECTED:", file=sys.stderr)
        for v in violations:
            print(f"  [X] {v}", file=sys.stderr)
        print("\n[X] DEPLOYMENT REJECTED: Sensitive artifacts or credentials detected!", file=sys.stderr)
        print("    Remove sensitive files or strip secrets before attempting FTP upload.", file=sys.stderr)
        sys.exit(1)
    else:
        if not args.quiet:
            print("\n[OK] PASSED: No sensitive files or credentials detected.")
            print("[OK] Safe to proceed with FTP/FTPS/SFTP deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()
