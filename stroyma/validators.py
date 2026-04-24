"""Общие валидаторы для загрузки файлов (размер, расширения)."""
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# Согласовано с DATA_UPLOAD / лимитами в settings
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 50 * 1024 * 1024


@deconstructible
class MaxFileSizeValidator:
    """Проверка максимального размера файла (байт)."""
    def __init__(self, max_bytes: int, message: str = None):
        self.max_bytes = max_bytes
        self.message = message or f'Максимальный размер файла — {max_bytes // (1024 * 1024)} МБ.'

    def __call__(self, value):
        if value and getattr(value, 'size', 0) > self.max_bytes:
            raise ValidationError(self.message, code='file_too_large')

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and self.max_bytes == other.max_bytes
