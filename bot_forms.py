from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, IntegerField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Regexp
from wtforms.widgets import CheckboxInput, ListWidget

class MultiCheckboxField(SelectMultipleField):
    """Custom field for multiple checkboxes"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class CreateBotForm(FlaskForm):
    """Form for creating a new bot"""
    name = StringField('Bot Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    
    # Platform selection
    platforms = MultiCheckboxField(
        'Platforms',
        choices=[('whatsapp', 'WhatsApp'), ('telegram', 'Telegram')],
        validators=[DataRequired(message="Please select at least one platform")]
    )
    
    # WhatsApp configuration
    whatsapp_access_token = StringField('WhatsApp Access Token', validators=[Optional(), Length(max=500)])
    whatsapp_phone_number_id = StringField('WhatsApp Phone Number ID', validators=[Optional(), Length(max=100)])
    whatsapp_webhook_url = StringField('WhatsApp Webhook URL', validators=[Optional(), Length(max=500)])
    whatsapp_verify_token = StringField('WhatsApp Verify Token', validators=[DataRequired(), Length(min=5, max=255)], default='CVGlobal_WhatsApp_Verify_2024')
    
    # Telegram configuration
    telegram_bot_token = StringField('Telegram Bot Token', validators=[Optional(), Length(max=500)])
    telegram_webhook_url = StringField('Telegram Webhook URL', validators=[Optional(), Length(max=500)])
    
    # Bot behavior
    ai_prompt = TextAreaField(
        'AI Personality',
        validators=[DataRequired(), Length(min=10, max=4000)],
        default="""You are a compassionate spiritual guide designed to help people from diverse backgrounds discover Jesus Christ through meaningful, culturally sensitive conversations.

CORE APPROACH:
* Show genuine care and interest in each person's spiritual journey and questions
* Respect their cultural and religious background while introducing Christian teachings
* Use appropriate terminology and references familiar to their background
* Reference credible sources like gotquestions.org, thegospelcoalition.org, desiringgod.org
* Ask thoughtful questions that encourage personal reflection about Jesus Christ
* Guide conversations toward Jesus while addressing their specific concerns and interests

CONVERSATION STYLE:
* Maintain a warm, understanding tone that acknowledges their spiritual search
* Be patient with doubts and questions - engage with them seriously and thoughtfully
* Share relevant Bible stories, scriptures, or spiritual insights when appropriate
* If they ask for prayer, provide prayers they can recite but explain you cannot pray yourself
* Show how Jesus addresses their deepest spiritual longings and life questions

CONTEXTUAL RESPONSES:
* When available, connect your responses to their current daily spiritual content
* Reference their journey stage and today's specific lesson or topic
* Build upon today's content themes to provide deeper spiritual insights
* Use their current content as foundation for exploring related concepts about Jesus

