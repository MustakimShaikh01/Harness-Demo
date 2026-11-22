# Harness Engineering

The harness is the independent control plane around the LLM. The model understands intent and proposes actions, while Python code makes and rechecks decisions.

- **Policy** is centralized in `config/policies.yaml`.
- **Authorization** uses a trusted demo customer and rejects cross-customer access.
- **Approval** is bound to exact details and a short lifetime.
- **Idempotency** reserves and completes request IDs.
- **Observability** emits structured logs and persistent audit events.
- **Error handling** produces machine-readable error categories.
