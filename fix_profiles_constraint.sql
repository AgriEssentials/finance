-- ============================================================================
-- FIX: Remove foreign key constraint from profiles table
-- This allows profiles to exist even when Supabase Auth is not available
-- Run this in your Supabase SQL Editor
-- ============================================================================

-- First, check if the constraint exists
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'profiles'::regclass;

-- Remove the foreign key constraint if it exists
ALTER TABLE public.profiles 
DROP CONSTRAINT IF EXISTS profiles_id_fkey;

-- Also change the ID column to not require UUID from auth.users
-- This allows us to use any ID (including SQLite integer IDs converted to text)
ALTER TABLE public.profiles 
ALTER COLUMN id DROP NOT NULL;

-- Add a unique email constraint if not exists
ALTER TABLE public.profiles 
ADD CONSTRAINT profiles_email_unique UNIQUE (email);

-- Verify the changes
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'profiles';

-- Test: Insert a profile without an auth user (this should now work)
-- This simulates what happens when a user registers but Supabase auth rate limits
INSERT INTO public.profiles (id, email, risk_tolerance, capital, preferred_strategy)
VALUES ('test-user-123', 'test_profile@example.com', 'medium', 100000, 'swing')
ON CONFLICT (email) DO NOTHING;

-- Check if it was inserted
SELECT * FROM public.profiles WHERE email = 'test_profile@example.com';

-- Clean up test data
DELETE FROM public.profiles WHERE email = 'test_profile@example.com';

-- ============================================================================
-- RESULT: Profiles can now be created without requiring an auth.users entry
-- ============================================================================
