

from pyspark.sql import Window, DataFrame
from pyspark.sql import functions as f

VALID_TXN_TYPES = ["purchase", "withdrawal", "transfer", "deposit"]
VALID_STATUSES = ["approved", "declined", "reversed"]
VALID_ACCOUNT_STATUSES = ["active", "closed", "frozen"]
TRACKED_ACCOUNT_COLS = ["account_type", "status"]

#-------------------------dedupe-------------------------

def dedupe(df: DataFrame, key_cols: list, order_col: str = "_ingested_at") -> DataFrame:
    '''
    Keep only the most recently ingested row per key_cols group.
    '''
    w = Window.partitionBy(*key_cols).orderBy(f.col(order_col).desc())

    return (
        df.withColumn("_row_num", f.row_number().over(w))
        .filter(f.col("_row_num") == 1)
        .drop("_row_num")
    )

def standardize_customers(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("first_name", f.trim(f.initcap(f.col("first_name"))))
        .withColumn("last_name", f.trim(f.initcap(f.col("last_name"))))
        .withColumn("email", f.lower(f.trim(f.col("email"))))
        .withColumn("phone", f.regexp_replace(f.col("phone"), r"[^\d]", ""))
    )
def standardize_accounts(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("account_type", f.trim(f.lower(f.col("account_type"))))
        .withColumn("_status_flag", 
            f.when(~f.col("status").isin(VALID_ACCOUNT_STATUSES), 
                   f.lit("unexpected_status"))
            .otherwise(None))
    )

def standardize_merchants(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("category", f.trim(f.lower(f.col("category"))))
    )

def standardize_transactions(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("channel", f.trim(f.lower(f.col("channel"))))
        .withColumn("_type_flag", 
            f.when(~f.col("type").isin(VALID_TXN_TYPES), 
                   f.lit("unexpected_type"))
            .otherwise(None))
        .withColumn("_status_flag", 
            f.when(~f.col("status").isin(VALID_STATUSES), 
                   f.lit("unexpected_status"))
            .otherwise(None))
    )

def prepare_scd2_updates(incoming_df: DataFrame) -> DataFrame:
    return (
        incoming_df.withColumn("effective_start_date", f.current_date())
        .withColumn("effective_end_date", f.lit(None).cast("date"))
        .withColumn("is_current", f.lit(True))
    )

def apply_scd2(spark, incoming_df : DataFrame, target_table:str) -> None:
    updates =   prepare_scd2_updates(incoming_df)   
    updates.createOrReplaceView("scd2_updates")

    conditions = " OR ".join([f"target.{c} <> source.{c}" for c in TRACKED_ACCOUNT_COLS])
    spark.sql(f"""
        MERGE INTO {target_table} AS target
        USING scd2_updates as source
        ON target.account_id = source.account_id AND target.is_current = true
        WHEN MATCHED AND ({conditions}) 
        THEN UPDATE SET is_current = false, effective_end_date = current_date()
         """)
    

    spark.sql(f"""
              MERGE INTO {target_table} as target
              USING scd2_updates as source
              ON target.account_id = source.account_id AND target.is_current = true
              WHEN NOT MATCHED THEN
              INSERT *
              """)

def run_dq_checks(spark, df: DataFrame, table_name: str, checks: dict) -> DataFrame:

    rows = []
    total = df.count()
    for check_name, condition in checks.items():
        failed = df.filter(f"NOT ({condition})").count()
        rows.append(
            (table_name, check_name, total, failed,
             round((total-failed)/total,4) if total else 0.0)
        )
    return (
        spark.createDataFrame(
            rows, ["table_name", "check_name", "total", "failed","pass_rate"]
        ).withColumn("generated_at", f.current_timestamp())
    )
    
    


        



