from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
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
        'AI Prompt',
        validators=[DataRequired(), Length(min=10, max=2000)],
        default="You are a helpful spiritual guide chatbot that helps users on their faith journey. Be compassionate, understanding, and provide thoughtful responses based on their spiritual questions and reflections."
    )
    journey_duration_days = IntegerField(
        'Journey Duration (Days)',
        validators=[DataRequired(), NumberRange(min=1, max=365)],
        default=30
    )
    delivery_interval_minutes = IntegerField(
        'Content Delivery Interval (Minutes)',
        validators=[DataRequired(), NumberRange(min=1, max=1440)],
        default=10,
        description="How often to deliver daily content (1-1440 minutes). Default: 10 minutes for testing, 1440 for daily delivery."
    )
    
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
    
    # Bot behavior
    ai_prompt = TextAreaField(
        'AI Prompt',
        validators=[DataRequired(), Length(min=10, max=2000)]
    )
    journey_duration_days = IntegerField(
        'Journey Duration (Days)',
        validators=[DataRequired(), NumberRange(min=1, max=365)]
    )
    delivery_interval_minutes = IntegerField(
        'Content Delivery Interval (Minutes)',
        validators=[DataRequired(), NumberRange(min=1, max=1440)],
        description="How often to deliver daily content (1-1440 minutes). Default: 10 minutes for testing, 1440 for daily delivery."
    )
    
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