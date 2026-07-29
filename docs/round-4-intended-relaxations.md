# Round-4 intended relaxations

**Written 2026-07-29, before any behaviour change, at HEAD `b1782ec`.**

The round-4 definition of done is:

> The sweep reports zero newly-allowed shapes versus `0fba4d2` and `b1782ec`
> **except for an explicit, enumerated INTENDED-RELAXATION list that you write
> down before you start.**

This is that list. It exists up front because as originally worded the
criterion was unsatisfiable — fixing D4 necessarily newly-allows a docs-only
`git push` against both baselines, and fixing D11 necessarily newly-allows
source writes, so a blanket "zero newly-allowed" blocks its own sequencing.

**Anything newly allowed that is not on this list is a regression.** The
list is closed: it was written before the parsers were touched and is not to
be extended after the fact to accommodate a measurement. If a fix turns out
to need a relaxation that is not here, the honest move is to add it in a
separate commit that says so, not to edit this file quietly.

Scope: **greenfield**. `mode: retrofit` is out of scope for this round
(owner decision, 2026-07-29); D14 stays open and is recorded in
`docs/deferred-backlog.md`.

---

## R-1 — eval-gate: a documentation-only push (D4)

| | shell | SDK |
|---|---|---|
| `git push`, only `README.md` and `docs.md` changed | allow (already) | **deny → allow** |

The SDK's predicate is `re.search(r"prompt|\.md$", diff)`, so every markdown
file is a prompt file. The shell narrowed this to `*[Pp]rompt*|prompts/*|*/prompts/*`
in round 3 and the SDK was left behind. Bringing the SDK to the shell's
predicate newly-allows the docs-only push on that substrate.

Not a weakening: an eval gate for prompt changes should fire on prompt files.
This is the CI-blocking class of freeze-exception 24 item 5, half-fixed.
`EVL-10` in the regression corpus pins it.

## R-2 — tdd-gate: creating a source file whose test exists under a
conventional name (D11)

| | shell | SDK |
|---|---|---|
| `Write src/main/java/com/ex/Payment.java` with `src/test/java/com/ex/PaymentTest.java` present | **deny → allow** | allow (already) |
| `Write src/Order.scala` with `OrderSpec.scala` present | **deny → allow** | allow (already) |
| `Write src/foo.ts` with `foo.test.ts` present | **deny → allow** | allow (already) |

The shell's `find` globs are case-sensitive, so `PaymentTest.java`,
`OrderSpec.scala` and `Foo.test.ts` — the default conventions in the exact
ecosystems the round-3 fix cites — did not match, while the SDK lowercases and
did. This is an unsatisfiable-gate defect of the same shape as freeze-exception
24 item 4, and the direction of the fix is to stop refusing work the operator
has already done.

**Paired with a newly-BLOCKED change in the same area** (not a relaxation, and
listed here so the pair is not mistaken for one): a test under `node_modules/`
or inside `.claude/` must stop satisfying the gate. `node_modules/p/dist/test_zzz.js`
satisfying `src/zzz.py`, and `.claude/commands/spec-new.md` satisfying
`src/new.py`, are why the gate is near-vacuous on a pristine install.

## R-3 — `script` and `su` with a bare command operand (brief item 6)

| | shell | SDK |
|---|---|---|
| `script pip install evilpkg` | **deny → allow** | allow (already) |
| `su pip install evilpkg` | **deny → allow** | allow (already) |
| `script -q /dev/null pip install evilpkg` | allow (already) | allow (already) |

Neither runs its positional operand:

- `script pip install evilpkg` names a **typescript file** `pip` and passes
  `install evilpkg` as surplus arguments. `script` runs `$SHELL`, not pip.
- `su pip install evilpkg` switches to the **user** `pip`. pip never runs.

Blocking either is a false positive, and modelling their arity correctly
removes it. The forms that DO execute are `script -c 'pip install evilpkg'
/dev/null` and `su root -c 'pip install evilpkg'`, and those are exactly what
the INVOKER rule catches — so R-3 is a relaxation on the harmless spelling
bought together with a block on the one that runs.

