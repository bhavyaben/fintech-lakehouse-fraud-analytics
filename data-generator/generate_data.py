"""
generate_data.py — synthetic fintech transaction data generator.

Builds four related tables that back the medallion lakehouse project:
    customers.csv
    accounts.csv
    merchants.csv
    transactions_YYYY-MM-DD.csv   (one file per simulated day)

Design decisions baked in here (tune these to make the project your own):
    - risk_segment on customers is weighted 70% low / 25% medium / 5% high.
    - merchant categories carry a baseline risk_score, skewed high for
      crypto_exchange, money_transfer, and gambling.
    - each account gets a "typical amount" profile (log-normal draw) used
      only internally, to decide whether a given transaction looks
      unusually large for that account.
    - fraud is simulated as a base probability that gets boosted by
      high-risk merchant category, late-night hours, cross-border/web
      channel, and unusually large amount — plus a little random noise
      so the rule isn't perfectly clean.

Usage:
    python generate_data.py --out ..\\data\\raw --seed 42 --n-customers 4000 --n-days 120
"""

import argparse
import datetime as dt

import numpy as np
import pandas as pd

# --- reference data -------------------------------------------------------

MERCHANT_CATEGORIES = [
    # (category, baseline_risk_score, weight in the merchant population)
    ("grocery", 0.02, 0.18),
    ("retail", 0.04, 0.18),
    ("restaurant", 0.03, 0.14),
    ("travel", 0.08, 0.08),
    ("utilities", 0.01, 0.10),
    ("electronics", 0.06, 0.10),
    ("crypto_exchange", 0.55, 0.06),
    ("money_transfer", 0.45, 0.08),
    ("gambling", 0.40, 0.08),
]

ACCOUNT_TYPES = ["checking", "savings", "credit"]
ACCOUNT_TYPE_WEIGHTS = [0.55, 0.30, 0.15]

TXN_TYPES = ["purchase", "withdrawal", "transfer", "deposit"]
TXN_TYPE_WEIGHTS = [0.65, 0.10, 0.15, 0.10]

CHANNELS = ["in_person", "web", "mobile", "atm"]
CHANNEL_WEIGHTS = [0.35, 0.30, 0.25, 0.10]

STATUS_CHOICES = ["approved", "declined", "reversed"]
STATUS_WEIGHTS = [0.93, 0.05, 0.02]


# --- table generators -------------------------------------------------------

def gen_customers(n, rng):
    risk_segment = rng.choice(["low", "medium", "high"], size=n, p=[0.70, 0.25, 0.05])
    signup_offset_days = rng.integers(0, 700, size=n)
    signup_date = pd.Timestamp("2023-01-01") + pd.to_timedelta(signup_offset_days, unit="D")

    return pd.DataFrame({
        "customer_id": [f"CUST{100000 + i}" for i in range(n)],
        "first_name": [f"First{i}" for i in range(n)],
        "last_name": [f"Last{i}" for i in range(n)],
        "email": [f"customer{i}@example.com" for i in range(n)],
        "phone": [f"555-{1000000 + i:07d}" for i in range(n)],
        "signup_date": signup_date.date,
        "risk_segment": risk_segment,
    })


def gen_accounts(customers_df, rng):
    """Returns a DataFrame with one or more accounts per customer.

    Includes an internal `_avg_txn_amount` column (a per-account spending
    baseline) that transactions are generated around. Drop this column
    before writing accounts.csv — it isn't part of the published schema.
    """
    rows = []
    account_counter = 0
    for cust_id in customers_df["customer_id"]:
        n_accounts = rng.choice([1, 2, 3], p=[0.55, 0.30, 0.15])
        for _ in range(n_accounts):
            account_counter += 1
            account_type = rng.choice(ACCOUNT_TYPES, p=ACCOUNT_TYPE_WEIGHTS)
            open_offset_days = int(rng.integers(0, 700))
            open_date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=open_offset_days)

            # ~4% of accounts are closed; the rest stay active or get frozen
            status_roll = rng.random()
            if status_roll < 0.04:
                status = "closed"
                close_date = open_date + pd.Timedelta(days=int(rng.integers(30, 500)))
            elif status_roll < 0.08:
                status = "frozen"
                close_date = pd.NaT
            else:
                status = "active"
                close_date = pd.NaT

            # log-normal spending baseline: most accounts cluster low,
            # a long tail of higher-spend accounts
            avg_txn_amount = float(rng.lognormal(mean=3.6, sigma=0.7))

            rows.append({
                "account_id": f"ACCT{200000 + account_counter}",
                "customer_id": cust_id,
                "account_type": account_type,
                "status": status,
                "open_date": open_date.date(),
                "close_date": close_date.date() if pd.notna(close_date) else None,
                "_avg_txn_amount": round(avg_txn_amount, 2),
            })

    return pd.DataFrame(rows)


def gen_merchants(n, rng):
    categories, base_risks, weights = zip(*MERCHANT_CATEGORIES)
    category_idx = rng.choice(len(categories), size=n, p=weights)

    risk_noise = rng.normal(0, 0.03, size=n)
    risk_score = np.clip(
        np.array(base_risks)[category_idx] + risk_noise, 0.01, 0.99
    )

    # a small share of merchants are foreign — used later as a fraud boost
    is_foreign = rng.random(n) < 0.08

    return pd.DataFrame({
        "merchant_id": [f"MERCH{300000 + i}" for i in range(n)],
        "category": np.array(categories)[category_idx],
        "mcc_code": rng.integers(4000, 9999, size=n),
        "risk_score": np.round(risk_score, 3),
        "is_foreign": is_foreign,
    })


