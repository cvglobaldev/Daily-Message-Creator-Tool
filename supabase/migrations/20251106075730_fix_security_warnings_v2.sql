/*
  # Fix Security Warnings

  ## Overview
  This migration addresses Supabase security advisor warnings:
  1. Unused indexes - These are intentional and will be used when the app starts receiving data
  2. Function search path - Makes the update_updated_at_column function secure

  ## Changes
  1. Replace update_updated_at_column function with secure version using stable search_path
  2. Add explanatory comments to indexes
  
  ## Security Notes
  - "Unused indexes" are NOT security issues - they're performance optimizations
  - Indexes become active when data exists and queries are executed
  - The function search_path fix prevents potential SQL injection attacks
*/

-- Replace the function with a secure version that has a stable search_path
-- CASCADE will recreate the triggers automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER 
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Add explanatory comments to indexes (these are NOT security issues)
-- These indexes are essential for production performance

COMMENT ON INDEX idx_admin_users_username IS 'Performance: Used for login authentication queries - active once users start logging in';
COMMENT ON INDEX idx_admin_users_email IS 'Performance: Used for email-based lookup and uniqueness validation';
COMMENT ON INDEX idx_bots_status IS 'Performance: Used for filtering active/inactive bots in dashboard queries';
COMMENT ON INDEX idx_bots_creator_id IS 'Performance: Used for user-specific bot listings';
COMMENT ON INDEX idx_users_bot_id IS 'Performance: CRITICAL - Used for bot-specific user queries in multi-bot architecture';
COMMENT ON INDEX idx_users_phone_number IS 'Performance: CRITICAL - Used for user lookup during message processing (high-frequency)';
COMMENT ON INDEX idx_users_status IS 'Performance: Used for active users filtering in analytics dashboard';
COMMENT ON INDEX idx_content_bot_id IS 'Performance: Used for bot-specific content retrieval';
COMMENT ON INDEX idx_content_day_number IS 'Performance: Used for day-based content queries';
COMMENT ON INDEX idx_content_bot_day IS 'Performance: CRITICAL - Composite index for bot+day content lookup (most common query)';
COMMENT ON INDEX idx_message_logs_user_id IS 'Performance: CRITICAL - Used for conversation history (high-frequency queries)';
COMMENT ON INDEX idx_message_logs_timestamp IS 'Performance: Used for time-based filtering and analytics';
COMMENT ON INDEX idx_message_logs_handoff IS 'Performance: Used for human handoff queue (filtered queries)';
COMMENT ON INDEX idx_tag_rules_tag_name IS 'Performance: Used for tag rule lookups during message processing';
COMMENT ON INDEX idx_tag_rules_rule_type IS 'Performance: Used for filtering AI-powered vs rule-based tags';
COMMENT ON INDEX idx_tag_rules_parent_id IS 'Performance: Used for hierarchical tag relationship queries';
COMMENT ON INDEX idx_tag_rules_active IS 'Performance: CRITICAL - Used for active rules filtering';
COMMENT ON INDEX idx_system_settings_key IS 'Performance: Used for settings lookup with uniqueness enforcement';

-- Note: "Unused index" warnings are informational only
-- Indexes cannot be "used" until:
-- 1. Data exists in the tables
-- 2. Queries that match the index pattern are executed
-- 3. The query planner determines the index is beneficial
-- 
-- These indexes are intentionally created now for production readiness