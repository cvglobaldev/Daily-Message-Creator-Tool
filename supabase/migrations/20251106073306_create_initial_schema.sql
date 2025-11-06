/*
  # Daily Message Creator Tool - Initial Database Schema

  ## Overview
  This migration creates the complete database schema for the Daily Message Creator Tool (Faith Journey Chatbot).
  The system supports multi-bot management with WhatsApp and Telegram integration, AI-powered content delivery,
  and comprehensive user journey tracking.

  ## Tables Created

  ### 1. admin_users
  Admin authentication and authorization for the web dashboard
  - Stores admin credentials with hashed passwords
  - Supports role-based access (admin, super_admin)
  - Tracks login history

  ### 2. bots
  Multi-bot management with platform-specific configurations
  - Supports WhatsApp (Meta API and WAHA) and Telegram platforms
  - Configurable AI prompts, delivery schedules, and journey duration
  - Timezone-based scheduling support
  - Customizable command messages

  ### 3. users
  End-users receiving daily spiritual journey content
  - Platform identification (WhatsApp/Telegram)
  - Journey progress tracking (current day, status)
  - Location data and timezone information
  - Quiet hours support
  - Bot isolation (each user belongs to one bot)

  ### 4. content
  Daily journey content with multimedia support
  - Text, image, video, and audio content
  - Reflection questions and tags
  - Bot-specific content isolation
  - Greeting and daily content types
  - Customizable confirmation buttons

  ### 5. message_logs
  Complete conversation history and AI analysis
  - Message direction (incoming/outgoing)
  - AI sentiment analysis and tagging
  - Human handoff detection
  - Voice message identification

  ### 6. tag_rules
  AI-powered and rule-based tagging system
  - Faith journey milestone detection
  - Hierarchical tag support (parent-child relationships)
  - When-If-Then rule configuration
  - Priority-based evaluation

  ### 7. system_settings
  Application configuration storage
  - Key-value pair storage
  - Centralized settings management

  ## Security
  - RLS enabled on all tables
  - Authenticated access required for all operations
  - Proper indexes for query performance

  ## Notes
  - All timestamps use UTC
  - JSON fields for flexible metadata storage
  - Foreign key constraints with cascade delete where appropriate
  - Unique constraints for data integrity
*/

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create admin_users table
CREATE TABLE IF NOT EXISTS admin_users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(80) UNIQUE NOT NULL,
  email VARCHAR(120) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(100) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'admin',
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);

