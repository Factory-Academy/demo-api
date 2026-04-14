---
layout: default
title: Setup
---

# Setup Guide

## Prerequisites

Run `/demo-setup` to verify all integrations:

```
Demo Prep Setup Status
══════════════════════════════════════════════════
  GitHub (Factory-Academy)   ......  OK
  GitHub App (Droid Review)  ......  OK
  Linear (SE Demo team)      ......  OK
  Git push access            ......  OK
  ~/demo-kits/               ......  OK
  Salesforce                 ......  OK / SKIP
  Apollo                     ......  SKIP
  Gong                       ......  SKIP (v2)
══════════════════════════════════════════════════
```

## Required

1. **GitHub CLI**: `gh auth login` with access to Factory-Academy org
2. **Linear**: `linear___list_teams` must find "SE Demo" team
3. **Git SSH**: `ssh -T git@github.com` must authenticate

## Optional (enhance research)

4. **Salesforce**: `sf org display` for contact lookup
5. **Apollo**: Contact enrichment (if integrated)

## Troubleshooting

- **No org access**: Ask an admin to add you to Factory-Academy
- **SSH fails**: Run `ssh-keygen` and add key to GitHub
- **Linear team missing**: Skill creates "SE Demo" team automatically
