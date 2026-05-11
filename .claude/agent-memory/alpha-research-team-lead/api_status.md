---
name: api_status
description: API connection status and rate limiting issues
type: project
---

# API Status

## Connection
- **Status**: Connected and authenticated
- **Email**: 2645471525@qq.com
- **Authentication**: JWT token stored automatically by session

## Rate Limiting
- **Severity**: Severe
- **Error Code**: 429 Too Many Requests
- **Impact**: Creating simulations frequently fails
- **Workaround**: 
  - Use longer delays (15-30 seconds) between requests
  - Implement exponential backoff (10s, 20s, 30s, etc.) on 429 errors
  - Wait several minutes between batches

## Valid Fields
- `actual_eps_value_quarterly` - works in expressions
- `actual_dividend_value_quarterly` - works in expressions
- `actual_cashflow_per_share_value_quarterly` - works in expressions

## How to Apply
- When creating simulations, always implement retry logic with backoff
- If seeing 429 errors, wait longer before retrying
- Consider running creation scripts in background with long delays
