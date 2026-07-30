"""THE command-position model. One definition, both substrates.

[round-4 D1/D2/D3/D7/D9] Before this module there were SIX hand-rolled
encodings of "where does a command begin, and what is its command word", and
FIVE distinct prefix-membership sets:

    shell:  _cs_isinv (walker)      CMD_PFX (anchor regex)
            _sg_push  (walker)      _CS_INVOKERS (dead code, already drifted)
    SDK:    _segment_candidates (walker)   _expand_invoker_args (walker)
            _CMD_PREFIXES (set)            _CMD_PFX_RE (anchor regex)

They disagreed about which words are transparent, whether a prefix may consume
an operand, whether `VAR=value` runs are skipped, and how deep an invoker's
argument is expanded. Every one of those disagreements shipped as a defect:
`su` was in `CMD_PFX` only; the ten wrapper names were in four of five sets and
absent from `_CMD_PFX_RE`, which is exactly how D3 happened - a comment reading
"Shell parity: this is CMD_PFX from the shell header, same alternation in the
same order" sat above a regex that was byte-identical to the previous commit
while its shell twin grew.

Every set below is defined ONCE and interpolated into both emitters. Adding a
wrapper here reaches all six sites; there is no second list to forget.

THREE CATEGORIES, and the third is why two sets were never enough
-----------------------------------------------------------------
PREFIXES   transparent - they do not change WHICH program runs, so the next
           token is still the command word. `nice -n 5 pip install evil` runs
           pip.
INVOKERS   their ARGUMENT is a command line, not data. `sh -c 'pip install
           evil'` runs pip; `git commit -m 'pip install evil'` does not.
DUAL       both at once, and modelling them as either alone loses a real
           execution path:
             watch  - `watch -n 1 pip install evil` runs pip (prefix), and
                      `watch -n 1 'cat secrets/prod.yaml'` joins its args and
                      runs them through `sh -c` (invoker).
             xargs  - `xargs -n1 pip install evil` runs pip with arguments
                      appended (prefix); a quoted argument is a command line.
             ssh    - `ssh box pip install evil` installs on the remote host,
                      which is still "unapproved software arrives"; `ssh box
                      "pip install evil"` is the quoted spelling of the same.

WHAT IS DELIBERATELY *NOT* HERE
-------------------------------
`su` and `script` are INVOKERS ONLY, not prefixes, and that is a behaviour
change in the allow direction recorded in docs/round-4-intended-relaxations.md
(R-3). Neither runs its positional operand:

    su pip install evil        switches to the user `pip`; pip never runs
    script pip install evil    writes a typescript to a file named `pip`

The spellings that DO execute are `su root -c 'pip install evil'` and
`script -c 'pip install evil' /dev/null`, and those are exactly what the
INVOKER rule catches. Keeping them in the prefix set bought a false positive
on the harmless spelling and nothing at all on the dangerous one.

ARITY: WHY THE TWO KINDS OF CONSUMER GET OPPOSITE TREATMENTS
------------------------------------------------------------
An earlier prescription was "model the arity, do not raise the bound"
everywhere. That is correct for the anchors and BACKWARDS for the walkers: a
reviewer implemented it and measured 16 of 27 real wrapper-flag spellings
regressing from deny to allow - `sudo -R /`, `sudo --chroot /`, `env --chdir
/tmp`, `nice --adjustment 5`, `ionice --classdata 4`, `flock --timeout 10`,
`stdbuf --output 0`, `proxychains --file c`, `doas -a pam` - mostly LONG forms
of flags whose short form was in the table. Any arity table written from memory
has that hole and a new coreutils flag reopens it silently.

  * WALKERS decide "is there an invoker at the head of this segment". They get
    an UNBOUNDED head scan, gated on having seen a prefix: once a wrapper word
    is seen, skip tokens until an invoker turns up or the segment ends. No flag
    table. Over-consumption is the safe direction here, and the bound is what
    kept re-opening: it was `< 3` in one walker and `< 4` in another, and
    `timeout -k 1 -s KILL 5 sh -c` needs five.

  * ANCHOR REGEXES decide "is `pip install` at command position". They
    currently UNDER-consume, which is the fail-open direction (D9:
    `sudo -u root pip install evil` allowed at every commit, on both
    substrates, invisible to both a differential and a parent-vs-head sweep).
    They get flags AND positionals after a wrapper word - also unbounded, for
    the same reason the walkers are.

    Unbounded consumption cannot fail open HERE, and the reason is worth
    stating because it is not obvious: regex matching answers "does there
    EXIST a parse", so a greedy prefix that swallows the command word simply
    backtracks. Verified:

        sudo -i pip install evil            MATCH  (-i takes no value; the
                                                    engine backtracks and
                                                    finds pip at the head)
        timeout -k 1 -s KILL 5 pip install  MATCH
        sudo -u root pip install evil       MATCH  (D9, allowed before)
        echo -n pip install evil            NO MATCH - `echo` is not a
                                                   wrapper, so the prefix run
                                                   never starts

    The last line is the whole safety argument: the positional allowance is
    gated on a wrapper word, so an ordinary command cannot drift into command
    position.
"""

