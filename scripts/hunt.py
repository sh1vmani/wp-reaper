#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Shivamani Vastrala
"""hunt.py - week-1 WordPress plugin vulnerability scanner.

Polls wordpress.org for recently updated plugins, downloads the ones inside
the [1000, 50000] active-install band, runs semgrep p/php and a custom
nopriv-AJAX nonce check, persists findings to SQLite, and prints a ranked
top-N summary of candidates worth manual review.

Read-only with respect to any live WordPress site. The only filesystem
writes are under --plugin-dir and --db.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests


API_URL = "https://api.wordpress.org/plugins/info/1.2/"
INSTALL_BAND_MIN = 1000
INSTALL_BAND_MAX = 50000
SUBSTRING_BLOCK = re.compile(r"security|antivirus|firewall", re.IGNORECASE)
SEMGREP_CONFIG = "p/php"
SEMGREP_TIMEOUT_SEC = 180
SEVERITY_SCORE = {"ERROR": 3, "WARNING": 2, "INFO": 1}

VENDORED_DIR_NAMES = {"vendor", "node_modules"}
VENDORED_LIB_CHILDREN = {"stripe", "stripe-gateway", "braintree", "paypal", "paypal-sdk"}

# Week-1 limitation: matches add_action('wp_ajax_nopriv_*', 'callback') only.
# Custom dispatchers (rcl_ajax_action, jet_ajax_register, etc) need a
# config-driven extension. Tracked for week 2.
NOPRIV_PATTERN = re.compile(
    r"""add_action\s*\(\s*['"]wp_ajax_nopriv_[\w-]+['"]\s*,\s*['"](?P<cb>\w+)['"]""",
)

SECURITY_TOKENS = re.compile(
    r"wp_verify_nonce|check_ajax_referer|current_user_can",
    re.IGNORECASE,
)

# Allowed values for plugins.triage_status:
# pending | triaged_clean | triaged_bug | submitted | rejected | archived
# hunt.py only ever sets 'pending' on insert; manual workflows mutate later.
SCHEMA = """
CREATE TABLE IF NOT EXISTS plugins (
    slug TEXT PRIMARY KEY,
    name TEXT,
    active_installs INTEGER,
    version TEXT,
    last_updated TEXT,
    downloaded_at TEXT,
    triage_status TEXT DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT,
    source TEXT,
    file_path TEXT,
    line INTEGER,
    rule_id TEXT,
    severity TEXT,
    message TEXT,
    raw_json TEXT,
    created_at TEXT
);
"""


def now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def load_blocklist(path: Path) -> set[str]:
    """Read the blocklist file. Strips inline `#` comments and blank lines."""
    if not path.exists():
        return set()
    out: set[str] = set()
    for raw in path.read_text().splitlines():
        cleaned = raw.split("#", 1)[0].strip()
        if cleaned:
            out.add(cleaned)
    return out


def is_blocked(slug: str, blocklist: set[str]) -> bool:
    """Return True if slug is in the blocklist or matches the substring rule."""
    return slug in blocklist or bool(SUBSTRING_BLOCK.search(slug))


def fetch_page(page: int) -> dict:
    """Fetch one page of recently-updated plugins from the wp.org API."""
    params = {
        "action": "query_plugins",
        "request[browse]": "updated",
        "request[per_page]": 100,
        "request[page]": page,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def collect_candidates(pages: int, blocklist: set[str]) -> list[dict]:
    """Walk N API pages, return plugins inside the install band that pass the blocklist."""
    seen: set[str] = set()
    out: list[dict] = []
    for p in range(1, pages + 1):
        data = fetch_page(p)
        for plugin in data.get("plugins", []):
            slug = plugin.get("slug", "")
            if slug in seen:
                continue
            installs = plugin.get("active_installs", 0)
            if INSTALL_BAND_MIN <= installs <= INSTALL_BAND_MAX and not is_blocked(slug, blocklist):
                seen.add(slug)
                out.append(plugin)
    return out


def cleanup_broken_downloads(plugin_dir: Path) -> None:
    """Delete plugin/version directories that look like failed extractions.

    A directory is considered broken if it contains zero .php files OR its
    total size is under 1 KiB. Triage status is intentionally not consulted.
    """
    if not plugin_dir.exists():
        print("Cleanup: removed 0 broken-download directories totaling 0.0 MB")
        return
    removed = 0
    bytes_freed = 0
    for slug_dir in plugin_dir.iterdir():
        if not slug_dir.is_dir():
            continue
        for ver_dir in slug_dir.iterdir():
            if not ver_dir.is_dir():
                continue
            php_count = sum(1 for _ in ver_dir.rglob("*.php"))
            total_size = sum(p.stat().st_size for p in ver_dir.rglob("*") if p.is_file())
            if php_count == 0 or total_size < 1024:
                shutil.rmtree(ver_dir)
                removed += 1
                bytes_freed += total_size
    print(
        f"Cleanup: removed {removed} broken-download directories totaling "
        f"{bytes_freed / (1024 * 1024):.1f} MB"
    )


def check_disk_pressure(plugin_dir: Path, max_gb: int) -> bool:
    """Return True if plugin_dir total content size is under max_gb."""
    if not plugin_dir.exists():
        return True
    total = 0
    for path in plugin_dir.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    used_gb = total / (1024 ** 3)
    if used_gb > max_gb:
        print(
            f"[!] Disk pressure: {used_gb:.1f} GB used in {plugin_dir}, limit {max_gb} GB",
            file=sys.stderr,
        )
        return False
    return True


def strip_vendored(target: Path, slug: str) -> None:
    """Remove vendored library directories from the freshly extracted plugin tree.

    Removes 'vendor' and 'node_modules' anywhere; removes specific payment-SDK
    directories (stripe, braintree, paypal, ...) when their parent is 'lib'.
    """
    candidates: list[Path] = []
    for path in target.rglob("*"):
        if not path.is_dir():
            continue
        name = path.name.lower()
        parent = path.parent.name.lower()
        if name in VENDORED_DIR_NAMES:
            candidates.append(path)
        elif name in VENDORED_LIB_CHILDREN and parent == "lib":
            candidates.append(path)
    candidates.sort(key=lambda p: len(p.parts))
    removed = 0
    bytes_freed = 0
    for path in candidates:
        if not path.exists():
            continue
        size = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
        shutil.rmtree(path)
        removed += 1
        bytes_freed += size
    print(
        f"Stripped vendored libs in {slug}: {removed} dirs removed, "
        f"{bytes_freed / (1024 * 1024):.1f} MB freed."
    )


def download_plugin(plugin: dict, plugin_dir: Path) -> Path:
    """Download zip and extract under <plugin_dir>/<slug>/<version>/. Idempotent."""
    slug = plugin["slug"]
    version = plugin.get("version") or "unknown"
    target = plugin_dir / slug / version
    if target.exists() and any(target.iterdir()):
        return target
    target.mkdir(parents=True, exist_ok=True)
    resp = requests.get(plugin["download_link"], timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(target)
    strip_vendored(target, slug)
    return target


def run_semgrep(target: Path) -> dict:
    """Run semgrep with the p/php rule pack against target. Returns parsed JSON.

    Surfaces any semgrep errors to stderr but does not abort the caller.
    """
    cmd = ["semgrep", f"--config={SEMGREP_CONFIG}", "--json", "."]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=SEMGREP_TIMEOUT_SEC,
        cwd=target,
    )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        snippet = (proc.stderr or proc.stdout)[:300]
        print(
            f"[!] semgrep produced unparseable output (exit {proc.returncode}): {snippet}",
            file=sys.stderr,
        )
        return {"results": []}
    for err in data.get("errors", []):
        msg = err.get("message", repr(err))[:200]
        print(f"[!] semgrep error: {msg}", file=sys.stderr)
    return data


def find_nopriv_handlers(target: Path) -> list[tuple[Path, int, str]]:
    """Return [(file, line, callback_name)] for every wp_ajax_nopriv_* registration."""
    out: list[tuple[Path, int, str]] = []
    for php in target.rglob("*.php"):
        try:
            text = php.read_text(errors="ignore")
        except OSError:
            continue
        for m in NOPRIV_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            out.append((php, line, m.group("cb")))
    return out


def handler_has_security_check(target: Path, callback: str) -> bool:
    """Look up `function callback(`, scan first 30 lines for nonce or capability tokens."""
    fn_re = re.compile(rf"function\s+{re.escape(callback)}\s*\(")
    for php in target.rglob("*.php"):
        try:
            text = php.read_text(errors="ignore")
        except OSError:
            continue
        m = fn_re.search(text)
        if not m:
            continue
        body = "\n".join(text[m.start():].splitlines()[:30])
        return bool(SECURITY_TOKENS.search(body))
    return False


def init_db(db_path: Path) -> sqlite3.Connection:
    """Open SQLite, create schema if absent. Parent dirs are created as needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def upsert_plugin(conn: sqlite3.Connection, plugin: dict) -> None:
    """Insert or update plugin metadata. Preserves triage_status across rescans."""
    conn.execute(
        "INSERT INTO plugins "
        "(slug, name, active_installs, version, last_updated, downloaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(slug) DO UPDATE SET "
        "name = excluded.name, "
        "active_installs = excluded.active_installs, "
        "version = excluded.version, "
        "last_updated = excluded.last_updated, "
        "downloaded_at = excluded.downloaded_at",
        (
            plugin["slug"],
            plugin.get("name", ""),
            plugin.get("active_installs", 0),
            plugin.get("version", ""),
            plugin.get("last_updated", ""),
            now_iso(),
        ),
    )


def insert_finding(
    conn: sqlite3.Connection,
    slug: str,
    source: str,
    file_path: str,
    line: int,
    rule_id: str,
    severity: str,
    message: str,
    raw_json: str,
) -> None:
    """Append one row to the findings table."""
    conn.execute(
        "INSERT INTO findings "
        "(slug, source, file_path, line, rule_id, severity, message, raw_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (slug, source, file_path, line, rule_id, severity, message, raw_json, now_iso()),
    )


def process_plugin(conn: sqlite3.Connection, plugin: dict, plugin_dir: Path) -> None:
    """Download, scan, and persist findings for one plugin. Idempotent on rescan."""
    slug = plugin["slug"]
    upsert_plugin(conn, plugin)
    target = download_plugin(plugin, plugin_dir)

    # Idempotent rescan: drop prior findings before re-inserting.
    conn.execute("DELETE FROM findings WHERE slug = ?", (slug,))

    semgrep_data = run_semgrep(target)
    for r in semgrep_data.get("results", []):
        insert_finding(
            conn,
            slug=slug,
            source="semgrep",
            file_path=r.get("path", ""),
            line=r.get("start", {}).get("line", 0),
            rule_id=r.get("check_id", ""),
            severity=r.get("extra", {}).get("severity", "INFO"),
            message=r.get("extra", {}).get("message", "")[:500],
            raw_json=json.dumps(r),
        )

    for php, line, cb in find_nopriv_handlers(target):
        if not handler_has_security_check(target, cb):
            insert_finding(
                conn,
                slug=slug,
                source="nonce_check",
                file_path=str(php.relative_to(target)),
                line=line,
                rule_id="missing-nonce-on-nopriv",
                severity="ERROR",
                message=f"nopriv AJAX handler '{cb}' has no nonce or capability check in first 30 lines",
                raw_json=json.dumps({"callback": cb}),
            )

    conn.commit()


def compute_score(conn: sqlite3.Connection, slug: str, active_installs: int) -> float:
    """Score = sum(semgrep_severity)*10 + missing_nonce*50 + min(installs, 10000)/1000."""
    sev_total = 0
    nonce_count = 0
    for sev, source in conn.execute(
        "SELECT severity, source FROM findings WHERE slug = ?", (slug,)
    ):
        if source == "semgrep":
            sev_total += SEVERITY_SCORE.get(sev, 0)
        elif source == "nonce_check":
            nonce_count += 1
    return sev_total * 10 + nonce_count * 50 + min(active_installs, 10000) / 1000


def print_summary(conn: sqlite3.Connection, top: int = 20) -> None:
    """Print ranked top-N plugin summary to stdout."""
    rows = conn.execute(
        "SELECT slug, name, active_installs FROM plugins"
    ).fetchall()
    scored = [
        (compute_score(conn, slug, installs), slug, name, installs)
        for slug, name, installs in rows
    ]
    scored.sort(reverse=True)
    print(f"\n{'Score':>8}  {'Slug':<35}  {'Installs':>9}  Name")
    print(f"{'-' * 8}  {'-' * 35}  {'-' * 9}  {'-' * 40}")
    for score, slug, name, installs in scored[:top]:
        print(f"{score:>8.1f}  {slug:<35}  {installs:>9}  {name[:40]}")


def parse_args() -> argparse.Namespace:
    """Parse CLI flags."""
    p = argparse.ArgumentParser(description="Week-1 WordPress plugin hunt scanner.")
    p.add_argument("--pages", type=int, default=2, help="API pages to walk (default: 2)")
    p.add_argument("--db", type=Path, default=Path("/opt/wp-scanner/sqlite/hunt.db"))
    p.add_argument("--plugin-dir", type=Path, default=Path("/opt/wp-scanner/plugins"))
    p.add_argument("--limit", type=int, default=None, help="Max plugins to scan this run")
    p.add_argument("--dry-run", action="store_true", help="Print plan, do not download or scan")
    p.add_argument("--max-disk-gb", type=int, default=50, help="Abort if plugin-dir exceeds this many GB")
    p.add_argument(
        "--blocklist-file",
        type=Path,
        default=Path(__file__).parent / "hunt-blocklist.txt",
    )
    return p.parse_args()


def main() -> int:
    """Entry point. Returns process exit code."""
    args = parse_args()
    conn = init_db(args.db)
    try:
        blocklist = load_blocklist(args.blocklist_file)
        candidates = collect_candidates(args.pages, blocklist)
        if args.limit is not None:
            candidates = candidates[: args.limit]

        if args.dry_run:
            print(f"Would scan {len(candidates)} plugin(s):")
            for plugin in candidates:
                print(
                    f"  {plugin['slug']:<35}  installs={plugin.get('active_installs', 0):>6}"
                    f"  v{plugin.get('version', '?')}"
                )
            return 0

        cleanup_broken_downloads(args.plugin_dir)
        if not check_disk_pressure(args.plugin_dir, args.max_disk_gb):
            return 1

        for plugin in candidates:
            try:
                process_plugin(conn, plugin, args.plugin_dir)
            except (requests.RequestException, zipfile.BadZipFile, subprocess.TimeoutExpired) as e:
                print(f"[!] {plugin['slug']}: {e.__class__.__name__}: {e}", file=sys.stderr)
                continue
        print_summary(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
