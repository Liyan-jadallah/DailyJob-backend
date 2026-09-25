import os
from django.core.exceptions import ValidationError
from rest_framework import serializers
from PIL import Image

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

def validate_image_file(file_obj):
    """
    Validates an uploaded image file:
    - Checks file size (max 5MB)
    - Checks file extension
    - Verifies MIME type from file content
    - Verifies image integrity using PIL
    """
    if not file_obj:
        return file_obj

    # 1. Check size
    if file_obj.size > MAX_IMAGE_SIZE_BYTES:
        raise serializers.ValidationError(
            f"حجم الصورة يتجاوز الحد المسموح ({MAX_IMAGE_SIZE_MB} ميغابايت)."
        )

    # 2. Check extension
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            f"نوع الملف غير مدعوم ({ext}). الصيغ المدعومة هي: JPG, PNG, WEBP فقط."
        )

    # 3. Verify actual image format and MIME type via PIL
    try:
        # Save position, verify, and restore
        curr_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        img = Image.open(file_obj)
        detected_format = img.format
        img.verify()
        if hasattr(file_obj, 'seek'):
            file_obj.seek(curr_pos)

        # Map PIL format to MIME type
        format_to_mime = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'WEBP': 'image/webp',
        }
        detected_mime = format_to_mime.get(detected_format)
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                "محتوى الملف لا يطابق صيغة صورة مدعومة. الصيغ المدعومة هي: JPG, PNG, WEBP فقط."
            )
    except serializers.ValidationError:
        raise
    except Exception:
        raise serializers.ValidationError("الملف المرفوع تالف أو ليس صورة صالحة.")

    return file_obj
