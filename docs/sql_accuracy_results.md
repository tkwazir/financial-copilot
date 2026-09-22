# SQL Accuracy Evaluation

Generated: 2026-09-22T05:02:41.465607+00:00

Model: Claude Haiku 4.5 (`backend/app/llm.py`), schema-aware prompt (`backend/app/schema_context.py`).

Grading: each generated query is executed against Snowflake and its result set compared to a hand-written reference query (see backend/eval/questions.py) — not eyeballed as SQL text.


## Overall: 29/30 correct (96.7%)


## By Category

| Category | Correct | Total | Accuracy |
|---|---|---|---|
| aggregation | 8 | 8 | 100.0% |
| filter | 2 | 2 | 100.0% |
| group_by | 6 | 6 | 100.0% |
| join | 5 | 6 | 83.3% |
| multi_condition | 2 | 2 | 100.0% |
| simple_lookup | 3 | 3 | 100.0% |
| unanswerable | 3 | 3 | 100.0% |

## Failures

- **[Q25] What is the average transaction amount for premium-segment accounts?** — result sets differ
  ```sql
  SELECT AVG(AVG_TRANSACTION_AMOUNT) AS average_transaction_amount
FROM DIM_ACCOUNTS
WHERE CUSTOMER_SEGMENT = 'premium'
  ```
  Investigated: not a SQL-generation error, a genuine schema ambiguity. DIM_ACCOUNTS has a column literally named AVG_TRANSACTION_AMOUNT (each account's historical baseline used by the data generator), which the question's phrasing ('average transaction amount for premium accounts') plausibly matches. The model averaged that column directly ($18.39); the reference query instead computes the average of actual observed amounts in FACT_TRANSACTIONS joined to premium accounts ($20.14) — both are defensible readings of an ambiguous question, not a wrong query.
