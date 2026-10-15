# Public canonical sync

Edit profile content in [TED-H-com/teddashh](https://github.com/TED-H-com/teddashh).
Edit hub data and generators in [TED-H-com/ted-h-com.github.io](https://github.com/TED-H-com/ted-h-com.github.io).
Personal repositories keep their existing profile and website URLs.

The scheduled workflow checks every five minutes. GitHub may delay or skip runs;
this is not guaranteed real-time synchronization. Public-repository schedules may
be disabled after 60 days without repository activity. Use Actions → Sync canonical
public profile / Sync and deploy canonical public hub → Run workflow for a manual check.

Each workflow reads its public canonical main branch and writes only this personal
repository with its own built-in GITHUB_TOKEN. No cross-repository write token is used.
Profile synchronization includes bilingual READMEs, assets/ and projects/.
Hub synchronization includes bilingual READMEs, LICENSE, hub.json and kit/; site/
is rebuilt for the personal host, preserving legacy redirects. Workflows, secrets,
repository settings and domain configuration are not copied. Hub deployment must
succeed before the sync state is committed, so failed deployments are retried.

The hub's render_profile.py produces profile content, but this workflow does not
publish that output into the separate canonical profile repository. After changing
hub data, review the generated profile output and commit it separately to
TED-H-com/teddashh; that repository's personal mirror then updates normally.

Do not edit managed content directly in the personal repositories. A personal edit
causes synchronization to fail safely rather than overwrite it. Reconcile that edit
with the canonical repository, then restore the personal managed files to their
last successfully synchronized version before rerunning. Do not reset the state to
hide a conflict. Normal non-force pushes also stop if another writer changes main.

The initial state was created by fetching the exact reviewed canonical commit and
comparing all allowlisted input hashes and path sets. The SHA and managed-file
hashes are recorded in sync-state.json. Tests: python3 .github/scripts/test_sync.py.
