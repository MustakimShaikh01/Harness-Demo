# Security

## Threat model

The model, tool arguments and customer text are untrusted. Prompt text cannot grant ownership or policy exceptions.

## Controls

- Active customer identity comes from environment/application context, never tool arguments.
- Sensitive execution tools use ADK's `FunctionTool(require_confirmation=True)` confirmation step in the UI.
- Sensitive operations validate exact approval fingerprints and reject expiry, modification and replay.
- All financial decisions use deterministic code and Decimal arithmetic.
- Corrupt JSON is detected and writes use backup plus atomic replacement.
- API keys are never written to audit logs.

Run ADK Web with `adk web --no_use_local_storage .` to keep ADK's conversational state in memory. Application banking records are JSON files; do not commit `.env`, `.adk` state or live credentials.

## Demo limitations

No production identity, MFA, HSM, fraud network, PCI controls or real banking integration is represented.
