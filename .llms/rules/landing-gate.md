---
oncalls: ['aps_ads_trunk']
apply_to_regex: '(hpc|torchrec|caffe2|testslide|sigrid|generative_recommenders)/.*\.(py|bzl|cpp|h)$'
apply_to_content: 'import |def |class |load\(|python_version'
apply_to_clients: ['code_review']
---

# Landing Gate

This rule flags diffs where the author acknowledges the change will break downstream consumers but intends to land anyway, or where the test plan indicates incomplete testing on shared infrastructure changes.

## MANDATORY PROCEDURE — Execute both checks on every diff this rule loads for.

### Check 1: Acknowledged breakage in test plan or summary

Read the diff's **test plan** and **summary/description**. Search for ANY of these phrases (case-insensitive):
- "expected to break"
- "will fix forward"
- "landing with failures"
- "expected to fail"
- "will break some CIs"
- "known to break"
- "will be fixed afterwards"
- "will land with test failures"
- "will land with failures"

**If ANY phrase is found → IMMEDIATELY report a codeIssue with severity "warning".**

Do NOT skip because:
- "The breakage is intentional" — intentional breakage still causes SEVs for downstream teams
- "Only some CIs will break" — partial breakage blocks trunk health for all consumers
- "The author has a plan to fix it" — fix-forward is not an acceptable strategy for shared infrastructure

Report format:
```
🚫 [MVAI Trunk Health] Acknowledged breakage detected
This diff's test plan states: "<exact quoted text>"
Landing diffs with known breakage requires explicit sign-off from
affected downstream oncalls before proceeding.
This pattern caused S622078. Please coordinate with aps_ads_trunk before landing.
```

### Check 2: Incomplete test plan on shared code

Read the diff's **test plan**. Search for these patterns:
- "signals should be fine" (no evidence of actual testing)
- "need to run" followed by "later" or "after" (testing deferred)
- "CI" as the entire test plan or the primary justification (no specific tests cited)
- "will run" + "after" or "once" (testing planned for post-land)

This diff modifies shared infrastructure (this rule only loads for shared dirs). If the test plan matches any pattern above, report:

```
⚠️ [MVAI Trunk Health] Incomplete test plan on shared infrastructure
This diff modifies shared code but the test plan indicates testing is
deferred or assumed: "<exact quoted text>"
Shared infrastructure changes require evidence of reverse-dependency
testing before landing. This pattern contributed to S624945 and S621784.
```

## CRITICAL: Where to look

The phrases you are looking for are in the diff's **test plan and summary** — NOT in the source code files. You MUST read the test plan using the diff details. Do not just read the changed files.

## Severity

- Acknowledged breakage phrases found: HIGH — blocking signal
- Incomplete test plan on shared code: MEDIUM — advisory signal
