"""20-30 test questions of varying difficulty (spec section 6 / Phase 9),
each with a hand-written reference SQL query used to grade the model's
generated SQL by executing both and comparing result sets — not by
eyeballing SQL text, which the spec's own wording ("manually check") would
have settled for; this is a stronger, still-defensible bar.

Data ranges as loaded (for date-aware questions):
  FACT_MARKET_PRICES: 2024-09-20 to 2026-09-18
  FACT_TRANSACTIONS:  2025-09-20 to 2026-09-19
"""

QUESTIONS = [
    # --- Market data: simple lookups ---
    {
        "id": "Q01",
        "category": "simple_lookup",
        "question": "What sector is the ticker AMZN in?",
        "reference_sql": "SELECT SECTOR FROM DIM_TICKERS WHERE TICKER = 'AMZN'",
    },
    {
        "id": "Q02",
        "category": "simple_lookup",
        "question": "What is the company name for the ticker JPM?",
        "reference_sql": "SELECT COMPANY_NAME FROM DIM_TICKERS WHERE TICKER = 'JPM'",
    },
    {
        "id": "Q03",
        "category": "simple_lookup",
        "question": "What was AAPL's closing price on 2025-01-15?",
        "reference_sql": "SELECT CLOSE FROM FACT_MARKET_PRICES WHERE TICKER = 'AAPL' AND PRICE_DATE = '2025-01-15'",
    },
    # --- Market data: aggregations ---
    {
        "id": "Q04",
        "category": "aggregation",
        "question": "What is the average closing price of MSFT across all available dates?",
        "reference_sql": "SELECT AVG(CLOSE) FROM FACT_MARKET_PRICES WHERE TICKER = 'MSFT'",
    },
    {
        "id": "Q05",
        "category": "aggregation",
        "question": "What was the highest trading volume ever recorded for NVDA?",
        "reference_sql": "SELECT MAX(VOLUME) FROM FACT_MARKET_PRICES WHERE TICKER = 'NVDA'",
    },
    {
        "id": "Q06",
        "category": "aggregation",
        "question": "What is the difference between the highest and lowest closing price for GOOGL?",
        "reference_sql": "SELECT MAX(CLOSE) - MIN(CLOSE) FROM FACT_MARKET_PRICES WHERE TICKER = 'GOOGL'",
    },
    {
        "id": "Q07",
        "category": "aggregation",
        "question": "How many trading days of price history do we have for AAPL?",
        "reference_sql": "SELECT COUNT(*) FROM FACT_MARKET_PRICES WHERE TICKER = 'AAPL'",
    },
    # --- Market data: group-by / top-N ---
    {
        "id": "Q08",
        "category": "group_by",
        "question": "Which ticker had the single highest trading volume on any one day?",
        "reference_sql": "SELECT TICKER FROM FACT_MARKET_PRICES ORDER BY VOLUME DESC LIMIT 1",
    },
    {
        "id": "Q09",
        "category": "group_by",
        "question": "How many tickers are in the Financials sector?",
        "reference_sql": "SELECT COUNT(*) FROM DIM_TICKERS WHERE SECTOR = 'Financials'",
    },
    {
        "id": "Q10",
        "category": "group_by",
        "question": "Which sector has the most tickers in it?",
        "reference_sql": "SELECT SECTOR FROM DIM_TICKERS GROUP BY SECTOR ORDER BY COUNT(*) DESC LIMIT 1",
    },
    # --- Market data: joins ---
    {
        "id": "Q11",
        "category": "join",
        "question": "What is the average closing price across all stocks in the Technology sector?",
        "reference_sql": """
            SELECT AVG(fmp.CLOSE)
            FROM FACT_MARKET_PRICES fmp
            JOIN DIM_TICKERS dt ON fmp.TICKER = dt.TICKER
            WHERE dt.SECTOR = 'Technology'
        """,
    },
    {
        "id": "Q12",
        "category": "join",
        "question": "Which ticker in the Energy sector has the highest average closing price?",
        "reference_sql": """
            SELECT fmp.TICKER
            FROM FACT_MARKET_PRICES fmp
            JOIN DIM_TICKERS dt ON fmp.TICKER = dt.TICKER
            WHERE dt.SECTOR = 'Energy'
            GROUP BY fmp.TICKER
            ORDER BY AVG(fmp.CLOSE) DESC
            LIMIT 1
        """,
    },
    {
        "id": "Q13",
        "category": "join",
        "question": "What is the average trading volume broken down by sector?",
        "reference_sql": """
            SELECT dt.SECTOR, AVG(fmp.VOLUME)
            FROM FACT_MARKET_PRICES fmp
            JOIN DIM_TICKERS dt ON fmp.TICKER = dt.TICKER
            GROUP BY dt.SECTOR
        """,
    },
    # --- Transactions: simple lookups / aggregations ---
    {
        "id": "Q14",
        "category": "aggregation",
        "question": "How many transactions are there in total?",
        "reference_sql": "SELECT COUNT(*) FROM FACT_TRANSACTIONS",
    },
    {
        "id": "Q15",
        "category": "aggregation",
        "question": "What is the total dollar amount of all transactions combined?",
        "reference_sql": "SELECT SUM(AMOUNT) FROM FACT_TRANSACTIONS",
    },
    {
        "id": "Q16",
        "category": "aggregation",
        "question": "What is the single largest transaction amount recorded?",
        "reference_sql": "SELECT MAX(AMOUNT) FROM FACT_TRANSACTIONS",
    },
    {
        "id": "Q17",
        "category": "aggregation",
        "question": "How many distinct merchant categories appear in the transaction data?",
        "reference_sql": "SELECT COUNT(DISTINCT MERCHANT_CATEGORY) FROM FACT_TRANSACTIONS",
    },
    # --- Transactions: filters ---
    {
        "id": "Q18",
        "category": "filter",
        "question": "How many transactions are flagged as anomalous?",
        "reference_sql": "SELECT COUNT(*) FROM FACT_TRANSACTIONS WHERE IS_FLAGGED = TRUE",
    },
    {
        "id": "Q19",
        "category": "filter",
        "question": "What is the total amount of transactions flagged as anomalous?",
        "reference_sql": "SELECT SUM(AMOUNT) FROM FACT_TRANSACTIONS WHERE IS_FLAGGED = TRUE",
    },
    {
        "id": "Q20",
        "category": "multi_condition",
        "question": "How many transactions over $1000 are flagged as anomalous?",
        "reference_sql": "SELECT COUNT(*) FROM FACT_TRANSACTIONS WHERE AMOUNT > 1000 AND IS_FLAGGED = TRUE",
    },
    {
        "id": "Q21",
        "category": "multi_condition",
        "question": "How many groceries transactions were there with an amount under $50?",
        "reference_sql": "SELECT COUNT(*) FROM FACT_TRANSACTIONS WHERE MERCHANT_CATEGORY = 'groceries' AND AMOUNT < 50",
    },
    # --- Transactions: group-by ---
    {
        "id": "Q22",
        "category": "group_by",
        "question": "Which merchant category has the highest total transaction amount?",
        "reference_sql": """
            SELECT MERCHANT_CATEGORY
            FROM FACT_TRANSACTIONS
            GROUP BY MERCHANT_CATEGORY
            ORDER BY SUM(AMOUNT) DESC
            LIMIT 1
        """,
    },
    {
        "id": "Q23",
        "category": "group_by",
        "question": "Which account has the highest total transaction amount?",
        "reference_sql": """
            SELECT ACCOUNT_ID
            FROM FACT_TRANSACTIONS
            GROUP BY ACCOUNT_ID
            ORDER BY SUM(AMOUNT) DESC
            LIMIT 1
        """,
    },
    # --- Transactions: joins ---
    {
        "id": "Q24",
        "category": "join",
        "question": "How many accounts are in the premium customer segment?",
        "reference_sql": "SELECT COUNT(*) FROM DIM_ACCOUNTS WHERE CUSTOMER_SEGMENT = 'premium'",
    },
    {
        "id": "Q25",
        "category": "join",
        "question": "What is the average transaction amount for premium-segment accounts?",
        "reference_sql": """
            SELECT AVG(t.AMOUNT)
            FROM FACT_TRANSACTIONS t
            JOIN DIM_ACCOUNTS a ON t.ACCOUNT_ID = a.ACCOUNT_ID
            WHERE a.CUSTOMER_SEGMENT = 'premium'
        """,
    },
    {
        "id": "Q26",
        "category": "join",
        "question": "What is the average transaction amount broken down by customer segment?",
        "reference_sql": """
            SELECT a.CUSTOMER_SEGMENT, AVG(t.AMOUNT)
            FROM FACT_TRANSACTIONS t
            JOIN DIM_ACCOUNTS a ON t.ACCOUNT_ID = a.ACCOUNT_ID
            GROUP BY a.CUSTOMER_SEGMENT
        """,
    },
    {
        "id": "Q27",
        "category": "group_by",
        "question": "Which home location has the most accounts?",
        "reference_sql": """
            SELECT HOME_LOCATION
            FROM DIM_ACCOUNTS
            GROUP BY HOME_LOCATION
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """,
    },
    # --- Unanswerable given this schema ---
    {
        "id": "Q28",
        "category": "unanswerable",
        "question": "What is the current weather in Chicago?",
        "reference_sql": None,
        "expect_unanswerable": True,
    },
    {
        "id": "Q29",
        "category": "unanswerable",
        "question": "Who is the CEO of Apple?",
        "reference_sql": None,
        "expect_unanswerable": True,
    },
    {
        "id": "Q30",
        "category": "unanswerable",
        "question": "Predict what AAPL's stock price will be next week.",
        "reference_sql": None,
        "expect_unanswerable": True,
    },
]

for _q in QUESTIONS:
    _q.setdefault("expect_unanswerable", False)
