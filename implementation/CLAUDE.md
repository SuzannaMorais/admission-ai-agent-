# Instructions for AI assistants working on this repository

This file governs how any AI assistant (Claude or otherwise) should work on the Admission AI Agent repository. Read it, and the relevant files below, before editing anything.

## Before editing

1. Read this file in full.
2. Read whichever of these is relevant to the task:
   - [`planning.md`](planning.md) — what the product is for and who it's for.
   - [`architecture.md`](architecture.md) — how it's actually built, including what's a real feature vs. a documented gap.
   - [`implementation-plan.md`](implementation-plan.md) — what's done, what's next, in what order.
   - [`testing.md`](testing.md) — how to run the tests and what they do/don't prove.
   - [`progress.md`](progress.md) — current live status.
3. Read the actual source for the module(s) you're about to touch. Do not assume behavior from a doc — the doc could be stale. If code and doc disagree, trust the code, then fix the doc.
4. Read the root-level [`../planning.md`](../planning.md) if the task involves anything from the original 9-task build — it has the exact signatures and interfaces that later tasks depend on.

## While working

5. Follow the project's existing conventions: Python 3.12, SQLAlchemy 2.x declarative models with `Mapped[...]` type annotations, FastAPI with `Depends(get_db)` for DB access, pytest with fixtures from `tests/conftest.py`, TDD (write the failing test first, watch it fail, then implement).
6. Make the smallest safe change that satisfies the request. Don't refactor unrelated code, don't add abstractions the task doesn't need, don't touch the mocked-tool boundary unless the task is specifically about replacing a mock with a real integration.
7. Never let a high-risk action (admission approval/rejection, fee exception, seat allocation) take effect anywhere except through `admission_agent/approvals.py::resolve_approval`. If a change seems to need a shortcut around that, stop and flag it instead of adding one.
8. Never remove the confidentiality check in `query_applicant_status` or the government-ID masking in `parse_uploaded_document` without an explicit, separate instruction to do so — these are the two concrete security guarantees this codebase currently has.

## After making a change

9. Update whichever of the docs in this folder the change affects, in the same piece of work — not as a follow-up later. A behavior change with no doc update is an incomplete change.
10. Update [`progress.md`](progress.md): what you did, what tests you ran, what the result actually was, and today's date. Do not write progress notes for work you intend to do next — only for work you actually did.
11. Run the relevant tests, and the full suite before calling anything done:
    ```bash
    ./.venv/Scripts/python -m pytest -v
    ```
    If there's ever a lint/type-check/build command configured (there isn't yet — see `testing.md`), run that too.
12. **Report failed checks honestly.** If a test fails, say so, with the actual output. Do not silently skip a failing test, and do not mark a task "done" in any doc while a test it depends on is red.
13. **Never claim a test passed, code was pushed, or anything was deployed unless you actually ran/verified it in this session.** "Should work" is not "works." A claim of success must be backed by output you actually saw.

## Secrets and safety

14. Never commit, print, or embed `.env` files, API keys (including `ANTHROPIC_API_KEY`), tokens, passwords, or production credentials. Check `git status`/`git diff` before committing if you've touched anything that might contain one.
15. Never overwrite or delete a file you haven't verified is safe to lose. If something in the working tree looks unfamiliar (not something you or this task created), stop and ask rather than assuming it's disposable.

## Git / GitHub workflow

16. Before committing: run `git status` and `git diff` and review exactly what's staged. Don't `git add -A`/`git add .` blindly — add the specific files the task touched.
17. Write descriptive commit messages (what changed and why, not just "update files").
18. Push only to the branch the task specifies. Do not force-push, and do not rewrite shared history, unless explicitly instructed to.
19. If a push fails (auth, permissions, conflicts), report the exact error — never claim the push succeeded without having seen confirmation (a successful `git push` output, or the commit visible via `gh api` / `gh repo view`).
20. If the requested change is substantial, destructive, touches production data, or changes deployment configuration, stop and ask for approval before doing it — don't just proceed because the instructions technically allow it.

## What "done" means in this repository

A task is only done when: the code change exists, the test for it exists and was watched to fail then pass, the full suite was run and its real output was read, the relevant doc(s) in this folder were updated to match, and (if the task's scope includes it) the commit was pushed and its presence on GitHub was verified — not assumed.
