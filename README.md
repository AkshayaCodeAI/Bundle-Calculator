# Bundle Calculator

Full-stack bundle pricing tool — FastAPI backend + React frontend.

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Server runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs on `http://localhost:5173`.

## CSV Formats

**master_sku.csv** (required):
```
sku,mrp,cogs,price
1209SI,500,200,450
1526CB,600,250,550
```

**bundle_sku.csv** (required):
```
bundle_sku
1209SI1526CB
1209SI1526CB1185CC
```

**special_sku.csv** (optional):
```
bundle_sku,special_price
1209SI1526CB,900
```

## Pricing Rules

| Bundle Size | Discount    |
|-------------|-------------|
| Bundle of 2 | 10% off MRP |
| Bundle of 3 | 15% off MRP |

Special SKU prices override calculated prices.
