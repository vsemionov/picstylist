import os

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import RadioField, IntegerRangeField
from wtforms.validators import NumberRange, StopValidation


from . import settings
from . import images


formatted_formats = ' and '.join([', '.join(settings.ALLOWED_FORMATS[:-1]), settings.ALLOWED_FORMATS[-1]])


class ImageValidator:
    def __init__(self, max_resolution):
        self.max_resolution = max_resolution

    def __call__(self, form, field):
        fmt, (width, height) = images.get_image_dimensions(field.data)
        if any(v is None for v in [fmt, width, height]):
            raise StopValidation('Invalid or corrupt image.')
        if fmt not in settings.ALLOWED_FORMATS:
            raise StopValidation(f'Unsupported image format. We support {formatted_formats}.')
        if width * height > self.max_resolution * 1024 * 1024:
            raise StopValidation('Image resolution too high. '
                f'The maximum acceptable resolution is {self.max_resolution} MP.')


class UploadForm(FlaskForm):
    __image_validators = [
        FileRequired(),
        FileAllowed(settings.ALLOWED_EXTENSIONS, message=f'Unsupported file type. We support {formatted_formats}.'),
        ImageValidator(settings.MAX_RESOLUTION_MP)
    ]

    content_image = FileField('Original image', validators=__image_validators)
    style_image = FileField('Style image', validators=__image_validators)
    model = RadioField('Model', choices=[('fast', 'Fast'), ('iterative', 'Iterative')], default='fast')
    strength = IntegerRangeField('Strength', default=settings.DEFAULT_STRENGTH, validators=[NumberRange(1, 100)])

    def validate(self, extra_validators=None):
        if not super().validate():
            return False

        upload_size = 0
        for f in [self.content_image.data, self.style_image.data]:
            f.seek(0, os.SEEK_END)
            upload_size += f.tell()
            f.seek(0)
        if upload_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            self.form_errors.append(f'Total upload size too large. We accept at most {settings.MAX_UPLOAD_SIZE_MB} MB.')
            return False

        return True


class CancelForm(FlaskForm):
    pass