Your goal is to create respectful, meaningful conversations that invite people to seriously consider Jesus Christ while honoring their questions, background, and spiritual journey stage."""
    )
    journey_duration_days = IntegerField(
        'Journey Duration (Days)',
        validators=[DataRequired(), NumberRange(min=1, max=365)],
        default=30
    )
    delivery_interval_minutes = SelectField(
        'Content Delivery Interval',
        choices=[
            ('10', '10 minutes (for testing)'),
            ('1440', '1440 minutes (1 day)'),
            ('2880', '2880 minutes (2 days)')
        ],
        validators=[DataRequired()],
        default='10',
        description="Select how often to check and deliver daily content to users."
    )
    
    # Timezone-based scheduling
    timezone = SelectField(
        'Bot Timezone (Optional)',
        choices=[
            ('', '-- Select Timezone (Optional) --'),
            ('Africa/Cairo', 'Africa/Cairo (GMT+2)'),
            ('Africa/Johannesburg', 'Africa/Johannesburg (GMT+2)'),
            ('Africa/Lagos', 'Africa/Lagos (GMT+1)'),
            ('America/Chicago', 'America/Chicago (GMT-6)'),
            ('America/Los_Angeles', 'America/Los Angeles (GMT-8)'),
            ('America/New_York', 'America/New York (GMT-5)'),
            ('America/Sao_Paulo', 'America/Sao Paulo (GMT-3)'),
            ('Asia/Bangkok', 'Asia/Bangkok (GMT+7)'),
            ('Asia/Dhaka', 'Asia/Dhaka (GMT+6)'),
            ('Asia/Dubai', 'Asia/Dubai (GMT+4)'),
            ('Asia/Hong_Kong', 'Asia/Hong Kong (GMT+8)'),
            ('Asia/Jakarta', 'Asia/Jakarta (GMT+7)'),
            ('Asia/Karachi', 'Asia/Karachi (GMT+5)'),
            ('Asia/Kolkata', 'Asia/Kolkata (GMT+5:30)'),
            ('Asia/Manila', 'Asia/Manila (GMT+8)'),
            ('Asia/Seoul', 'Asia/Seoul (GMT+9)'),
            ('Asia/Shanghai', 'Asia/Shanghai (GMT+8)'),
            ('Asia/Singapore', 'Asia/Singapore (GMT+8)'),
            ('Asia/Tokyo', 'Asia/Tokyo (GMT+9)'),
            ('Australia/Sydney', 'Australia/Sydney (GMT+10)'),
            ('Europe/Amsterdam', 'Europe/Amsterdam (GMT+1)'),
            ('Europe/Berlin', 'Europe/Berlin (GMT+1)'),
            ('Europe/Istanbul', 'Europe/Istanbul (GMT+3)'),
            ('Europe/London', 'Europe/London (GMT+0)'),
            ('Europe/Madrid', 'Europe/Madrid (GMT+1)'),
            ('Europe/Moscow', 'Europe/Moscow (GMT+3)'),
            ('Europe/Paris', 'Europe/Paris (GMT+1)'),
            ('Europe/Rome', 'Europe/Rome (GMT+1)'),
            ('Pacific/Auckland', 'Pacific/Auckland (GMT+12)'),
            ('UTC', 'UTC (GMT+0)')
        ],
        validators=[Optional()],
        description="Select the timezone for scheduled content delivery. Leave empty to use interval-based delivery."
    )
    
    scheduled_delivery_time = SelectField(
        'Scheduled Delivery Time (Optional)',
        choices=[
            ('', '-- Select Time (Optional) --'),
            ('00:00', '00:00 (12:00 AM)'),
            ('01:00', '01:00 (1:00 AM)'),
            ('02:00', '02:00 (2:00 AM)'),
            ('03:00', '03:00 (3:00 AM)'),
            ('04:00', '04:00 (4:00 AM)'),
            ('05:00', '05:00 (5:00 AM)'),
            ('06:00', '06:00 (6:00 AM)'),
            ('07:00', '07:00 (7:00 AM)'),
            ('08:00', '08:00 (8:00 AM)'),
            ('09:00', '09:00 (9:00 AM)'),
            ('10:00', '10:00 (10:00 AM)'),
            ('11:00', '11:00 (11:00 AM)'),
            ('12:00', '12:00 (12:00 PM)'),
            ('13:00', '13:00 (1:00 PM)'),
            ('14:00', '14:00 (2:00 PM)'),
            ('15:00', '15:00 (3:00 PM)'),
            ('16:00', '16:00 (4:00 PM)'),
            ('17:00', '17:00 (5:00 PM)'),
            ('18:00', '18:00 (6:00 PM)'),
            ('19:00', '19:00 (7:00 PM)'),
            ('20:00', '20:00 (8:00 PM)'),
            ('21:00', '21:00 (9:00 PM)'),
            ('22:00', '22:00 (10:00 PM)'),
            ('23:00', '23:00 (11:00 PM)')
        ],
        validators=[Optional()],
        description="Daily delivery time in bot's timezone. Requires timezone to be set."
    )
    
    # Language setting (same as audience_language for consistency)
    language = SelectField('Bot Language', 
                          choices=[
                              ('English', 'English'),
                              ('Arabic', 'Arabic'),
                              ('Bengali', 'Bengali'),
                              ('Bulgarian', 'Bulgarian'),
                              ('Chinese (Simplified)', 'Chinese (Simplified)'),
                              ('Chinese (Traditional)', 'Chinese (Traditional)'),
                              ('Croatian', 'Croatian'),
                              ('Czech', 'Czech'),
                              ('Danish', 'Danish'),
                              ('Dutch', 'Dutch'),
                              ('Estonian', 'Estonian'),
                              ('Farsi', 'Farsi'),
                              ('Finnish', 'Finnish'),
                              ('French', 'French'),
                              ('German', 'German'),
                              ('Greek', 'Greek'),
                              ('Gujarati', 'Gujarati'),
                              ('Hausa', 'Hausa'),
                              ('Hebrew', 'Hebrew'),
                              ('Hindi', 'Hindi'),
                              ('Hungarian', 'Hungarian'),
                              ('Indonesian', 'Indonesian'),
                              ('Italian', 'Italian'),
                              ('Japanese', 'Japanese'),
                              ('Kannada', 'Kannada'),
                              ('Korean', 'Korean'),
                              ('Latvian', 'Latvian'),
                              ('Lithuanian', 'Lithuanian'),
                              ('Malayalam', 'Malayalam'),
                              ('Marathi', 'Marathi'),
                              ('Norwegian', 'Norwegian'),
                              ('Polish', 'Polish'),
                              ('Portuguese', 'Portuguese'),
                              ('Romanian', 'Romanian'),
                              ('Russian', 'Russian'),
                              ('Serbian', 'Serbian'),
                              ('Slovak', 'Slovak'),
                              ('Slovenian', 'Slovenian'),
                              ('Spanish', 'Spanish'),
                              ('Swahili', 'Swahili'),
                              ('Swedish', 'Swedish'),
                              ('Tamil', 'Tamil'),
                              ('Telugu', 'Telugu'),
                              ('Thai', 'Thai'),
                              ('Turkish', 'Turkish'),
                              ('Ukrainian', 'Ukrainian'),
                              ('Urdu', 'Urdu'),
                              ('Vietnamese', 'Vietnamese')
                          ],
                          default="English", 
                          description="Primary language for bot responses and content")
    
    # Customizable command messages
    help_message = TextAreaField(
        'Help Command Message',
        validators=[DataRequired(), Length(min=10, max=1000)],
        default="🤝 Available Commands:\n\n📖 START - Begin your faith journey\n⏹️ STOP - Pause the journey\n❓ HELP - Show this help message\n👤 HUMAN - Connect with a human counselor\n\nI'm here to guide you through a meaningful spiritual journey. Feel free to ask questions or share your thoughts anytime!"
    )
    stop_message = TextAreaField(
        'Stop Command Message',
        validators=[DataRequired(), Length(min=10, max=1000)],
        default="⏸️ Your faith journey has been paused.\n\nTake your time whenever you're ready to continue. Send START to resume your journey, or HUMAN if you'd like to speak with someone.\n\nRemember, this is your personal space for spiritual exploration. There's no pressure - go at your own pace. 🙏"
    )
    human_message = TextAreaField(
        'Human Command Message',
        validators=[DataRequired(), Length(min=10, max=1000)],
        default="👤 Human Support Requested\n\nI've flagged your conversation for our human counselors who will respond as soon as possible. They're trained in spiritual guidance and are here to support you.\n\nIn the meantime, feel free to continue sharing your thoughts or questions. Everything you share is treated with care and confidentiality. 💝"
    )
    completion_message = TextAreaField(
        'Journey Completion Message',
        validators=[DataRequired(), Length(min=10, max=1000)],
        default="🎉 You've completed the available journey content!\n\nThank you for taking this journey with us. We hope it has been meaningful and enriching for you.\n\n📱 What would you like to do next?\n\n• Continue exploring with AI-guided conversations\n• Type 'HUMAN' or '/human' to connect with a counselor\n• Type 'START' or '/start' to restart the journey\n\nFeel free to share your thoughts, ask questions, or explore further. I'm here to help! 💬",
        description="Message shown when users complete all available journey content"
    )
    
    # AI Content Generation Settings
    enable_ai_content_generation = BooleanField('Enable AI Content Generation', default=False)
    content_generation_duration = SelectField(
        'Content Duration',
        choices=[('10', '10 Days'), ('30', '30 Days'), ('90', '90 Days')],
        default='30',
        validators=[Optional()]
    )
    
    # Language and Cultural Templates
    bot_template = SelectField(
        'Bot Template',
        choices=[
            ('english_general', 'English - General Christian Outreach'),
            ('indonesian_muslim', 'Indonesian - Muslim Background (Bang Kris Style)'),
            ('hausa_general', 'Hausa - General Christian Outreach'),
            ('custom', 'Custom - Define your own prompts')
        ],
        default='custom',
        description="Pre-configured templates with culturally appropriate language and messaging"
    )
    
    # Audience and Content Customization
    target_audience = StringField('Target Audience', validators=[Optional(), Length(max=200)], 
                                 description="e.g., Young Muslim adults, Christian seekers, etc.")
    audience_language = SelectField('Audience Language', 
                                   choices=[
                                       ('English', 'English'),
                                       ('Arabic', 'Arabic'),
                                       ('Bengali', 'Bengali'),
                                       ('Bulgarian', 'Bulgarian'),
                                       ('Chinese (Simplified)', 'Chinese (Simplified)'),
                                       ('Chinese (Traditional)', 'Chinese (Traditional)'),
                                       ('Croatian', 'Croatian'),
                                       ('Czech', 'Czech'),
                                       ('Danish', 'Danish'),
                                       ('Dutch', 'Dutch'),
                                       ('Estonian', 'Estonian'),
                                       ('Farsi', 'Farsi'),
                                       ('Finnish', 'Finnish'),
                                       ('French', 'French'),
                                       ('German', 'German'),
                                       ('Greek', 'Greek'),
                                       ('Gujarati', 'Gujarati'),
                                       ('Hausa', 'Hausa'),
                                       ('Hebrew', 'Hebrew'),
                                       ('Hindi', 'Hindi'),
                                       ('Hungarian', 'Hungarian'),
                                       ('Indonesian', 'Indonesian'),
                                       ('Italian', 'Italian'),
                                       ('Japanese', 'Japanese'),
                                       ('Kannada', 'Kannada'),
                                       ('Korean', 'Korean'),
                                       ('Latvian', 'Latvian'),
                                       ('Lithuanian', 'Lithuanian'),
                                       ('Malayalam', 'Malayalam'),
                                       ('Marathi', 'Marathi'),
                                       ('Norwegian', 'Norwegian'),
                                       ('Polish', 'Polish'),
                                       ('Portuguese', 'Portuguese'),
                                       ('Romanian', 'Romanian'),
                                       ('Russian', 'Russian'),
                                       ('Serbian', 'Serbian'),
                                       ('Slovak', 'Slovak'),
                                       ('Slovenian', 'Slovenian'),
                                       ('Spanish', 'Spanish'),
                                       ('Swahili', 'Swahili'),
                                       ('Swedish', 'Swedish'),
                                       ('Tamil', 'Tamil'),
                                       ('Telugu', 'Telugu'),
                                       ('Thai', 'Thai'),
                                       ('Turkish', 'Turkish'),
                                       ('Ukrainian', 'Ukrainian'),
                                       ('Urdu', 'Urdu'),
                                       ('Vietnamese', 'Vietnamese')
                                   ],
                                   default="English", 
                                   description="Primary language for bot responses and content")
    audience_religion = StringField('Current Religion/Background', validators=[Optional(), Length(max=100)], 
                                   description="e.g., Islam, Christianity, Hindu, Secular, etc.")
    audience_age_group = StringField('Age Group', validators=[Optional(), Length(max=50)], 
                                    description="e.g., 18-25, 25-35, Adults, etc.")
    
    # Content Generation Prompt
    content_generation_prompt = TextAreaField(
        'Content Generation Prompt',
        validators=[Optional(), Length(max=2000)],
        default="Create a gentle, respectful faith journey that introduces Christian concepts to someone from a Muslim background. Focus on love, compassion, and spiritual growth. Include reflection questions that encourage personal spiritual exploration.",
        description="Describe the type of content you want to generate. Be specific about tone, topics, and approach."
    )
    
    submit = SubmitField('Create Bot')

class EditBotForm(FlaskForm):
    """Form for editing an existing bot"""
    name = StringField('Bot Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    
    # Platform selection
    platforms = MultiCheckboxField(
        'Platforms',
        choices=[('whatsapp', 'WhatsApp'), ('telegram', 'Telegram')],
        validators=[DataRequired(message="Please select at least one platform")]
    )
    
    # WhatsApp configuration
    whatsapp_access_token = StringField('WhatsApp Access Token', validators=[Optional(), Length(max=500)])
    whatsapp_phone_number_id = StringField('WhatsApp Phone Number ID', validators=[Optional(), Length(max=100)])
    whatsapp_webhook_url = StringField('WhatsApp Webhook URL', validators=[Optional(), Length(max=500)])
    whatsapp_verify_token = StringField('WhatsApp Verify Token', validators=[DataRequired(), Length(min=5, max=255)], default='CVGlobal_WhatsApp_Verify_2024')
    
    # Telegram configuration
    telegram_bot_token = StringField('Telegram Bot Token', validators=[Optional(), Length(max=500)])
    telegram_webhook_url = StringField('Telegram Webhook URL', validators=[Optional(), Length(max=500)])
    
    # Language and Cultural Templates
    bot_template = SelectField(
        'Bot Template',
        choices=[
            ('english_general', 'English - General Christian Outreach'),
            ('indonesian_muslim', 'Indonesian - Muslim Background (Bang Kris Style)'),
            ('hausa_general', 'Hausa - General Christian Outreach'),
            ('custom', 'Custom - Define your own prompts')
        ],
        default='custom',
        description="Pre-configured templates with culturally appropriate language and messaging"
    )
    
    # Bot behavior
    ai_prompt = TextAreaField(
        'AI Personality',
        validators=[DataRequired(), Length(min=10, max=2000)]
    )
    journey_duration_days = IntegerField(
        'Journey Duration (Days)',
        validators=[DataRequired(), NumberRange(min=1, max=365)]
    )
    delivery_interval_minutes = SelectField(
        'Content Delivery Interval',
        choices=[
            ('10', '10 minutes (for testing)'),
            ('1440', '1440 minutes (1 day)'),
            ('2880', '2880 minutes (2 days)')
        ],
        validators=[DataRequired()],
        description="Select how often to check and deliver daily content to users."
    )
    
    # Timezone-based scheduling
    timezone = SelectField(
        'Bot Timezone (Optional)',
        choices=[
            ('', '-- Select Timezone (Optional) --'),
            ('Africa/Cairo', 'Africa/Cairo (GMT+2)'),
            ('Africa/Johannesburg', 'Africa/Johannesburg (GMT+2)'),
            ('Africa/Lagos', 'Africa/Lagos (GMT+1)'),
            ('America/Chicago', 'America/Chicago (GMT-6)'),
            ('America/Los_Angeles', 'America/Los Angeles (GMT-8)'),
            ('America/New_York', 'America/New York (GMT-5)'),
            ('America/Sao_Paulo', 'America/Sao Paulo (GMT-3)'),
            ('Asia/Bangkok', 'Asia/Bangkok (GMT+7)'),
            ('Asia/Dhaka', 'Asia/Dhaka (GMT+6)'),
            ('Asia/Dubai', 'Asia/Dubai (GMT+4)'),
            ('Asia/Hong_Kong', 'Asia/Hong Kong (GMT+8)'),
            ('Asia/Jakarta', 'Asia/Jakarta (GMT+7)'),
            ('Asia/Karachi', 'Asia/Karachi (GMT+5)'),
            ('Asia/Kolkata', 'Asia/Kolkata (GMT+5:30)'),
            ('Asia/Manila', 'Asia/Manila (GMT+8)'),
            ('Asia/Seoul', 'Asia/Seoul (GMT+9)'),
            ('Asia/Shanghai', 'Asia/Shanghai (GMT+8)'),
            ('Asia/Singapore', 'Asia/Singapore (GMT+8)'),
            ('Asia/Tokyo', 'Asia/Tokyo (GMT+9)'),
            ('Australia/Sydney', 'Australia/Sydney (GMT+10)'),
            ('Europe/Amsterdam', 'Europe/Amsterdam (GMT+1)'),
            ('Europe/Berlin', 'Europe/Berlin (GMT+1)'),
            ('Europe/Istanbul', 'Europe/Istanbul (GMT+3)'),
            ('Europe/London', 'Europe/London (GMT+0)'),
            ('Europe/Madrid', 'Europe/Madrid (GMT+1)'),
            ('Europe/Moscow', 'Europe/Moscow (GMT+3)'),
            ('Europe/Paris', 'Europe/Paris (GMT+1)'),
            ('Europe/Rome', 'Europe/Rome (GMT+1)'),
            ('Pacific/Auckland', 'Pacific/Auckland (GMT+12)'),
            ('UTC', 'UTC (GMT+0)')
        ],
        validators=[Optional()],
        description="Select the timezone for scheduled content delivery. Leave empty to use interval-based delivery."
    )
    
    scheduled_delivery_time = SelectField(
        'Scheduled Delivery Time (Optional)',
        choices=[
            ('', '-- Select Time (Optional) --'),
            ('00:00', '00:00 (12:00 AM)'),
            ('01:00', '01:00 (1:00 AM)'),
            ('02:00', '02:00 (2:00 AM)'),
            ('03:00', '03:00 (3:00 AM)'),
            ('04:00', '04:00 (4:00 AM)'),
            ('05:00', '05:00 (5:00 AM)'),
            ('06:00', '06:00 (6:00 AM)'),
            ('07:00', '07:00 (7:00 AM)'),
            ('08:00', '08:00 (8:00 AM)'),
            ('09:00', '09:00 (9:00 AM)'),
            ('10:00', '10:00 (10:00 AM)'),
            ('11:00', '11:00 (11:00 AM)'),
            ('12:00', '12:00 (12:00 PM)'),
            ('13:00', '13:00 (1:00 PM)'),
            ('14:00', '14:00 (2:00 PM)'),
            ('15:00', '15:00 (3:00 PM)'),
            ('16:00', '16:00 (4:00 PM)'),
            ('17:00', '17:00 (5:00 PM)'),
            ('18:00', '18:00 (6:00 PM)'),
            ('19:00', '19:00 (7:00 PM)'),
            ('20:00', '20:00 (8:00 PM)'),
            ('21:00', '21:00 (9:00 PM)'),
            ('22:00', '22:00 (10:00 PM)'),
            ('23:00', '23:00 (11:00 PM)')
        ],
        validators=[Optional()],
        description="Daily delivery time in bot's timezone. Requires timezone to be set."
    )
    
    # Language setting
    language = SelectField('Bot Language', 
                          choices=[
                              ('English', 'English'),
                              ('Arabic', 'Arabic'),
                              ('Bengali', 'Bengali'),
                              ('Bulgarian', 'Bulgarian'),
                              ('Chinese (Simplified)', 'Chinese (Simplified)'),
                              ('Chinese (Traditional)', 'Chinese (Traditional)'),
                              ('Croatian', 'Croatian'),
                              ('Czech', 'Czech'),
                              ('Danish', 'Danish'),
                              ('Dutch', 'Dutch'),
                              ('Estonian', 'Estonian'),
                              ('Farsi', 'Farsi'),
                              ('Finnish', 'Finnish'),
                              ('French', 'French'),
                              ('German', 'German'),
                              ('Greek', 'Greek'),
                              ('Gujarati', 'Gujarati'),
                              ('Hausa', 'Hausa'),
                              ('Hebrew', 'Hebrew'),
                              ('Hindi', 'Hindi'),
                              ('Hungarian', 'Hungarian'),
                              ('Indonesian', 'Indonesian'),
                              ('Italian', 'Italian'),
                              ('Japanese', 'Japanese'),
                              ('Kannada', 'Kannada'),
                              ('Korean', 'Korean'),
                              ('Latvian', 'Latvian'),
                              ('Lithuanian', 'Lithuanian'),
                              ('Malayalam', 'Malayalam'),
                              ('Marathi', 'Marathi'),
                              ('Norwegian', 'Norwegian'),
                              ('Polish', 'Polish'),
                              ('Portuguese', 'Portuguese'),
                              ('Romanian', 'Romanian'),
                              ('Russian', 'Russian'),
                              ('Serbian', 'Serbian'),
                              ('Slovak', 'Slovak'),
                              ('Slovenian', 'Slovenian'),
                              ('Spanish', 'Spanish'),
                              ('Swahili', 'Swahili'),
                              ('Swedish', 'Swedish'),
                              ('Tamil', 'Tamil'),
                              ('Telugu', 'Telugu'),
                              ('Thai', 'Thai'),
                              ('Turkish', 'Turkish'),
                              ('Ukrainian', 'Ukrainian'),
                              ('Urdu', 'Urdu'),
                              ('Vietnamese', 'Vietnamese')
                          ],
                          default="English", 
                          description="Primary language for bot responses and content")
    
    # Customizable command messages
    help_message = TextAreaField(
        'Help Command Message',
        validators=[DataRequired(), Length(min=10, max=1000)]
    )
    stop_message = TextAreaField(
        'Stop Command Message',
        validators=[DataRequired(), Length(min=10, max=1000)]
    )
    human_message = TextAreaField(
        'Human Command Message',
        validators=[DataRequired(), Length(min=10, max=1000)]
    )
    completion_message = TextAreaField(
        'Journey Completion Message',
        validators=[DataRequired(), Length(min=10, max=1000)],
        description="Message shown when users complete all available journey content"
    )
    
    
    # Status
    status = BooleanField('Active')
    
    submit = SubmitField('Update Bot')

class BotContentForm(FlaskForm):
    """Form for creating bot-specific content"""
    day_number = IntegerField('Day Number', validators=[DataRequired(), NumberRange(min=1, max=365)])
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=200)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=10, max=5000)])
    reflection_question = TextAreaField('Reflection Question', validators=[DataRequired(), Length(min=10, max=1000)])
    
    tags = MultiCheckboxField(
        'Tags',
        choices=[
            ('Bible Exposure', 'Bible Exposure'),
            ('Christian Learning', 'Christian Learning'),
            ('Bible Engagement', 'Bible Engagement'),
            ('Salvation Prayer', 'Salvation Prayer'),
            ('Gospel Presentation', 'Gospel Presentation'),
            ('Prayer', 'Prayer'),
            ('Introduction to Jesus', 'Introduction to Jesus'),
            ('Holy Spirit Empowerment', 'Holy Spirit Empowerment')
        ]
    )
    
    media_type = SelectMultipleField(
        'Media Type',
        choices=[('text', 'Text Only'), ('image', 'Image'), ('video', 'Video'), ('audio', 'Audio')],
        default=['text']
    )
    
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Content')