-- Create bots table
CREATE TABLE IF NOT EXISTS bots (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  platforms TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  
  -- WhatsApp Meta API configuration
  whatsapp_connection_type VARCHAR(20) NOT NULL DEFAULT 'meta',
  whatsapp_access_token VARCHAR(500),
  whatsapp_phone_number_id VARCHAR(100),
  whatsapp_webhook_url VARCHAR(500),
  whatsapp_verify_token VARCHAR(255) NOT NULL DEFAULT 'CVGlobal_WhatsApp_Verify_2024',
  
  -- WhatsApp WAHA configuration
  waha_base_url VARCHAR(500),
  waha_api_key VARCHAR(500),
  waha_session VARCHAR(100) NOT NULL DEFAULT 'default',
  
  -- Telegram configuration
  telegram_bot_token VARCHAR(500),
  telegram_webhook_url VARCHAR(500),
  
  -- Bot behavior settings
  ai_prompt TEXT NOT NULL DEFAULT 'You are a helpful spiritual guide chatbot.',
  journey_duration_days INTEGER NOT NULL DEFAULT 30,
  delivery_interval_minutes INTEGER NOT NULL DEFAULT 10,
  timezone VARCHAR(50),
  scheduled_delivery_time VARCHAR(5),
  language VARCHAR(50) NOT NULL DEFAULT 'English',
  
  -- Customizable messages
  help_message TEXT NOT NULL DEFAULT '🤝 Available Commands:\n\n📖 START - Begin your faith journey\n⏹️ STOP - Pause the journey\n❓ HELP - Show this help message\n👤 HUMAN - Connect with a human counselor\n\nI''m here to guide you through a meaningful spiritual journey. Feel free to ask questions or share your thoughts anytime!',
  stop_message TEXT NOT NULL DEFAULT '⏸️ Your faith journey has been paused.\n\nTake your time whenever you''re ready to continue. Send START to resume your journey, or HUMAN if you''d like to speak with someone.\n\nRemember, this is your personal space for spiritual exploration. There''s no pressure - go at your own pace. 🙏',
  human_message TEXT NOT NULL DEFAULT '👤 Human Support Requested\n\nI''ve flagged your conversation for our human counselors who will respond as soon as possible. They''re trained in spiritual guidance and are here to support you.\n\nIn the meantime, feel free to continue sharing your thoughts or questions. Everything you share is treated with care and confidentiality. 💝',
  completion_message TEXT NOT NULL DEFAULT '🎉 You''ve completed the available journey content!\n\nThank you for taking this journey with us. We hope it has been meaningful and enriching for you.\n\n📱 What would you like to do next?\n\n• Continue exploring with AI-guided conversations\n• Type ''HUMAN'' or ''/human'' to connect with a counselor\n• Type ''START'' or ''/start'' to restart the journey\n\nFeel free to share your thoughts, ask questions, or explore further. I''m here to help! 💬',
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  creator_id INTEGER REFERENCES admin_users(id)
);

CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status);
CREATE INDEX IF NOT EXISTS idx_bots_creator_id ON bots(creator_id);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  bot_id INTEGER REFERENCES bots(id) ON DELETE SET NULL,
  phone_number VARCHAR(20) NOT NULL,
  name VARCHAR(100),
  username VARCHAR(100),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  language_code VARCHAR(10),
  is_premium BOOLEAN,
  
  -- WhatsApp specific fields
  whatsapp_contact_name VARCHAR(100),
  whatsapp_formatted_name VARCHAR(100),
  whatsapp_phone VARCHAR(20),
  
  -- Location data
  country VARCHAR(100),
  region VARCHAR(100),
  city VARCHAR(100),
  timezone VARCHAR(50),
  ip_address VARCHAR(45),
  location_data JSONB,
  
  -- Journey tracking
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  current_day INTEGER NOT NULL DEFAULT 1,
  join_date TIMESTAMPTZ NOT NULL DEFAULT now(),
  completion_date TIMESTAMPTZ,
  tags JSONB DEFAULT '[]'::JSONB,
  
  -- Quiet hours feature
  quiet_hours_enabled BOOLEAN NOT NULL DEFAULT false,
  quiet_hours_start VARCHAR(5),
  quiet_hours_end VARCHAR(5)
);

