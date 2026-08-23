from pyspark.sql import SparkSession
import pytest
from databricks.silver.transformations import dedup_accounts  # whatever you named it

@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder.master("local[1]").getOrCreate()

def test_dedup_removes_duplicate_account(spark):
    data = [
        ("ACC1", "active", "2024-01-01"),
        ("ACC1", "active", "2024-01-02"),  # duplicate account_id, newer timestamp
        ("ACC2", "closed", "2024-01-01"),
    ]
    df = spark.createDataFrame(data, ["account_id", "status", "_ingested_at"])
    result = dedup_accounts(df)
    assert result.count() == 2  # ACC1 appears once, ACC2 once