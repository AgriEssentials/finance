-- ============================================================================
-- SUPABASE DATABASE SETUP & FIX SCRIPT
-- For: AI Stock Analysis Assistant
-- Project: https://nveqpgqiqiilnagcqsib.supabase.co
-- ============================================================================

-- ============================================================================
-- PART 1: FIX AUTH SCHEMA (if corrupted)
-- ============================================================================

-- Reset auth schema (only if auth is broken - run this first if you can't create users)
-- WARNING: This will delete all existing auth data
-- DROP SCHEMA IF EXISTS auth CASCADE;
-- CREATE SCHEMA auth;

-- Alternative: Just check auth schema health
SELECT 'Auth schema exists and has tables' as status 
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'auth' 
    AND table_name = 'users'
);

-- ============================================================================
-- PART 2: CREATE PROFILES TABLE
-- For personalized trading user profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    risk_tolerance TEXT DEFAULT 'medium' CHECK (risk_tolerance IN ('low', 'medium', 'high')),
    capital NUMERIC DEFAULT 100000,
    preferred_strategy TEXT DEFAULT 'swing' CHECK (preferred_strategy IN ('intraday', 'swing', 'long_term')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for profiles
CREATE POLICY "Users can view own profile" 
    ON public.profiles 
    FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON public.profiles 
    FOR UPDATE 
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" 
    ON public.profiles 
    FOR INSERT 
    WITH CHECK (auth.uid() = id);

-- Trigger to automatically create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, risk_tolerance, capital, preferred_strategy)
    VALUES (
        NEW.id, 
        NEW.email, 
        'medium',  -- default risk tolerance
        100000,    -- default capital
        'swing'    -- default strategy
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- PART 3: CREATE PORTFOLIO TABLE
-- For tracking user stock positions
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    avg_price NUMERIC NOT NULL DEFAULT 0,
    current_price NUMERIC,
    pnl NUMERIC DEFAULT 0,
    pnl_percent NUMERIC DEFAULT 0,
    sector TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- Enable RLS on portfolio
ALTER TABLE public.portfolio ENABLE ROW LEVEL SECURITY;

-- RLS Policies for portfolio
CREATE POLICY "Users can view own portfolio" 
    ON public.portfolio 
    FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert to own portfolio" 
    ON public.portfolio 
    FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own portfolio" 
    ON public.portfolio 
    FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete from own portfolio" 
    ON public.portfolio 
    FOR DELETE 
    USING (auth.uid() = user_id);

-- ============================================================================
-- PART 4: CREATE TRADE_HISTORY TABLE
-- For trade journal and history tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.trade_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    entry_price NUMERIC NOT NULL,
    exit_price NUMERIC,
    quantity INTEGER NOT NULL,
    trade_type TEXT NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    strategy TEXT,
    reason TEXT,
    emotion TEXT,
    pnl NUMERIC,
    entry_date TIMESTAMPTZ DEFAULT NOW(),
    exit_date TIMESTAMPTZ,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on trade_history
ALTER TABLE public.trade_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies for trade_history
CREATE POLICY "Users can view own trade history" 
    ON public.trade_history 
    FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert to own trade history" 
    ON public.trade_history 
    FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own trade history" 
    ON public.trade_history 
    FOR UPDATE 
    USING (auth.uid() = user_id);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_trade_history_user_id ON public.trade_history(user_id);
CREATE INDEX IF NOT EXISTS idx_trade_history_symbol ON public.trade_history(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_history_entry_date ON public.trade_history(entry_date DESC);

-- ============================================================================
-- PART 5: CREATE WATCHLIST TABLE
-- For user watchlists
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    notes TEXT,
    target_price NUMERIC,
    stop_loss NUMERIC,
    alert_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- Enable RLS on watchlist
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;

-- RLS Policies for watchlist
CREATE POLICY "Users can view own watchlist" 
    ON public.watchlist 
    FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can add to own watchlist" 
    ON public.watchlist 
    FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can remove from own watchlist" 
    ON public.watchlist 
    FOR DELETE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own watchlist" 
    ON public.watchlist 
    FOR UPDATE 
    USING (auth.uid() = user_id);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON public.watchlist(user_id);

-- ============================================================================
-- PART 6: CREATE ALERTS TABLE
-- For price and indicator alerts
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('price', 'indicator', 'news', 'volume')),
    condition TEXT NOT NULL CHECK (condition IN ('above', 'below', 'crosses_above', 'crosses_below')),
    threshold NUMERIC NOT NULL,
    message TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMPTZ,
    notification_methods JSONB DEFAULT '["email"]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Enable RLS on alerts
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for alerts
CREATE POLICY "Users can view own alerts" 
    ON public.alerts 
    FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own alerts" 
    ON public.alerts 
    FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own alerts" 
    ON public.alerts 
    FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own alerts" 
    ON public.alerts 
    FOR DELETE 
    USING (auth.uid() = user_id);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON public.alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON public.alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON public.alerts(user_id, is_active);

-- ============================================================================
-- PART 7: GRANT PERMISSIONS
-- ============================================================================

-- Grant permissions to authenticated users
GRANT ALL ON public.profiles TO authenticated;
GRANT ALL ON public.portfolio TO authenticated;
GRANT ALL ON public.trade_history TO authenticated;
GRANT ALL ON public.watchlist TO authenticated;
GRANT ALL ON public.alerts TO authenticated;

-- Grant permissions to anon (for signups)
GRANT INSERT, SELECT ON public.profiles TO anon;

-- ============================================================================
-- PART 8: VERIFY SETUP
-- ============================================================================

SELECT 'Tables created successfully' as status;

-- List all tables created
SELECT 
    table_name,
    'Created' as status
FROM 
    information_schema.tables 
WHERE 
    table_schema = 'public' 
    AND table_name IN ('profiles', 'portfolio', 'trade_history', 'watchlist', 'alerts')
ORDER BY 
    table_name;
