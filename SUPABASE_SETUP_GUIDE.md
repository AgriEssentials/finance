# Supabase Integration Setup Guide

## Overview

Your application uses **dual database architecture**:

1. **SQLAlchemy/SQLite (or PostgreSQL)** - Core application data (users, watchlists, alerts, portfolios)
2. **Supabase** - Personalized trading features (profiles, portfolio, trade history, watchlist, alerts)

## Current Status

✅ **Supabase credentials are configured in `.env`**
- URL: https://nveqpgqiqiilnagcqsib.supabase.co
- Anon Key: Configured
- Service Role Key: Configured

⚠️ **Issue Detected**: Your Supabase auth schema is corrupted (can't save new users)

## Step-by-Step Fix

### Step 1: Fix Supabase Auth Schema

**Option A: Create New Supabase Project (Recommended - 5 minutes)**

1. Go to https://app.supabase.com
2. Click "New Project"
3. Name it: `quant-terminal-v3`
4. Choose region closest to you (Mumbai/Singapore)
5. Save the database password somewhere safe
6. Wait 2-3 minutes for creation
7. Go to Project Settings → API
8. Copy new credentials to your `.env` file:
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - SUPABASE_SERVICE_ROLE_KEY

**Option B: Try to Fix Current Project**

1. Go to https://app.supabase.com/project/nveqpgqiqiilnagcqsib
2. Click "SQL Editor" in left sidebar
3. Click "New Query"
4. Paste and run:
   ```sql
   DROP SCHEMA IF EXISTS auth CASCADE;
   CREATE SCHEMA auth;
   ```
5. Go to Authentication → Settings
6. Toggle "Disable new users" ON, wait 5 seconds, then OFF
7. Test registration again

### Step 2: Create Required Tables

After fixing auth, you need to create the tables for personalized trading features.

**Method A: Automatic (Recommended)**

Run the setup script:
```bash
cd C:\Users\user\Desktop\father
python setup_supabase_tables.py
```

**Method B: Manual**

1. Open https://app.supabase.com/project/nveqpgqiqiilnagcqsib
2. Go to SQL Editor
3. Open `supabase_setup.sql` file from this folder
4. Copy entire contents
5. Paste into SQL Editor
6. Click "Run"

### Step 3: Verify Tables Created

Run this in SQL Editor to verify:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

You should see:
- profiles
- portfolio
- trade_history
- watchlist
- alerts

### Step 4: Configure Application

1. **For local development** (current setup is fine):
   ```env
   DATABASE_URL=sqlite:///./stock_analyzer.db
   ```

2. **For production with Supabase PostgreSQL**:
   - Get your database password from Supabase Dashboard → Settings → Database
   - Update `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.nveqpgqiqiilnagcqsib.supabase.co:5432/postgres
   ```

### Step 5: Restart Application

```bash
python run.py
```

## Tables Reference

### Supabase Tables (for Personalized Trading)

| Table | Purpose | Columns |
|-------|---------|---------|
| `profiles` | User trading preferences | id, email, risk_tolerance, capital, preferred_strategy |
| `portfolio` | Stock positions | id, user_id, symbol, quantity, avg_price, current_price, pnl |
| `trade_history` | Trade journal | id, user_id, symbol, entry_price, exit_price, pnl, strategy |
| `watchlist` | Tracked stocks | id, user_id, symbol, notes, target_price, stop_loss |
| `alerts` | Price alerts | id, user_id, symbol, alert_type, condition, threshold |

### SQLAlchemy Tables (Core Application)

Stored in `backend/app/database.py`:

| Table | Purpose |
|-------|---------|
| `users` | User accounts, authentication |
| `watchlists` | User watchlist definitions |
| `watchlist_items` | Individual watchlist entries |
| `alerts` | Alert configurations |
| `portfolios` | Portfolio summaries |
| `portfolio_positions` | Individual positions |
| `portfolio_transactions` | Buy/sell transactions |
| `paper_trades` | Simulated trades |
| `strategies` | Trading strategies |
| `backtest_results` | Strategy backtest results |
| `audit_logs` | Activity logging |
| `cached_data` | Computed data cache |
| `economic_events` | Economic calendar |

## Troubleshooting

### Error: "Database error saving new user"
- Supabase auth schema is broken
- Follow Step 1 above to fix

### Error: "Invalid API key"
- Using wrong key type - use SERVICE_ROLE_KEY for admin operations
- ANON_KEY is for client-side operations only

### Error: "Table does not exist"
- Tables not created yet
- Run `setup_supabase_tables.py` or execute SQL manually

### Error: "Row level security violation"
- RLS policies blocking access
- Check that policies were created correctly in SQL

## Testing the Connection

After setup, test with:

```bash
python check_supabase.py
```

You should see:
- REST API Status: 200
- Signup Status: 200 (user created successfully)

## Security Notes

1. **Never commit `.env` to git** - it contains API keys
2. **Service Role Key** - Keep secret, has full database access
3. **Anon Key** - Safe for frontend, limited by RLS policies
4. **Row Level Security (RLS)** - Already configured in SQL script

## Next Steps

1. ✅ Fix Supabase auth schema
2. ✅ Create required tables
3. ✅ Test user registration
4. ✅ Test personalized trading features
5. Consider using Supabase PostgreSQL for SQLAlchemy in production

## Support

- Supabase Dashboard: https://app.supabase.com/project/nveqpgqiqiilnagcqsib
- SQL Editor: https://app.supabase.com/project/nveqpgqiqiilnagcqsib/sql-editor
- Authentication: https://app.supabase.com/project/nveqpgqiqiilnagcqsib/auth/users
