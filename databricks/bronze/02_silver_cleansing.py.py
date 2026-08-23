# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
dbutils.widgets.text("catalog", "fintech_lakehouse")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# COMMAND ----------

# MAGIC %md Import the transformation functions from the sibling module,
# MAGIC so the same code is unit-testable with pytest outside Databricks.

# COMMAND ----------

# COMMAND ----------

import sys, os

sys.path.append(os.getcwd())

from transformations import (
        dedupe, standardize_customers, standardize_accounts,
    standardize_merchants, standardize_transactions,
    apply_scd2, prepare_scd2_updates, run_dq_checks
)

from pyspark.sql import functions as F

# COMMAND ----------

# COMMAND ----------

# MAGIC %md ## Customers

# COMMAND ----------


# COMMAND ----------

customers = standardize_customers(dedupe(spark.table(f"{catalog}.bronze.customers"),["customer_id"]))
customers.write.mode("overwrite").saveAsTable(f"{catalog}.silver.customers")

# COMMAND ----------

merchants = standardize_merchants(dedupe(spark.table(f"{catalog}.bronze.merchants"), ["merchant_id"]))
merchants.write.mode("overwrite").saveAsTable(f"{catalog}.silver.merchants")

# COMMAND ----------

accounts_clean = standardize_accounts(dedupe(spark.table(f"{catalog}.bronze.accounts"),["account_id"]))
if not spark.catalog.tableExists(f"{catalog}.silver.accounts"):
    prepare_scd2_updates(accounts_clean).write.mode("overwrite").saveAsTable(f"{catalog}.silver.accounts")
else:
    apply_scd2(spark, accounts_clean, f"{catalog}.silver.accounts")

# COMMAND ----------

transactions = standardize_transactions(dedupe(spark.table(f"{catalog}.bronze.transactions"),["transaction_id"]))
transactions.write.mode("overwrite").saveAsTable(f"{catalog}.silver.transactions")

# COMMAND ----------

for name in ["customers", "accounts", "merchants", "transactions"]:
    count = spark.table(f"{catalog}.silver.{name}").count()
    assert count > 0, f"{name} table is empty!"
    print(f"{name}: {count:,} rows")