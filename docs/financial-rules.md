# Financial rules

These are MVP invariants. [ADR-002](adr/ADR-002-money-and-transaction-semantics.md) records the decision; [ADR-005](adr/ADR-005-analytics-definitions.md) records the analytics formulas.

## Money and currency

Use Python `Decimal` and PostgreSQL `NUMERIC(19,2)`. The money parser and ORM validator reject values with more than two fractional digits instead of rounding; direct SQL clients must obey the same contract because PostgreSQL coerces values to the column scale. API responses serialize monetary amounts as decimal strings. Reject currencies other than USD.

## Transaction meaning

| Kind | Sign | Financial treatment |
|---|---:|---|
| Income | Positive | Gross income |
| Expense | Negative | Gross expenses by absolute value |
| Refund | Positive | Reduces net spending; not income |
| Transfer out | Negative | Excluded from income and spending |
| Transfer in | Positive | Excluded from income and spending |

Store kind explicitly. Do not infer it from sign alone. Status is `pending`, `posted`, or `voided`; default analytics include posted only.

An internal transfer is two signed transactions linked across distinct accounts owned by the same user. The database checks matching opposite amounts and transfer kinds, and prevents linked financial fields from changing until the link is removed. A credit card purchase is an expense; paying the card from checking is a transfer. A refund is a separate positive transaction.

Categories have income or expense kind. Income transactions use income categories; expense and refund transactions use expense categories; transfers have no category.

## Analytics

- Gross income = sum of posted income amounts.
- Gross expenses = absolute sum of posted expense amounts.
- Refunds = sum of posted refund amounts.
- Net spending = gross expenses − refunds.
- Net cash flow = gross income − gross expenses + refunds.

Negative net spending is valid when refunds exceed expenses. Empty periods return valid zero amounts. Percentages with a zero denominator need a documented response convention before implementation.

## Dates

All date filters use `start_date <= transaction_date < end_date`. A month begins on its first day and ends before the next month's first day. Test leap years, month boundaries, and empty periods.
