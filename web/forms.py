import os

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import StopValidation


from . import settings
from . import images


class ImageValidator:
    def __init__(self, max_resolution):
        self.max_resolution = max_resolution

    def __call__(self, form, field):
        fmt, size = images.get_image_dimensions(field.data, self.max_resolution)
        width, height = size
        if any(v is None for v in [fmt, width, height]):
            raise StopValidation('Invalid or corrupt image.')
        if fmt not in settings.ALLOWED_FORMATS:
            raise StopValidation(f'Unsupported image format. We support JPEG and PNG only.')
        if width * height > self.max_resolution * 1024 * 1024:
            raise StopValidation('Image resolution too high. '
                f'The maximum allowed resolution is {self.max_resolution} MP.')


validators = [
    FileRequired(),
    FileAllowed(settings.ALLOWED_EXTENSIONS, message='Unsupported file type. We support JPEG and PNG only.'),
    ImageValidator(settings.MAX_RESOLUTION_MP)
]


class UploadForm(FlaskForm):
    content_image = FileField('Original image', validators=[FileRequired()])
    style_image = FileField('Style image', validators=[FileRequired()])

    def validate(self, extra_validators = None):
        if not super().validate():
            return False

        upload_size = 0
        for f in [self.content_image.data, self.style_image.data]:
            f.seek(0, os.SEEK_END)
            upload_size += f.tell()
            f.seek(0)
        if upload_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            self.form_errors.append(f'Combined file size too large (max {settings.MAX_UPLOAD_SIZE_MB} MB).')
            return False

        return True
