# Observability & Telemetry (operator-opt-in)

**Status:** enabled at bootstrap (`telemetry_export_enabled: true`). Off by default; you turned it on.

This project exports **Claude Code's native OpenTelemetry signal** to a backend **you own**. The
Bootstrap Protocol opens no network sink of its own and transmits nothing to anyone. Everything below
is standard Claude Code configuration — we compose it, we do not wrap it.

Claude Code telemetry is opt-in and, by design, is sent only to the OTLP endpoint you configure —
never to Anthropic, and never to the Bootstrap maintainers. (This describes the OpenTelemetry export.
Anthropic's separate operational telemetry is a different channel, governed by Claude Code's Data
usage settings, not by anything here.) If you later choose to share findings to
help improve the protocol, that is a deliberate export you perform from your own backend, not an
automatic channel.

## Enable

Set these in your shell profile, or in `.claude/settings.local.json` (gitignored), **before**
launching `claude`. Variables exported after launch have no effect. Do **not** put backend auth
headers or tokens (`OTEL_EXPORTER_OTLP_HEADERS`) in `.claude/settings.json` or any other committed
file — that file is committed and security-critical-tier, and nothing in the pipeline scans it for a
pasted secret. (Org-wide managed settings are a separate, MDM-distributed system file, not the
project `.claude/settings.json`.)

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317   # your collector

# Slice mechanism health by archetype and protocol version in your own backend.
# <protocol_version> and <archetype> are stamped by the wizard at emission time
# from .bootstrap-state.json (bootstrap_protocol_version) and the resolved config:
export OTEL_RESOURCE_ATTRIBUTES="bootstrap.protocol_version=<protocol_version>,bootstrap.archetype=<archetype>"
```

To confirm it works locally before wiring a backend, set `OTEL_METRICS_EXPORTER=console` and
`OTEL_LOGS_EXPORTER=console` and watch the events print.

## Redaction posture — do not widen without cause

This project's default is the **redaction-clean** signal: prompts, tool arguments, file contents, and
raw API bodies are **not** exported. That is deliberate. The mechanism-health questions below are all
answerable from the redacted events. Do **not** set `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`,
`OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_ASSISTANT_RESPONSES`, or `OTEL_LOG_RAW_API_BODIES` unless you have
a specific reason and you have confirmed your backend filters sensitive fields. Note one gotcha:
`OTEL_LOG_ASSISTANT_RESPONSES` falls back to `OTEL_LOG_USER_PROMPTS` when unset, so if you turn prompt
logging on, set `OTEL_LOG_ASSISTANT_RESPONSES=0` to keep responses redacted. The trajectory logs (`.claude/logs/trajectory-*.jsonl`) remain the local,
gitignored raw record for "why did it do that at 3am?" — they are not part of this export. Note their
retention is the operator-completed loop's responsibility (the 7-day state policy covers
`.claude/sessions/`, not `.claude/logs/`), so confirm the real retention window before citing one in a
privacy review.

Identity rides every export even at the redaction-clean default: when you authenticate via OAuth,
`user.email` is attached to metrics and events, and `user.account_uuid` / `user.account_id` are on by
default. For a backend you own this is usually fine; if it is not, filter those fields at the backend
or set `OTEL_METRICS_INCLUDE_ACCOUNT_UUID=false`.

## What to watch, and which Bootstrap mechanism it answers

| Question about our mechanisms | Event / metric | Key attributes |
| --- | --- | --- |
| Are the gates (secrets/deps/drift hooks) firing, and where from? | `claude_code.tool_decision`, `claude_code.hook_execution_complete` | `decision`, `source`, `num_blocking`, `num_non_blocking_error` |
| Do the drift thresholds match real saturation? (this project's configured values are in `.claude/steering/assumption-ledger.md`) | `claude_code.compaction` | `trigger`, `pre_tokens`, `post_tokens` |
| How often do unattended loops hit infra failure / usage-limit halts? | `claude_code.api_error`, `claude_code.api_retries_exhausted` | `attempt`, `status_code`, `total_attempts` |
| How often does autonomy escalate or get gated? | `claude_code.permission_mode_changed` | `from_mode`, `to_mode` (always present); `trigger` (`auto_gate_denied`, `auto_opt_in`) — absent when the transition originates from the SDK/bridge, so verify it appears under `claude -p` at implementation |
| Is the subagent token multiplier assumption still valid? | `claude_code.token.usage` | `agent.name`, `query_source` (`main`/`subagent`/`auxiliary`) |
| Are we tripping model refusals in autonomous runs? | `claude_code.api_refusal` | `has_category` |

The token-usage-by-subagent row feeds the **Assumption Ledger** directly: it is the evidence source
for re-validating the subagent token-multiplier assumption on any pinned-model change.

## What this is not

- **Not a phone-home.** The protocol ships no maintainer endpoint. Rejected on category-mismatch
  (fleet metrics, GAR-04), wire-surface/exfiltration threat, and complexity budget.
- **Not a substitute for the audit record.** The committed `loop-final-*.md` / `run-summary-*.md`
  artifacts remain the operator-facing review surface. OTel is the trend/aggregate layer over them.
- **Not required.** Disable any time by unsetting `CLAUDE_CODE_ENABLE_TELEMETRY`; nothing else changes.
