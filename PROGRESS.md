# wp-reaper Progress

## Status: Setting up toolchain

## Architecture
Replacing wp-bug-hunter regex scanner with:
1. Semgrep CE + custom WordPress rules (AST-based)
2. PHP_CodeSniffer + WordPressCS security sniffs
3. Psalm + wordpress-stubs taint analysis
4. Plugin Check (PCP) via WP-CLI
5. wordpress.org API poller (15-min interval)
6. SQLite tracking + submission management

## Completed
- [ ] Toolchain install
- [ ] Project structure
- [ ] Plugin poller
- [ ] Semgrep orchestrator
- [ ] WPCS layer
- [ ] Psalm taint layer
- [ ] Triage ranker
- [ ] Report generator
- [ ] Submission tracker

## Scanner Disk
/opt/wp-scanner/ -- 98GB dedicated disk mounted and ready