CREATE INDEX IF NOT EXISTS idx_users_bot_id ON users(bot_id);
CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- Create content table
CREATE TABLE IF NOT EXISTS content (
  id SERIAL PRIMARY KEY,
  bot_id INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
  day_number INTEGER NOT NULL,
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  reflection_question TEXT NOT NULL,
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  
  -- Multimedia fields
  media_type VARCHAR(20) NOT NULL DEFAULT 'text',
  image_filename VARCHAR(255),
  video_filename VARCHAR(255),
  youtube_url VARCHAR(500),
  audio_filename VARCHAR(255),
  
  is_active BOOLEAN NOT NULL DEFAULT true,
  content_type VARCHAR(20) NOT NULL DEFAULT 'daily',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Confirmation button customization
  confirmation_message TEXT,
  yes_button_text VARCHAR(100),
  no_button_text VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_content_bot_id ON content(bot_id);
CREATE INDEX IF NOT EXISTS idx_content_day_number ON content(day_number);
CREATE INDEX IF NOT EXISTS idx_content_bot_day ON content(bot_id, day_number);

-- Create message_logs table
CREATE TABLE IF NOT EXISTS message_logs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  direction VARCHAR(20) NOT NULL,
  raw_text TEXT NOT NULL,
  llm_sentiment VARCHAR(20),
  llm_tags JSONB DEFAULT '[]'::JSONB,
  llm_confidence NUMERIC,
  is_human_handoff BOOLEAN NOT NULL DEFAULT false,
  is_voice_message BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_message_logs_user_id ON message_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_timestamp ON message_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_message_logs_handoff ON message_logs(is_human_handoff) WHERE is_human_handoff = true;

-- Create tag_rules table
CREATE TABLE IF NOT EXISTS tag_rules (
  id SERIAL PRIMARY KEY,
  tag_name VARCHAR(100) NOT NULL,
  description TEXT NOT NULL,
  rule_type VARCHAR(20) NOT NULL DEFAULT 'ai_powered',
  ai_evaluation_rule TEXT,
  rule_config JSONB,
  is_active BOOLEAN NOT NULL DEFAULT true,
  priority INTEGER NOT NULL DEFAULT 0,
  parent_id INTEGER REFERENCES tag_rules(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tag_rules_tag_name ON tag_rules(tag_name);
CREATE INDEX IF NOT EXISTS idx_tag_rules_rule_type ON tag_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_tag_rules_parent_id ON tag_rules(parent_id);
CREATE INDEX IF NOT EXISTS idx_tag_rules_active ON tag_rules(is_active) WHERE is_active = true;

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
  id SERIAL PRIMARY KEY,
  key VARCHAR(100) UNIQUE NOT NULL,
  value TEXT NOT NULL,
  description TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);

-- Enable Row Level Security
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE bots ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE content ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for admin_users
CREATE POLICY "Admin users can view all admin accounts"
  ON admin_users FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Admin users can insert new admin accounts"
  ON admin_users FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Admin users can update admin accounts"
  ON admin_users FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Admin users can delete admin accounts"
  ON admin_users FOR DELETE
  TO authenticated
  USING (true);

-- RLS Policies for bots
CREATE POLICY "Authenticated users can view all bots"
  ON bots FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can create bots"
  ON bots FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update bots"
  ON bots FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete bots"
  ON bots FOR DELETE
  TO authenticated
  USING (true);

-- RLS Policies for users
CREATE POLICY "Authenticated users can view all users"
  ON users FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can create users"
  ON users FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update users"
  ON users FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete users"
  ON users FOR DELETE
  TO authenticated
  USING (true);

-- RLS Policies for content
CREATE POLICY "Authenticated users can view all content"
  ON content FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can create content"
  ON content FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update content"
  ON content FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete content"
  ON content FOR DELETE
  TO authenticated
  USING (true);

-- RLS Policies for message_logs
CREATE POLICY "Authenticated users can view all message logs"
  ON message_logs FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can create message logs"
  ON message_logs FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update message logs"
  ON message_logs FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete message logs"
  ON message_logs FOR DELETE
  TO authenticated
  USING (true);

-- RLS Policies for tag_rules
CREATE POLICY "Authenticated users can view all tag rules"
  ON tag_rules FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can create tag rules"
  ON tag_rules FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update tag rules"
  ON tag_rules FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete tag rules"
  ON tag_rules FOR DELETE
  TO authenticated
  USING (true);

-- RLS Policies for system_settings
CREATE POLICY "Authenticated users can view all system settings"
  ON system_settings FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can create system settings"
  ON system_settings FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update system settings"
  ON system_settings FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete system settings"
  ON system_settings FOR DELETE
  TO authenticated
  USING (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at columns
CREATE TRIGGER update_bots_updated_at
  BEFORE UPDATE ON bots
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_updated_at
  BEFORE UPDATE ON content
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tag_rules_updated_at
  BEFORE UPDATE ON tag_rules
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at
  BEFORE UPDATE ON system_settings
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();