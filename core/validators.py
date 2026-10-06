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


def optimize_image(file_obj, max_dimension=1920, quality=85):
    """
    ضغط وتحسين الصورة المرفوعة لتقليل حجمها:
    - تصغير الأبعاد إذا تجاوزت max_dimension
    - ضغط الجودة إلى quality%
    - تحويل PNG الكبيرة إلى JPEG إذا لم تحتوي على شفافية
    """
    if not file_obj:
        return file_obj
    
    try:
        import io
        curr_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        img = Image.open(file_obj)
        
        # لا نعالج الصور الصغيرة (أقل من 200KB)
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(curr_pos)
        if file_size < 200 * 1024:
            return file_obj
        
        # تصغير الأبعاد إذا كانت كبيرة
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # تحديد صيغة الإخراج
        output_format = img.format or 'JPEG'
        if output_format == 'PNG' and img.mode != 'RGBA':
            output_format = 'JPEG'
        
        if output_format == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # حفظ الصورة المضغوطة
        buffer = io.BytesIO()
        save_kwargs = {'optimize': True}
        if output_format in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
        img.save(buffer, format=output_format, **save_kwargs)
        buffer.seek(0)
        
        # تحديث ملف الرفع
        from django.core.files.uploadedfile import InMemoryUploadedFile
        ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}
        ext = ext_map.get(output_format, '.jpg')
        
        optimized = InMemoryUploadedFile(
            file=buffer,
            field_name=getattr(file_obj, 'field_name', 'image'),
            name=os.path.splitext(file_obj.name)[0] + ext,
            content_type=f'image/{output_format.lower()}',
            size=buffer.getbuffer().nbytes,
            charset=None,
        )
        return optimized
    except Exception:
        # إذا فشل الضغط، نعيد الملف الأصلي
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        return file_obj
