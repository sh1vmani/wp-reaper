# Reference: prjblk/wordpress-audit-automation

## Summary
External reference implementation of bulk-scan WordPress plugin auditing.
Captured here because it informed wp-reaper's bulk-download approach and
Semgrep usage, but the project does not depend on the upstream code.

## Upstream
- Repo: https://github.com/prjblk/wordpress-audit-automation
- Write-up: https://projectblack.io/blog/cve-hunting-at-scale/
- Snapshot taken: 2026-05-10
- HEAD commit at snapshot: f8e9587e5216155dd231189b253b98ea309a588f (2024-08-27, "Update README.md")
- Stack: Python, MySQL, Semgrep
- Stars at snapshot: 90

## Techniques borrowed
**Bulk plugin download from the wordpress.org plugin API.** The upstream
tool pages through the full plugin directory using
`https://api.wordpress.org/plugins/info/1.2/?action=query_plugins` with
`per_page=10`, discovering the page count from `info.pages` in the first
response and then walking pages 1 through `total_pages`. Freshness
filtering is applied client-side inside the download loop: a plugin is
skipped if `last_updated`'s year is less than `datetime.now().year - 2`,
so the cut is year-granularity rather than a true 2-year window. wp-reaper
reuses the same `query_plugins` API and zip-then-extract shape, but scopes
the candidate set to the 1,000-50,000 active-install band (excluding the
top 100) and drives it from a 15-minute poller rather than walking the
entire directory in one pass.

**Sequential Semgrep p/php scan as the baseline rule pack.** Upstream
invokes Semgrep with the registry pack `p/php` and stores findings keyed by
check_id and plugin slug for later SQL triage. wp-reaper takes the same
baseline: `p/php` is the floor, on top of which we layer custom WordPress
rules, PHPCS+WPCS sniffs, and Psalm taint analysis. Triage in wp-reaper is
a Python ranker over SQLite rather than ad-hoc SQL queries, because we
combine Semgrep results with PCP findings, install counts, and update
freshness signals.

## Why we do not vendor or depend on the code
The upstream repo has no LICENSE file. The GitHub license API returns 404
and the `licenseInfo` field is null, so default copyright applies and all
rights are reserved by the author. A git submodule would only store a
pointer to upstream commits and is technically separate from
redistribution, but importing or copying source from this repo into
wp-reaper has no legal cover. The borrowed techniques (download loop,
Semgrep invocation) are small and reproducible from the published blog
post plus the wordpress.org plugin API directly, so the cost of
independence is low.