This is the trap the brief flags: "modelling `script`'s arity *correctly*
newly-allows `script pip install evilpkg` on BOTH substrates." It is intended.
`su` is the same case and the brief's item 6 names it alongside `script`; both
are in D3's list of twelve, so **two of those twelve resolve to allow/allow
rather than deny/deny.** The regression corpus pins them at `deny` and its
`want` is corrected in the same commit, per its own rule about disagreeing
with the record (`REGRESSION-INVARIANTS-README.md` §"three ways to fool this
corpus", item 1).

## R-4 — the six advisory hooks stop exiting 2 on an empty payload (D17)

| | shell |
|---|---|
| empty stdin to `format-lint-gate`, `spec-gate-entry`, `cost-log`, `drift-detector`, `task-done-alarm`, `decision-required-alarm` | **rc=2 → rc=0** |

These six set `FAIL_CLOSED=0` and still exit 2 on an empty payload, because
`hook_fail` sits above each hook's `FAIL_CLOSED=0` line in the shared header.
On a `Stop` event `exit 2` means "do not stop"; on `spec-gate-entry`, a
`UserPromptSubmit` hook, it blocks the user's own prompt. An advisory hook that
blocks is not advisory.

`S-10` pins this. Backlog J-19 undercounts the set at four.

## R-4b — `ssh h "git commit -m '.env'"` now DENIES (D8's price)

| | shell | SDK |
|---|---|---|
| `ssh h "git commit -m '.env'"` | allow → **deny** | allow → **deny** |

Not a relaxation — a newly-BLOCKED shape — but recorded here because it is a
deliberate over-match and the corpus pins it the other way.

Fixing D8 means an invoker's quoted argument is re-PARSED rather than
whitespace-split, so the inner `'.env'` is no longer glued to its quotes. Every
token of that command line then becomes a candidate, and `.env` matches. There
is no way to have

    bash -c "cat 'secrets/prod.yaml'"    deny      (D8, a real fail-open)
    ssh h "git commit -m '.env'"         allow     (prose in a message)

at the same time while deciding invoker-ness structurally, because the two are
the same shape: an invoker, a quoted argument, a nested quote.

Backlog **J-15** already recorded this exact over-match as accepted "in the
cheap direction". The corpus set `want=allow` after measuring that it allowed
*today* — correctly observing that J-15's stated trade-off did not exist,
because D8 was silently paying for it. With D8 fixed, J-15's original judgement
becomes true again. J-15 is rewritten from executed evidence and the corpus row
is re-pointed, in the same commit, with this note as the justification.

## R-5 — never_read_paths spellings that guarded nothing now guard
something (D18) — *anti*-relaxation, recorded for symmetry

No shape is newly allowed. Recorded here because the change is large and a
reader scanning for behaviour changes should not have to discover it in a diff:
`["**/secrets/**"]`, `["./secrets/**"]`, `["secrets/"]` and `["secrets"]` each
produced a secrets-gate that guarded nothing, installing rc=0 with no warning.
They now also guard the root-anchored/subtree forms. The DEFAULT list is
byte-identical through the normalizer, so no existing install, fixture or golden
digest moves.

## R-6 — configs that used to install now fail validation (D12) —
*anti*-relaxation

No command verdict changes. A config carrying a heredoc sentinel, a newline, a
shell metacharacter in `never_read_paths`/`deps.approved`, a non-integer drift
threshold, or an unbalanced quote in `commands.*` is now REFUSED at
`resolve_config` instead of silently emitting a hook that executes it. An
operator with such a config sees an install failure naming the field where they
previously saw rc=0 and a gate that had stopped guarding.

---

## Everything else is newly-BLOCKED or unchanged

The rest of the round moves in the deny direction and needs no permission:
D1, D2, D3, D5, D6, D7, D8, D9, D15, D16, D19, D20 all close fail-opens.

## The invariants that must not move in EITHER direction

Restated from `REGRESSION-INVARIANTS-README.md` §"the nine invariants a
tokenizer redesign is most likely to undo", because the whole point of writing
a relaxation list up front is that it does not become a licence:

1. Prose in a commit message is not a path (`ALW-01..05`).
2. A bare word equal to a never-read directory stem is not a path
   (`ALW-06..08`, backlog J-14).
3. The dotenv template basenames are exempt, exactly (`ALW-20..28`).
4. A shell invoker's argument is a command line; everyone else's quoted run is
   opaque (`INV-01..11` vs `INV-20..22`).
5. A separator inside quotes does not segment; outside quotes it does
   (`QOT-07..11`, `OPS-08`, `ALW-40`).
6. A newline inside a quoted run is not a segment break (`QOT-10`).
7. A parse failure must never become an allow (`QOT-20..23`).
8. The docs-only commit and the docs-only push must succeed (`SPC-01`, `EVL-10`).
9. Flag values are not package names, and versions need a dot
   (`FLG-01..10`, `ALW-41..46`).

## Owner decisions that stay open

**A-5** (should a retrofit install fail closed during its warn-only weeks) and
**A-6** (what `spec-gate-commit`'s predicate should be) are not closed by this
round. Backlog **J-1** — `sh -c "git commit"` recorded as deliberately
unmatched — now describes neither substrate and is SURFACED for an owner call,
not retired.
