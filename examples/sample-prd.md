# Hawkbill — Webhook Delivery Service

## Problem

Teams that emit webhooks need reliable, observable delivery with retries and
dead-lettering. Today each team rebuilds this badly. Hawkbill is a backend
microservice exposing a REST API to register endpoints and enqueue webhook
deliveries, with a worker that retries with backoff.

## Primary user

Platform engineers integrating webhook fan-out into their own services.

## Success criterion

99.9% of deliveries either succeed within 5 attempts or land in the
dead-letter queue with a clear reason, observable via the API.

## Personas

- **Integrator** — registers endpoints, inspects delivery status.
- **On-call SRE** — triages dead-lettered deliveries.

## User journeys

1. Integrator registers an endpoint with a shared secret.
2. Integrator enqueues a delivery; receives a delivery id.
3. Worker attempts delivery, retries on failure with exponential backoff.
4. SRE queries failed deliveries and replays them.

## Non-goals

- No UI in v1 (API only).
- No multi-region replication in v1.

## Security & secrets

Endpoints are authenticated with per-endpoint signing secrets and an API key
for the management API. Secrets must never be logged. Credentials are read
from the environment.

## Risks

- Thundering-herd retries against a recovering endpoint.
- Secret leakage in logs.

## Dependencies

Standard web framework plus a queue. Concrete library choices are TBD by the
engineering team.

## Latency

Enqueue must return in under 50 ms (real-time path); delivery itself is async.
