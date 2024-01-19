from flask_wtf import FlaskForm
from wtforms import FileField
from wtforms.validators import DataRequired


class UploadForm(FlaskForm):
    content_image = FileField('content_file', validators=[DataRequired()])
    style_image = FileField('style_image', validators=[DataRequired()])
