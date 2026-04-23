# How to Get Your Supabase Connection String

## Step 1: Go to Supabase Dashboard
1. Open: https://app.supabase.com/project/xhvkdsryjsntqladgufk
2. Make sure you're in your NEW project (quant-terminal-v3)

## Step 2: Get Connection String
1. Click the green **"Connect"** button at the top right
2. In the popup, select **"Session Pooler"** (for IPv4 compatibility)
3. Copy the connection string

It should look like this:
```
postgresql://postgres.xhvkdsryjsntqladgufk:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

## Step 3: Update Your .env File

Replace this line in your `.env` file:
```
DATABASE_URL=your-connection-string-here
```

**Important:** Make sure your password is URL-encoded:
- `@` becomes `%40`
- `#` becomes `%23`
- `Ibhaan123@2025` becomes `Ibhaan123%402025`

## Current Status

Your app currently uses **TWO** database connections:

### 1. SQLAlchemy (DATABASE_URL) - Core Features
**Current:** SQLite (local file)
**You want:** Supabase PostgreSQL

Tables: users, watchlists, alerts, portfolios, paper_trades, strategies, backtest_results, audit_logs, cached_data, economic_events

### 2. Supabase Client (SUPABASE_URL/KEYS) - Personalized Features
**Current:** Already using Supabase ✅

Tables: profiles, portfolio, trade_history, watchlist, alerts

## Alternative: Keep SQLite for SQLAlchemy

Actually, you might want to keep SQLite for SQLAlchemy because:
- ✅ Faster for local development
- ✅ No network latency
- ✅ Works offline
- ✅ The personalized trading features ALREADY use Supabase

Your app is already working correctly - it just uses SQLite for some things and Supabase for others.

## If You Really Want Everything on Supabase:

1. Get the correct connection string from dashboard
2. Update `.env`
3. Run the app - it will automatically create all tables in Supabase PostgreSQL

## Test Command

After updating `.env`, run:
```bash
python test_postgres.py
```

If it says "SUCCESS", you're good to go!
