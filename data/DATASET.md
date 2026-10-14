# Dataset provenance

`credit.csv` is derived from the official UCI Machine Learning Repository **Statlog (German Credit Data)** dataset, donated in 1994 by Hans Hofmann. Source: https://archive.ics.uci.edu/dataset/144/statloggermancreditdata ; DOI: https://doi.org/10.24432/C5NC77 ; licence: CC BY 4.0.

The upstream `german.data` contains 1,000 rows and 20 predictors plus class. Sakshi selects 11 predictors to match the demonstration form. `default=1` means UCI class 2 (bad credit risk); `default=0` means class 1 (good credit risk). This is historical German data, not Indian lending data and not a production-ready lending dataset.

Categorical encodings used by Sakshi: `checking_account`: A11=1, A12=2, A13=3, A14=4; `credit_history`: A30=0, A31=1, A32=2, A33=3, A34=4; `employment_years`: A71=0, A72=1, A73=2, A74=3, A75=4; `savings_account`: A61=0, A62=1, A63=2, A64=3, A65=4. Other selected predictors retain their source numeric values. These ordinal encodings are a compact MVP interface and impose ordering assumptions; they should be revisited in a richer categorical model.
