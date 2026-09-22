# Backend

Placeholder. This is where the FastAPI NL-to-SQL service lands (spec phase 5):

- Schema-aware prompt construction (RAG over table/column descriptions)
- Claude API call generating SQL
- Validation/guardrail layer: `SELECT`-only enforcement, hard `LIMIT`, read-only role, query timeout, generation logging
- Snowflake Python Connector execution
- Second Claude API call turning result rows into a natural-language answer

See the main project spec and README's "Roadmap" section for full context.
