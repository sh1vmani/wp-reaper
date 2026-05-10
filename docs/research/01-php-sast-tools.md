# Open-Source PHP/WordPress SAST Tools Comparison

## Summary
Comprehensive analysis of free PHP static analysis tools for WordPress vulnerability detection. This research drove the wp-reaper architecture decision to use Semgrep + Psalm + WPCS instead of regex.

## Key Findings
- AST-based taint analysis is fundamentally different from regex matching, not just incrementally better
- Free toolchain that replicates ~80% of paid SAST methodology: Psalm + Progpilot + Phan-SecurityCheck + Semgrep + PHPCS+WPCS
- Best foundation library: nikic/php-parser (BSD-3, 17,400+ stars)
- WordPress-specific knowledge lives in WordPress-Coding-Standards security sniffs

## Tools Compared
1. Semgrep CE (LGPL-2.1) - free intra-procedural taint, paid for inter-procedural
2. Psalm (MIT) - interprocedural taint analysis, supports SARIF
3. PHPStan - no taint engine, type checker only
4. RIPS open source 0.5 - abandoned 2013, replaced by Progpilot
5. Progpilot (MIT) - AST→CFG/SSA via php-cfg, full taint engine
6. Phan + mediawiki/phan-taint-check-plugin - taint categories: html, sql, shell, serialize, code, path, regex
7. WordPress-Coding-Standards - NonceVerificationSniff, ValidatedSanitizedInput, EscapeOutput, PreparedSQL
8. pheromone/phpcs-security-audit - PHPCS sniffs by Jonathan Marcil
9. WPScan - black-box HTTP scanner, vulnerability database lookup

## What Regex Cannot Catch (proven by analysis)
- CSRF with nonce check in parent function
- Privilege escalation with capability check in caller
- $wpdb->prepare misuse
- Second-order SQLi through wp_options
- Object injection via WordPress AJAX unserialize
- XSS through WordPress output functions

## Vulnerability Intelligence Sources (2026)
| Source | Cost | Auth | Rate limit |
|--------|------|------|------------|
| Wordfence Intelligence v3 | Free, commercial OK | Free API key required as of 3/9/2026 | 1 req / 30 min default |
| WPScan API free | Free non-commercial | Token | 25 req / 24h |
| Patchstack TI Standard | Closed to new customers | - | - |
| Patchstack public DB | Free read | None | - |
| NIST NVD | Public domain | Optional key | 50 req / 30s |
| Wordfence webhooks | Free | API key | Push notifications |

## Implemented in wp-reaper
The recommendations from this research are now baked into:
- docker/tools/Dockerfile (PHPCS phar + Psalm phar + WPCS git clone + wordpress-stubs)
- install.sh Step 11 (Semgrep via Docker)
- Wrapper scripts at ~/.local/bin/{phpcs,psalm,semgrep}

## Reference Architecture (4-stage roadmap)
- Stage 1 (1-2 days): Replace regex with nikic/php-parser AST visitors
- Stage 2 (3-5 days): Orchestrate Psalm + Progpilot + Semgrep, normalize to SARIF
- Stage 3 (1 week): WordPress framework awareness via Psalm plugin
- Stage 4 (ongoing): Wordfence Intelligence v3 + Patchstack public DB integration

## Caveats
- Hook indirection (do_action/apply_filters) defeats every static analyzer including paid ones
- WPScan license is non-commercial only
- Brandon Roldan's 89.2% false-positive rate on raw Semgrep PHP rules without WordPress tuning
