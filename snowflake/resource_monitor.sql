-- Account-wide spend cap: 350 credits (buffer under the $400 trial credit),
-- notifying at 75%/90% and suspending compute before it's exceeded.
-- FREQUENCY = NEVER since trial credit is a one-time pool, not a recurring
-- monthly allowance that should reset.

USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS FIN_COPILOT_MONITOR
  WITH
    CREDIT_QUOTA = 350
    FREQUENCY = NEVER
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
      ON 75 PERCENT DO NOTIFY
      ON 90 PERCENT DO NOTIFY
      ON 100 PERCENT DO SUSPEND
      ON 110 PERCENT DO SUSPEND_IMMEDIATE;

ALTER ACCOUNT SET RESOURCE_MONITOR = FIN_COPILOT_MONITOR;
