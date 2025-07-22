from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
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
    day_number = SelectField('Day Number', coerce=int, validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=200)])
    content = TextAreaField('Content', validators=[DataRequired()], render_kw={"rows": 8})
    reflection_question = TextAreaField('Reflection Question', validators=[DataRequired()], render_kw={"rows": 3})
    
    # Media type selection
    media_type = SelectField('Media Type', 
                           choices=[('text', 'Text Only'), 
                                   ('image', 'Text + Image'), 
                                   ('video', 'Text + YouTube Video'), 
                                   ('audio', 'Text + Audio File')], 
                           validators=[DataRequired()], default='text')
    
    # File uploads
    image_file = FileField('Upload Image', 
                          validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                                    'Only image files (jpg, jpeg, png, gif) are allowed!')])
    
    audio_file = FileField('Upload Audio File', 
                          validators=[Optional(), FileAllowed(['mp3', 'wav', 'ogg', 'm4a'], 
                                    'Only audio files (mp3, wav, ogg, m4a) are allowed!')])
    
    # YouTube URL
    youtube_url = URLField('YouTube URL', validators=[Optional()])
    
    # Faith journey tags (multi-select will be handled in template)
    tags = StringField('Faith Journey Tags (comma-separated)', 
                      description='Choose from: Bible Exposure, Christian Learning, Bible Engagement, Salvation Prayer, Gospel Presentation, Prayer, Introduction to Jesus, Holy Spirit Empowerment')
    
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Content')
    
    def __init__(self, day_choices=None, *args, **kwargs):
        super(ContentForm, self).__init__(*args, **kwargs)
        if day_choices:
            self.day_number.choices = [(i, f'Day {i}') for i in day_choices]
        else:
            # Default to 1-90 days
            self.day_number.choices = [(i, f'Day {i}') for i in range(1, 91)]