\# Data



\## What's here



\- `sample/` — a small, committed slice of the generated dataset: the full

&#x20; `customers.csv`, `accounts.csv`, and `merchants.csv`, plus a handful of

&#x20; representative days under `transactions/`. Safe to browse on GitHub;

&#x20; used for quick review and CI smoke tests.

\- `raw/` — the full generated dataset. \*\*Not committed\*\* — excluded via

&#x20; `.gitignore` because it's fully regenerable and can get large.



\## Regenerating the full dataset



From `data-generator\\`, with the virtual environment activated:



\\`\\`\\`

cd data-generator

.venv\\Scripts\\activate

python generate\_data.py --out ..\\data\\raw --seed 42 --n-customers 4000 --n-days 120

\\`\\`\\`



Same seed (`42`) always reproduces identical output.