def gen_transactions(day, accounts_df, merchants_df, rng):
    """Generate one day's worth of transactions.

    `day` is a datetime.date. `accounts_df` must include the internal
    `_avg_txn_amount` column produced by gen_accounts.
    """
    # only active/frozen accounts transact; frozen accounts transact rarely
    eligible = accounts_df[accounts_df["status"] != "closed"].copy()
    txn_weight = np.where(eligible["status"] == "frozen", 0.1, 1.0)
    txn_weight = txn_weight / txn_weight.sum()

    # roughly 0.5-1.5 transactions per eligible account per day
    n_txns = int(len(eligible) * rng.uniform(0.5, 1.5))
    chosen_accounts = eligible.sample(
        n=n_txns, weights=txn_weight, replace=True, random_state=int(rng.integers(0, 2**32 - 1))
    ).reset_index(drop=True)

    merchant_sample = merchants_df.sample(
        n=n_txns, replace=True, random_state=int(rng.integers(0, 2**32 - 1))
    ).reset_index(drop=True)

    # amount: log-normal around each account's own baseline
    amount = rng.lognormal(
        mean=np.log(chosen_accounts["_avg_txn_amount"].clip(lower=5.0)),
        sigma=0.6,
    )
    amount = np.round(amount, 2)

    hour = rng.integers(0, 24, size=n_txns)
    minute = rng.integers(0, 60, size=n_txns)
    second = rng.integers(0, 60, size=n_txns)
    timestamps = [
        dt.datetime.combine(day, dt.time(h, m, s))
        for h, m, s in zip(hour, minute, second)
    ]

    channel = rng.choice(CHANNELS, size=n_txns, p=CHANNEL_WEIGHTS)
    txn_type = rng.choice(TXN_TYPES, size=n_txns, p=TXN_TYPE_WEIGHTS)
    status = rng.choice(STATUS_CHOICES, size=n_txns, p=STATUS_WEIGHTS)

    # --- fraud probability: base rate + explainable boosts + noise ---
    base_rate = 0.004

    high_risk_merchant = merchant_sample["risk_score"].to_numpy() > 0.20
    night_hours = (hour >= 0) & (hour < 5)
    cross_border_web = (merchant_sample["is_foreign"].to_numpy()) & (channel == "web")
    unusually_large = amount > (chosen_accounts["_avg_txn_amount"].to_numpy() * 3)

    fraud_prob = np.full(n_txns, base_rate)
    fraud_prob[high_risk_merchant] *= 6
    fraud_prob[night_hours] *= 4
    fraud_prob[cross_border_web] *= 3
    fraud_prob[unusually_large] *= 5

    fraud_prob = fraud_prob + rng.normal(0, 0.002, size=n_txns)
    fraud_prob = np.clip(fraud_prob, 0.0002, 0.95)

    is_fraud = rng.random(n_txns) < fraud_prob

    return pd.DataFrame({
        "transaction_id": [f"TXN{day.strftime('%Y%m%d')}{i:06d}" for i in range(n_txns)],
        "account_id": chosen_accounts["account_id"].to_numpy(),
        "merchant_id": merchant_sample["merchant_id"].to_numpy(),
        "type": txn_type,
        "amount": amount,
        "channel": channel,
        "timestamp": timestamps,
        "status": status,
        "is_fraud": is_fraud,
    })


# --- orchestration -------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic fintech data.")
    parser.add_argument("--out", required=True, help="Output directory for the CSVs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-customers", type=int, default=4000)
    parser.add_argument("--n-merchants", type=int, default=300)
    parser.add_argument("--n-days", type=int, default=120)
    parser.add_argument("--start-date", default="2024-01-01")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    out_dir = args.out
    import os
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "transactions"), exist_ok=True)

    customers_df = gen_customers(args.n_customers, rng)
    accounts_full_df = gen_accounts(customers_df, rng)
    merchants_df = gen_merchants(args.n_merchants, rng)

    customers_df.to_csv(os.path.join(out_dir, "customers.csv"), index=False)
    accounts_full_df.drop(columns=["_avg_txn_amount"]).to_csv(
        os.path.join(out_dir, "accounts.csv"), index=False
    )
    merchants_df.to_csv(os.path.join(out_dir, "merchants.csv"), index=False)

    start = dt.datetime.strptime(args.start_date, "%Y-%m-%d").date()
    total_txns = 0
    total_fraud = 0
    for i in range(args.n_days):
        day = start + dt.timedelta(days=i)
        txns_df = gen_transactions(day, accounts_full_df, merchants_df, rng)
        txns_df.to_csv(
            os.path.join(out_dir, "transactions", f"transactions_{day.isoformat()}.csv"),
            index=False,
        )
        total_txns += len(txns_df)
        total_fraud += int(txns_df["is_fraud"].sum())

    print(f"customers:  {len(customers_df):,}")
    print(f"accounts:   {len(accounts_full_df):,}")
    print(f"merchants:  {len(merchants_df):,}")
    print(f"days:       {args.n_days}")
    print(f"transactions: {total_txns:,}")
    print(f"fraud rate: {total_fraud / total_txns:.4%}")


if __name__ == "__main__":
    main()