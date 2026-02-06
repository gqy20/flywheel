---
name: flywheel-scan-issues
description: Scan repository source files and create high-value GitHub issues with bounded volume and deduplication.
allowed-tools: Read,Grep,Glob,LS,Bash(rg:*),Bash(find:*),Bash(gh:*),Bash(git:*)
---

# Flywheel Scan Issues

## Goal

Find meaningful engineering issues from source code and create a bounded number of actionable issues.

## Workflow

1. Read `.github/FLYWHEEL.md` and `.github/workflows/scan.yml`.
2. Scan only the target directory and prioritize likely defect signals:
   - unsafe patterns
   - missing error handling
   - brittle logic
   - obvious test gaps
3. Read open issues first and skip duplicates by title/intent.
4. Generate a stable dedup fingerprint per issue and include it in issue body:
   - Format: `[fingerprint:<value>]`
   - Value should be derived from file path + issue type + normalized symptom key.
5. Create at most `MAX_ISSUES` issues for this run.
6. Apply one priority label (`p0`/`p1`/`p2`/`p3`) and one type label when available.
7. Keep issue body concise and reproducible (location, risk, expected outcome).

## Safety Rules

- Never create low-signal spam issues.
- Never exceed `MAX_ISSUES`.
- Never modify repository code in scan mode.

## Output Checklist

- Scanned paths
- Created issue numbers
- Deduplication summary
