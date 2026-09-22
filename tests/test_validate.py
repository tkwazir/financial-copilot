from backend.app.validate import validate_sql


def test_accepts_simple_select():
    result = validate_sql("SELECT * FROM FACT_TRANSACTIONS")
    assert result.accepted
    assert "LIMIT" in result.safe_sql


def test_accepts_cte_select():
    result = validate_sql("WITH recent AS (SELECT * FROM FACT_TRANSACTIONS) SELECT * FROM recent")
    assert result.accepted


def test_preserves_existing_limit():
    result = validate_sql("SELECT * FROM FACT_TRANSACTIONS LIMIT 5")
    assert result.accepted
    assert result.safe_sql.count("LIMIT") == 1
    assert "LIMIT 5" in result.safe_sql


def test_rejects_empty_query():
    result = validate_sql("")
    assert not result.accepted


def test_rejects_insert():
    result = validate_sql("INSERT INTO FACT_TRANSACTIONS (transaction_id) VALUES ('x')")
    assert not result.accepted


def test_rejects_drop():
    result = validate_sql("DROP TABLE FACT_TRANSACTIONS")
    assert not result.accepted


def test_rejects_delete():
    result = validate_sql("DELETE FROM FACT_TRANSACTIONS WHERE amount > 0")
    assert not result.accepted


def test_rejects_multi_statement_injection():
    result = validate_sql("SELECT 1; DROP TABLE FACT_TRANSACTIONS")
    assert not result.accepted


def test_rejects_update_disguised_in_where_clause_lookalike():
    # forbidden keyword must be caught even if it's not the leading statement type
    result = validate_sql("SELECT * FROM FACT_TRANSACTIONS WHERE amount = (SELECT 1); UPDATE FACT_TRANSACTIONS SET amount = 0")
    assert not result.accepted


def test_rejects_non_select_leading_keyword():
    result = validate_sql("EXPLAIN SELECT * FROM FACT_TRANSACTIONS")
    assert not result.accepted


def test_trailing_semicolon_is_fine():
    result = validate_sql("SELECT * FROM FACT_TRANSACTIONS;")
    assert result.accepted
