---
name: alternative_datasets
description: Documentation of alternative datasets and fields found in forum
type: reference
---

# Alternative Datasets and Fields

## From Forum Posts

### other355 dataset
- oth335_combined_all_region_hedge - "来自对冲模型的得分（Score from the hedge model）"
- This is from IND region

### IND template
- "行业中性化残差信号IND模板" suggests using industry neutralization
- The "IND" suggests this is a specific region or type

### Key insight from forum
The problem is we cannot apply neutralization because all values (industry, market, sector, crowding) are INVALID.

But perhaps the API accepts a different naming convention. Let me try variations.

## Valid Fields We Know
- actual_eps_value_quarterly (analyst4)
- actual_sales_value_quarterly
- actual_cashflow_per_share_value_quarterly
- actual_dividend_value_quarterly
- close, vwap, open (market data)

## Something to Try
Maybe the neutralization issue is case sensitivity. Let me try "INDUSTRY" or "Market" with capital letters.

Actually, looking at the error message format: "is not a valid choice" - this suggests there's a fixed list of options. Perhaps we need to find the exact valid values.