from __future__ import annotations

# Transparent prefixes. `then|else|do|elif` are shell KEYWORDS rather than
# binaries and are kept separate because only the anchor can use them - a
# walker sees them as ordinary words at a segment head.
PREFIXES = (
    "env", "sudo", "doas", "nohup", "time", "timeout", "command", "exec",
    "builtin", "stdbuf", "setsid", "nice", "ionice", "flock", "chroot",
    "unbuffer", "proxychains",
)

# Their argument is a command line.
INVOKERS = (
    "sh", "bash", "zsh", "dash", "ksh", "ash", "busybox", "eval", "su",
    "script",
)

# Transparent AND invoking. See the module docstring.
DUAL = ("watch", "xargs", "ssh")

# Shell keywords that open a command position.
KEYWORDS = ("then", "else", "do", "elif")

# The two membership sets every consumer actually asks about.
ALL_PREFIXES = PREFIXES + DUAL          # may be skipped past at command pos
ALL_INVOKERS = INVOKERS + DUAL          # their argument is a command line


# ---- [round-4 D16/D20] remote-script execution ---------------------------- #
#
# `curl url | sh` is the same "unapproved software arrives" class the
# dependency gate exists for, with no inspectable package name. The pattern
# that guarded it was
#
#     (curl|wget)[^;&|]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?|perl|ruby)( |$)
#
# and every one of these walked through it, `allow` on both substrates at
# every commit:
#
#     curl url | /bin/sh            path-qualified shell
#     curl url | tee /tmp/x | sh    `[^;&|]*` cannot cross the first pipe
#     curl url | sudo -u root sh    `sudo\s+` takes no flags or operands
#     curl url | env sh             the whole prefix set defeats it; `sudo`
#     curl url | timeout 5 sh       was the ONLY prefix it knew
#     curl url | nohup sh
#     fetch -o - url | sh           the downloader list was curl|wget only
#     aria2c url | sh
#     http url | sh
#
# Three of those four causes are the same mistake - a hand-written subset of a
# set that already exists elsewhere in this file - so the shell word and the
# prefix run are now built from ALL_PREFIXES and INVOKERS rather than typed
# out again.
DOWNLOADERS = (
    "curl", "wget", "aria2c", "axel", "http", "https", "fetch",
    "lwp-download", "lwp-request", "wget2",
)

# Interpreters that will execute a script on stdin. A superset of the invoker
# set: `python3 -`, `perl`, `ruby` are not shell invokers but do run what they
# are piped.
INTERPRETERS = INVOKERS + ("python", "python2", "python3", "perl", "ruby",
                           "node", "php", "Rscript")

# Package-EXECUTING channels. `npx evil` fetches and runs an unapproved
# package; not installing it first is not a mitigation.
#
# [round-4 D20] `yarn create`, `npm init <pkg>`, `pnpm create`, `bun create`,
# `pipx run`, `uv tool run` and `bun x` were all missing. Every entry here
# takes a PACKAGE as its next token, which is what makes the existing
# "inspect every token after the verb" scan correct for them unchanged.
#
# DELIBERATELY ABSENT, because they would be false positives:
#   `deno run main.ts`  - ordinary local execution. Only the URL form is an
#                         arrival channel, and it is matched separately.
#   `uv run python`     - ordinary. `--with <pkg>` is the arrival channel and
#                         is matched separately.
# Blocking those two outright is the "unactionable refusal" shape this
# codebase has already shipped twice; the narrow rules cost one regex each.
RUNNER_SOLO = ("npx", "uvx", "bunx")
RUNNER_VERBS = (
    ("npm", ("dlx", "exec", "init", "create")),
    ("pnpm", ("dlx", "exec", "create")),
    ("yarn", ("dlx", "exec", "create")),
    ("bun", ("x", "create")),
    ("pipx", ("run",)),
)
# Multi-word spellings. `uv tool run evil` is `uvx evil` written out, and
# `uvx` was in the list while its long form was not.
RUNNER_PHRASES = (
    ("uv", "tool", "run"),
)


