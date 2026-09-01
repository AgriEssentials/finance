# Supabase Database Status & Setup Guide

## 🔍 Current Status

### Your Existing Supabase Project
**Project URL:** `https://nveqpgqiqiilnagcqsib.supabase.co`

| Component | Status | Details |
|-----------|--------|---------|
| Connection | ✅ Working | Can connect via Python |
| Tables | ✅ 5 tables exist | profiles, portfolio, trade_history, watchlist, alerts |
| **Auth Schema** | ❌ **CORRUPTED** | Cannot create new users |

### The Problem
Your Supabase auth schema is corrupted. When trying to create users, you get:
```
"Database error saving new user"
```

This means:
- ❌ User registration won't work
- ❌ Personalized trading features won't work
- ❌ The app can't save user data to Supabase

## ✅ Solution: Create New Supabase Project

### Step 1: Create New Project (5 minutes)

1. Go to https://app.supabase.com
2. Click **"New Project"**
3. Fill in:
   - **Name:** `quant-terminal-v3` (or any name you like)
   - **Database Password:** Generate a strong one and SAVE IT
   - **Region:** Choose closest to you (Mumbai, Singapore, or US East)
4. Click **"Create New Project"**
5. Wait 2-3 minutes for it to be ready

### Step 2: Get New API Keys

1. In your new project, click **Project Settings** (gear icon)
2. Click **API** in the left sidebar
3. Copy these 3 values:
   - `URL` (starts with https://)
   - `anon public` key (starts with eyJhbG...)
   - `service_role secret` key (starts with eyJhbG...)

### Step 3: Update Your .env File

Open `C:\Users\user\Desktop\father\.env` and update lines 8-10:

```env
SUPABASE_URL=https://your-new-project.supabase.co
SUPABASE_ANON_KEY=eyJhbG...your-new-anon-key
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...your-new-service-key
```

### Step 4: Create Tables in New Project

1. In your new project, click **"SQL Editor"** in left sidebar
2. Click **"New Query"**
3. Open the file `supabase_quick_setup.sql` from this folder
4. Copy the entire contents
5. Paste into SQL Editor
6. Click **"Run"**

This creates:
- ✅ profiles table (with auto-trigger for new users)
- ✅ portfolio table
- ✅ trade_history table
- ✅ watchlist table
- ✅ alerts table

### Step 5: Test

Run this to verify everything works:
```bash
python check_tables.py
python test_table_structure.py
```

You should see "SUCCESS" messages.

### Step 6: Restart Your App

```bash
python run.py
```

Then test:
1. Go to http://localhost:8000/auth.html
2. Try to register a new user
3. If registration works, you're all set!

## 📊 Database Architecture

Your app uses **TWO** database systems:

### 1. SQLAlchemy (SQLite by default)
**Location:** Local file `stock_analyzer.db`

**Tables:**
- `users` - User accounts & authentication
- `watchlists` - Watchlist definitions
- `watchlist_items` - Individual watchlist entries
- `alerts` - Alert configurations
- `portfolios` - Portfolio summaries
- `portfolio_positions` - Stock positions
- `portfolio_transactions` - Buy/sell records
- `paper_trades` - Simulated trades
- `strategies` - Trading strategies
- `backtest_results` - Strategy backtests
- `audit_logs` - Activity logging
- `cached_data` - Computed data cache
- `economic_events` - Economic calendar

**Purpose:** Core application features

### 2. Supabase (PostgreSQL)
**Location:** Cloud database at supabase.co

**Tables:**
- `profiles` - User trading preferences (risk tolerance, capital, strategy)
- `portfolio` - Live position tracking with PnL
- `trade_history` - Trade journal for AI coach
- `watchlist` - Real-time watchlist with notes
- `alerts` - Price and indicator alerts

**Purpose:** Personalized trading assistant features

## 🔐 Security Notes

### Row Level Security (RLS)
All Supabase tables have RLS policies that ensure:
- Users can ONLY see their own data
- Users can ONLY modify their own data
- Data is isolated between users

### API Keys
- **Anon Key:** Safe for frontend, limited by RLS
- **Service Role Key:** Has full access, keep secret

## 📁 Files Created for You

| File | Purpose |
|------|---------|
| `supabase_setup.sql` | Complete SQL for table creation |
| `supabase_quick_setup.sql` | Quick setup SQL for new project |
| `check_tables.py` | Check if tables exist |
| `check_table_structure.py` | Verify table columns |
| `test_table_structure.py` | Test with actual data insertion |
| `SUPABASE_SETUP_GUIDE.md` | Full setup documentation |
| `SUPABASE_FIX.txt` | Original fix instructions |

## 🚀 Quick Commands

```bash
# Check current status
python check_tables.py

# Test if everything works
python test_table_structure.py

# Run the app
python run.py
```

## ❓ FAQ

**Q: Do I need to create a new project?**
A: Yes, your current auth schema is corrupted and can't be easily fixed. A new project takes 5 minutes and gives you a clean slate.

**Q: Will I lose data?**
A: No, your current project has 0 users and empty tables, so there's nothing to lose.

**Q: Can I use Supabase PostgreSQL for SQLAlchemy too?**
A: Yes! In production, you can set `DATABASE_URL` to your Supabase PostgreSQL connection string. This unifies both databases.

**Q: How do I get the PostgreSQL connection string?**
A: In Supabase Dashboard → Settings → Database → Connection String. Use the URI format.

**Q: What if I still can't create users?**
A: Make sure you:
1. Copied the correct API keys (not from old project)
2. Restarted the app after updating .env
3. Are using the new project URL

## 📞 Next Steps

1. ✅ Create new Supabase project
2. ✅ Update `.env` with new credentials
3. ✅ Run SQL setup in new project
4. ✅ Test with `python test_table_structure.py`
5. ✅ Restart app and test registration
6. ✅ Enjoy personalized trading features!

## 📚 Useful Links

- **Supabase Dashboard:** https://app.supabase.com
- **Your Old Project:** https://app.supabase.com/project/nveqpgqiqiilnagcqsib
- **SQL Editor:** https://app.supabase.com/project/[your-new-project]/sql-editor
- **Project Settings:** https://app.supabase.com/project/[your-new-project]/settings/api
