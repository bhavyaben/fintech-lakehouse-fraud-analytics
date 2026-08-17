# Architecture

Simulates a fintech company's transaction pipeline: synthetic customer/account/transaction
data flows through a Databricks lakehouse (bronze/silver in PySpark, gold in dbt) into a
Power BI fraud-monitoring dashboard.

## Diagram

\```mermaid
flowchart LR
    A[Source CSVs<br/>Python generator] --> B[Bronze<br/>Auto Loader / Delta]
    B --> C[Silver<br/>PySpark cleansing + SCD2]
    C --> D[Gold<br/>dbt staging/int/marts]
    D --> E[Power BI<br/>dashboard]
    F[Databricks Workflows] -.orchestrates.-> B
    F -.orchestrates.-> C
    F -.orchestrates.-> D
    G[GitHub Actions CI] -.tests.-> D
\```

## Why each layer exists

**Source (synthetic data generator)** — The pipeline starts from a Python generator rather
than a real data source because no real fintech data is available or appropriate for a
public project. Generating it ourselves also means the dataset is fully reproducible (same
seed, same data) and the shape of the entities is a deliberate design choice.

**Bronze** — Bronze exists to capture the raw data exactly as it arrived, with nothing
cleaned, deduplicated, or reshaped yet. Keeping an unmodified, replayable copy means that
if a downstream bug is ever found, we can re-derive silver and gold from bronze without
needing to re-fetch anything from the source.

**Silver** — Silver exists because cleansing and history-tracking need to happen somewhere
that isn't the raw copy. This is where duplicates are removed, fields are standardized, and
account history is tracked with SCD Type 2 — separating "what the source sent us" from
"what we trust to be true."

**Gold (dbt)** — Gold exists to turn trusted silver data into a business-ready, dimensional
model that's easy and fast for a BI tool to query. Doing this in dbt means the transformation
logic is SQL-based, version-controlled, automatically tested, and self-documenting.

**Power BI** — Power BI exists as the single consumption layer so stakeholders never need
to query gold tables directly. Building a real semantic model with DAX measures here is what
turns a set of tables into a tool someone can actually use to make a decision.

**Databricks Workflows (orchestration)** — This exists so the bronze -> silver -> gold
pipeline runs on a schedule with explicit dependencies, instead of each notebook being run
by hand in the right order.

**GitHub Actions CI** — This exists to catch a broken model or a bad transformation before
it merges into `main`, not after.