def alt(words) -> str:
    """`a|b|c` - the alternation body shared by bash `case` patterns, bash
    ERE alternations and Python regex alternations.

    Interpolated at EMISSION time rather than read from a variable at hook
    runtime, because bash does not split a `case` pattern on a `|` that
    arrived through parameter expansion: `P='a|b'; case a in $P)` does NOT
    match. Verified, and it is the reason this is a build-time constant
    instead of a shell array.
    """
    return "|".join(words)


def bash_case_alt(words, indent: str = "") -> str:
    """The same alternation, line-wrapped for a bash `case` arm.

    Bash allows a backslash-newline inside a pattern list; the emitted hooks
    stay under the line-length the rest of the file keeps to.
    """
    out, line = [], ""
    for w in words:
        piece = (w if not line else "|" + w)
        if len(line) + len(piece) > 60:
            out.append(line)
            line = w
        else:
            line += piece
    if line:
        out.append(line)
    return ("\\\n" + indent + "|").join(out)


# ---- the anchor regex, built once and spelled for both regex dialects ----- #
#
# A command-position prefix run: any number of
#   * a wrapper word followed by its flags and positionals,
#   * a brace group,
#   * a redirection,
#   * a VAR=value assignment,
#   * a shell keyword.
#
# The wrapper arm is what fixes D9 and, on the SDK side, D3. `\S`-style
# shorthands are avoided so the identical source works as a bash ERE.

def pipe_to_shell_regex(space: str = " +", nonspace: str = "[^ ]") -> str:
    r"""A downloader whose output reaches an interpreter through any number of
    pipes, with any prefix run in front of the interpreter.

    `[^;&]*` is deliberate and is the fix for `curl url | tee /tmp/x | sh`: it
    permits further PIPES while still refusing to read across a `;` or `&`,
    which really do end the command. The old `[^;&|]*` stopped at the first
    pipe, so one harmless-looking filter in the middle defeated the rule.
    """
    return (
        "(" + alt(DOWNLOADERS) + ")[^;&]*[|] *"
        + "(" + "(" + alt(ALL_PREFIXES) + ")(" + space + "-" + nonspace + "+|"
        + space + "[^- ]" + nonspace + "*)*" + space + ")*"
        + "(" + nonspace + "*/)?(" + alt(INTERPRETERS) + ")( |$)"
    )


def runners_regex(space: str = " +", nonspace: str = "[^ ]") -> str:
    """The package-EXECUTING channels, as one alternation."""
    parts = ["(" + nonspace + "*/)?(" + alt(RUNNER_SOLO) + ")"]
    for tool, verbs in RUNNER_VERBS:
        parts.append("(" + nonspace + "*/)?" + tool + space
                     + "(" + alt(verbs) + ")")
    for phrase in RUNNER_PHRASES:
        parts.append("(" + nonspace + "*/)?" + space.join(phrase))
    return "|".join(parts)


def anchor_regex(space: str = " +", nonspace: str = "[^ ]") -> str:
    """The prefix-run regex. `space`/`nonspace` are parameterised only so the
    Python side can keep its `\\s`/`\\S` spelling; the STRUCTURE - and every
    word in it - comes from this file for both."""
    wrap = alt(ALL_PREFIXES)
    kw = alt(KEYWORDS)
    return (
        "((" + wrap + ")(" + space + "-" + nonspace + "+|"
        + space + "[^- ]" + nonspace + "*)*" + space
        + "|[{]" + space
        + "|[0-9]*[<>]+ *" + nonspace + "+" + space
        + "|[A-Za-z_][A-Za-z0-9_]*=" + nonspace + "*" + space
        + "|(" + kw + ")" + space
        + ")*"
    )
