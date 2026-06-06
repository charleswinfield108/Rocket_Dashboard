---
name: validate-api
description: Validates one live API endpoint against docs/api_spec.md. Usage: /validate-api /api/elevators or /validate-api /api/elevators/10
user-invocable: true
---

The user has invoked `/validate-api` with an endpoint path argument: `$ARGUMENTS`

Spawn the `api-validator` subagent and pass it the endpoint path `$ARGUMENTS`. Do not perform any validation yourself — all validation logic lives in the subagent. Surface its conformance report back to the user exactly as returned, without summarising or paraphrasing.
