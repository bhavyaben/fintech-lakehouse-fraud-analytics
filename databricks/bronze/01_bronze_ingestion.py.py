# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
from pyspark.sql import types as T

transactions_schema = T.StructType([
    T.StructField("transaction_id", T.StringType(), True),
    T.StructField("account_id", T.StringType(), True),
    T.StructField("merchant_id", T.StringType(), True),
    T.StructField("type", T.StringType(), True),
    T.StructField("amount", T.DoubleType(), True),
    T.StructField("channel", T.StringType(), True),
    T.StructField("timestamp", T.TimestampType(), True),
    T.StructField("status", T.StringType(), True),
    T.StructField("is_fraud", T.BooleanType(), True),
])

# COMMAND ----------

dbutils.widgets.text("catalog", "fintech_lakehouse")
dbutils.widgets.text("raw_path", "/Volumes/fintech_lakehouse/bronze/landing/")
dbutils.widgets.text("checkpoint_path", "/Volumes/fintech_lakehouse/bronze/landing/_checkpoints")

catalog = dbutils.widgets.get("catalog")
raw_path = dbutils.widgets.get("raw_path")
checkpoint_path = dbutils.widgets.get("checkpoint_path")


# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

from pyspark.sql import functions as F

for name in ["customers","accounts","merchants"]:
    df =(
        spark.read
        .option("header","true")
        .option("inferSchema","true")
        .csv(f"{raw_path}/../{name}.csv")
        .withColumn("_source_file",F.col("_metadata.file_path"))
        .withColumn("_ingested_at",F.current_timestamp())
    )
    df.write.mode("overwrite").saveAsTable(f"{catalog}.bronze.{name}")

# COMMAND ----------

# DBTITLE 1,Ingest transactions with Auto Loader
stream_df = (
    spark.readStream.format("cloudFiles")
    .option("header", "true")
    .option("cloudFiles.format","csv")
    .schema(transactions_schema)
    .load(f"{raw_path}/transacations/")  # Note: directory name has typo 'transacations'
    .withColumn("_ingested_at", F.current_timestamp())
)

query = (stream_df.writeStream
    .format("delta")
    .option("checkpointLocation", f"{checkpoint_path}/transactions")
    .trigger(availableNow=True)
    .toTable(f"{catalog}.bronze.transactions"))

query.awaitTermination()

# COMMAND ----------

# DBTITLE 1,Verify row counts
for name in ["customers", "accounts", "merchants", "transactions"]:
    count = spark.table(f"{catalog}.bronze.{name}").count()
    print(f"{name}: {count:,} rows")