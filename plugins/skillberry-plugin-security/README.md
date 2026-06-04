# skillberry-plugin-security

LLM-based security evaluation plugin for Skillberry Store.

Evaluates tools, skills, and snippets for security posture, storing a `security-score:N` tag (1–10) and a paragraph explanation that names specific vulnerabilities found.

## Configuration

```bash
LLM_PROVIDER=openai.async
LLM_MODEL=gpt-4
OPENAI_API_KEY=...
```

## API

`POST /api/plugins/security/evaluate`
```json
{"uuid": "<uuid>", "content_type": "tool|skill|snippet"}
```
