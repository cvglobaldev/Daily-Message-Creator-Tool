from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, TextAreaField, URLField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from models import AdminUser, db

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('super_admin', 'Super Admin')], default='admin')
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = AdminUser.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, email):
        user = AdminUser.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('super_admin', 'Super Admin')])
    is_active = BooleanField('Active')
    submit = SubmitField('Update User')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField('Repeat New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class ContentForm(FlaskForm):
    """Form for creating and editing multimedia content"""
    bot_id = SelectField('Bot', coerce=int, validators=[Optional()])  # For bot-specific content isolation
    day_number = SelectField('Day Number', coerce=int, validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=200)])
    content = TextAreaField('Content', validators=[DataRequired()], render_kw={"rows": 8})
    reflection_question = TextAreaField('Reflection Question', validators=[DataRequired()], render_kw={"rows": 3})
    
    # Media type selection
    media_type = SelectField('Media Type', 
                           choices=[('text', 'Text Only'), 
                                   ('image', 'Text + Image'), 
                                   ('video', 'Text + Video Upload'), 
                                   ('audio', 'Text + Audio File')], 
                           validators=[DataRequired()], default='text')
    
    # File uploads
    image_file = FileField('Upload Image', 
                          validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                                    'Only image files (jpg, jpeg, png, gif) are allowed!')])
    
    video_file = FileField('Upload Video', 
                          validators=[Optional(), 
                                    FileAllowed(['mp4', 'mov', 'avi', 'mkv', 'webm'], 
                                              'Only video files (mp4, mov, avi, mkv, webm) are allowed!'),
                                    FileSize(max_size=200*1024*1024, message='Video file size must be less than 200MB')])
    
    audio_file = FileField('Upload Audio File', 
                          validators=[Optional(), FileAllowed(['mp3', 'wav', 'ogg', 'm4a'], 
                                    'Only audio files (mp3, wav, ogg, m4a) are allowed!')])
    
    # YouTube URL (deprecated but kept for backwards compatibility)
    youtube_url = URLField('YouTube URL', validators=[Optional()])
    
    # Faith journey tags (multi-select will be handled in template)
    tags = StringField('Faith Journey Tags (comma-separated)', 
                      description='Choose from: Bible Exposure, Christian Learning, Bible Engagement, Salvation Prayer, Gospel Presentation, Prayer, Introduction to Jesus, Holy Spirit Empowerment')
    
    is_active = BooleanField('Active', default=True)
    
    # AI Content Generation Settings
    enable_ai_content_generation = BooleanField('Enable AI Content Generation', default=False)
    content_generation_duration = SelectField(
        'Content Duration',
        choices=[('10', '10 Days'), ('30', '30 Days'), ('90', '90 Days')],
        default='30',
        validators=[Optional()]
    )
    
    # Audience and Content Customization
    target_audience = StringField('Target Audience', validators=[Optional(), Length(max=200)], 
                                 description="e.g., Young Muslim adults, Christian seekers, etc.")
    audience_language = SelectField('Audience Language', 
                                   choices=[
                                       ('English', 'English'),
                                       ('Indonesian', 'Bahasa Indonesia'),
                                       ('Spanish', 'Spanish'),
                                       ('Other', 'Other (specify in content prompt)')
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
    
    # Confirmation Button Customization
    confirmation_message = TextAreaField(
        'Confirmation Message', 
        validators=[Optional(), Length(max=500)],
        render_kw={"rows": 2, "placeholder": "Leave blank for default message. E.g., 'Have you read today's message?'"},
        description="Custom message asking if user has read the content. Leave blank to use default."
    )
    yes_button_text = StringField(
        'Yes Button Text',
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Leave blank for default. E.g., 'Yes, I've read it'"},
        description="Custom text for the 'Yes' button. Leave blank to use default."
    )
    no_button_text = StringField(
        'No Button Text',
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Leave blank for default. E.g., 'Not yet'"},
        description="Custom text for the 'No' button. Leave blank to use default."
    )
    
    submit = SubmitField('Save Content')

class AIContentGenerationForm(FlaskForm):
    """Form for AI content generation setup"""
    content_generation_duration = SelectField(
        'Content Duration',
        choices=[('10', '10 Days'), ('30', '30 Days'), ('60', '60 Days'), ('90', '90 Days')],
        default='30',
        validators=[DataRequired()]
    )
    
    # Audience and Content Customization
    target_audience = StringField('Target Audience', validators=[Optional(), Length(max=200)], 
                                 description="e.g., Young Muslim adults, Christian seekers, etc.")
    audience_language = SelectField('Audience Language', 
                                   choices=[
                                       ('English', 'English'),
                                       ('Indonesian', 'Bahasa Indonesia'),
                                       ('Spanish', 'Spanish'),
                                       ('Other', 'Other (specify in content prompt)')
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
        validators=[DataRequired(), Length(max=2000)],
        default="Create a gentle, respectful faith journey that introduces Christian concepts to someone from a Muslim background. Focus on love, compassion, and spiritual growth. Include reflection questions that encourage personal spiritual exploration.",
        description="Describe the type of content you want to generate. Be specific about tone, topics, and approach."
    )
    
    submit = SubmitField('Generate Content')

class TagRuleForm(FlaskForm):
    """Form for creating and editing custom tagging rules with hierarchical support"""
    tag_name = StringField('Tag Name', 
                          validators=[DataRequired(), Length(min=2, max=100)],
                          description="Name of the tag (e.g., 'Prayer Response', 'Bible Interest', 'Spiritual Growth')")
    
    parent_id = SelectField('Parent Tag (Optional)', 
                           coerce=lambda x: int(x) if x and x != '' else None,
                           choices=[],
                           validators=[Optional()],
                           description="Select a parent tag to create a sub-tag, or leave empty for a main tag")
    
    description = TextAreaField('Description', 
                               validators=[DataRequired(), Length(min=10, max=500)],
                               render_kw={"rows": 3},
                               description="Describe when this tag should be applied")
    
    ai_evaluation_rule = TextAreaField('AI Evaluation Rule', 
                                      validators=[DataRequired(), Length(min=20, max=1000)],
                                      render_kw={"rows": 6},
                                      description="Write a clear instruction for the AI about when to apply this tag. Example: 'Apply this tag when the user mentions praying, asking for prayer, or expressing interest in prayer'")
    
    priority = SelectField('Priority', 
                          coerce=int,
                          choices=[(0, 'Low'), (5, 'Medium'), (10, 'High')],
                          default=5,
                          description="Higher priority tags are checked first")
    
    is_active = BooleanField('Active', default=True, description="Only active tags are used for analysis")
    
    submit = SubmitField('Save Tag Rule')