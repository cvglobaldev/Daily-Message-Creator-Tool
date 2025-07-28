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