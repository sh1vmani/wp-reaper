# WordPress Bug Bounty Playbook 2025-2026

## Summary
Strategic research on maximizing earnings and CVE credit from WordPress plugin bug bounties.
Drives all wp-reaper targeting and submission decisions.

## Earnings Reality Check
- Wordfence: max $31,200 / $32,760 for 1337 researchers, $400k+ paid in 2024
- Patchstack Alliance: $8,800 monthly pool, top 20 places
- Realistic part-time (10-15 hr/week, eJPT level): $5,000-$25,000/year
- Stealthcopter (proven blueprint): $27,000 in H1 2024, ~300 reports, ~$90 average

## Submit-Where Decision Rule
- ≥1,000 installs + high-threat (RCE/file upload/options update/auth bypass) → Wordfence first
- 100-999 installs + CVSS ≥8.5 → Patchstack only
- Reflected XSS, CSRF, IDOR with limited impact → Patchstack
- WordPress core, Automattic plugins → HackerOne
- MainWP plugins → HackerOne (MainWP)
- NEVER submit same bug to two platforms

## Wordfence Payout Structure
Maximum: $31,200 base, $32,760 with 1337 status
High-Threat (≥25 installs): RCE, file upload, options update, auth bypass, PrivEsc to admin
Common+Dangerous (≥500 installs): Stored XSS, SQLi
Bonuses stack: +15% active exploitation, +15% chaining, +10% creative, +10% meaningful, +5% 1337

## Patchstack Alliance Distribution (monthly)
1st: $2,000 / 2nd: $1,400 / 3rd: $800 / 4th: $600 / 5th: $500
6th-10th: $400 each / 11th-15th: $200 each / 16th-19th: $100 each / 20th + 1 random: $50
Critical rule: 67% rejection rate triggers monthly ban

## Patchstack Zeroday Tiers
- 1k installs: $250 unauth / $125 auth
- 10k: $600 / $300
- 50k: $1,400 / $700
- 100k: $2,600 / $1,300
- 1M: $7,200 / $3,600
- 5M: $14,400 / $7,200
- 15M+: $33,000 / $16,500

## Target Selection Sweet Spot
- 1,000-50,000 active installs
- Categories: file managers, forms, bookings, payments, LMS, import/export
- AVOID: top 100 plugins, security plugins, WordPress core, Gutenberg

## Code Smells That Predict Bugs
- add_action('wp_ajax_nopriv_*') without check_ajax_referer or current_user_can
- Direct $wpdb->query("..." . $_POST['x']) concatenation
- move_uploaded_file with extension whitelists missing .phtml/.phar
- unserialize($_POST/*)
- include/require of user-controllable parameter
- Abandoned plugins (last update >12mo) with active installs >1k

## Most Profitable Vulnerability Patterns (2025-2026)
1. AJAX file upload with missing validation (Modern Events Calendar $3,094, Avada $2,751, AI Power $650)
2. Unsafe unserialize (object injection)
3. Missing-nonce CSRF on settings updates
4. Broken current_user_can checks
5. Path traversal in file management (MW WP Form $1,275)
6. $wpdb->prepare misuse with %s/%d type confusion
7. sanitize_text_field used where esc_attr required (Stealthcopter >$6k from this alone)

## First-Finder Advantage
- Poll wordpress.org plugin API every 15 min for browse=updated
- SVN diff between versions to identify exactly what changed
- Most patches sit in tiny diffs, ideal for targeted Semgrep
- Patch bypasses on disclosed bugs within 7 days = highest ROI

## Successful Hunters
- Stealthcopter: github.com/stealthcopter/wordpress-hacking
- Project Black: github.com/prjblk/wordpress-audit-automation (14 CVEs in 3 Sundays)
- Brandon Roldan: Semgrep join-mode CSRF detection
- Pohekar & Ali (Nullcon 2022): "Raining CVEs" Semgrep methodology

## Phased Plan
- Weeks 1-2: Replace regex with prjblk-style pipeline (DONE - we built our own)
- Weeks 3-6: First 5 paid bugs targeting 1k-10k install plugins
- Weeks 7-12: Add 15-min API poller + SVN diff + LLM triage
- Months 4-6: Build 15-25 named CVE portfolio for resume

## Daily Workflow
- Morning (30-60 min): triage scanner queue, 5-minute rule, pick top 3
- Daytime (3-5 hr): deep dive top 1-2 candidates, 90-minute drop rule
- Evening (1 hr): write up confirmed bugs, submit
- Weekly (2 hr): review rejections, tune rules, look for patch bypasses
- Target: 5-10 confirmed reports/week steady state

## Caveats
- Wordfence per-vuln base table not publicly published since March 2024 (in-page JS calculator)
- Patchstack 2026 rules effective May 1, 2026 (recent)
- WPScan license forbids commercial use
- Stealthcopter $27k is one data point, not typical
- 24-48 hour window between finding and submitting -- otherwise duplicate-rejection risk
