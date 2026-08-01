# Epic J acceptance fixture

This is a deliberately small, fictional legacy-system evidence set.  It is
versioned so every developer and CI run begins with the same inputs.

| Evidence location | Consumed by | Purpose |
| --- | --- | --- |
| `evidence/motivation/` and `evidence/strategy/` | strategy-analyst | Goals, drivers, and a modernisation capability. |
| `evidence/business/` | business-analyst | A short customer-support interview transcript. |
| `evidence/code/` | code-analyzer | A tiny Customer API and its customer data structure. |
| `evidence/infra/` | infra-analyzer | One Terraform resource for the API host. |
| `evidence/integration/` | integration-mapper | The API contract and relationship evidence. |

## Deliberate edge cases

- **F1 duplicate:** `code/customer_api.py` contains both the `CustomerApi`
  application and its legacy `customer-api` service alias.  During acceptance,
  create the same-type, normalized-name candidates `Customer API` and
  `customer-api`; F1 must retain one canonical element and both evidence
  citations.  The automated J test seeds these candidates deterministically so
  the assertion does not depend on LLM wording.
- **F2/E5 invalid reference:** `integration/customer-api-invalid.yaml` names
  `app-retired-billing-service`, which is intentionally absent from the
  evidence/model.  It must be used for the first run: validation must report a
  dangling target and H1 must not commit or open a PR.  Remove that proposed
  relationship (or use `customer-api.yaml` only) for the clean PR run.

The invalid integration file is evidence for a *bad proposed relationship*;
the integration mapper is expected to reject it because the target does not
exist.  It must never become an accepted model relationship in a clean run.
