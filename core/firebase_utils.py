import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

import json
import logging

logger = logging.getLogger(__name__)

def _ensure_firebase_app():
    """التحقق من تهيئة Firebase Admin SDK مع دعم كافة المسارات والمتغيرات البيئية"""
    if firebase_admin._apps:
        return True
    try:
        firebase_json_env = os.getenv('FIREBASE_CREDENTIALS_JSON', '').strip()
        if firebase_json_env:
            try:
                cred_dict = json.loads(firebase_json_env)
            except Exception:
                import base64
                cred_dict = json.loads(base64.b64decode(firebase_json_env).decode('utf-8'))

            # معالجة مشكلة الـ newlines في private_key إذا تم تمريرها كنص مع \\n
            if isinstance(cred_dict, dict) and 'private_key' in cred_dict:
                if '\\n' in cred_dict['private_key']:
                    cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')

            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Successfully initialized Firebase Admin SDK from FIREBASE_CREDENTIALS_JSON env.")
            return True

        possible_paths = [
            os.getenv('FIREBASE_CRED_PATH', ''),
            '/etc/secrets/firebase-adminsdk.json',  # مسار Render Secret Files الافتراضي
            os.path.join(settings.BASE_DIR, 'firebase-adminsdk.json'),
            os.path.join(getattr(settings, 'BASE_DIR', ''), 'backend', 'firebase-adminsdk.json'),
            os.path.join(getattr(settings, 'BASE_DIR', '').parent if hasattr(settings.BASE_DIR, 'parent') else '', 'firebase-adminsdk.json'),
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                cred = credentials.Certificate(path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Successfully initialized Firebase Admin SDK from {path}.")
                return True

        logger.warning("Firebase credentials not found (checked FIREBASE_CREDENTIALS_JSON and all file paths).")
        return False
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin: {e}", exc_info=True)
        return False

# محاولة التهيئة عند التحميل
_ensure_firebase_app()

def send_push_notification(user, title, body, data=None, badge_count=1):
    """
    إرسال إشعار دفع (Push Notification) لجهاز مستخدم معين عبر FCM
    """
    if not user.fcm_token:
        logger.info(f"User {user.username} doesn't have an FCM token. Skipping push.")
        return False

    if not _ensure_firebase_app():
        logger.warning("Cannot send push: Firebase Admin is not initialized.")
        return False

    try:
        # تجهيز بيانات إضافية للتطبيق إن وُجدت
        extra_data = data or {}
        fcm_data = {str(k): str(v) for k, v in extra_data.items()}

        android_cfg = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='daily_job_channel',
                sound='default',
                default_sound=True,
                default_vibrate_timings=True,
            )
        )
        apns_cfg = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=badge_count)
            )
        )

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=fcm_data,
            android=android_cfg,
            apns=apns_cfg,
            token=user.fcm_token,
        )

        response = messaging.send(message)
        logger.info(f"FCM message sent successfully to user {user.username}. Response ID: {response}")
        return True
    except messaging.UnregisteredError:
        logger.info(f"FCM token expired for user {user.username}. Clearing token.")
        user.fcm_token = ''
        user.save(update_fields=['fcm_token'])
        return False
    except Exception as e:
        logger.warning(f"Failed to send FCM message to user {user.username}: {e}")
        return False

def send_topic_notification(topic, title, body, data=None, badge_count=1):
    """
    إرسال إشعار دفع (Push Notification) لموضوع معين (Topic) في FCM
    """
    if not _ensure_firebase_app():
        logger.warning("Cannot send topic push: Firebase Admin is not initialized.")
        return False

    try:
        extra_data = data or {}
        fcm_data = {str(k): str(v) for k, v in extra_data.items()}

        android_cfg = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='daily_job_channel',
                sound='default',
                default_sound=True,
                default_vibrate_timings=True,
            )
        )
        apns_cfg = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=badge_count)
            )
        )

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=fcm_data,
            android=android_cfg,
            apns=apns_cfg,
            topic=topic,
        )

        response = messaging.send(message)
        logger.info(f"FCM message sent successfully to topic {topic}. Response ID: {response}")
        return True
    except Exception as e:
        logger.warning(f"Failed to send FCM message to topic {topic}: {e}")
        return False


def send_multicast_push_notification(tokens, title, body, data=None, badge_count=1):
    """
    إرسال إشعار دفع (Push Notification) لمجموعة من التوكنات بكفاءة
    """
    if not tokens:
        return False
    valid_tokens = list({t.strip() for t in tokens if t and t.strip()})
    if not valid_tokens:
        return False
    if not _ensure_firebase_app():
        logger.warning("Cannot send multicast push: Firebase Admin is not initialized.")
        return False

    try:
        extra_data = data or {}
        fcm_data = {str(k): str(v) for k, v in extra_data.items()}

        android_cfg = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='daily_job_channel',
                sound='default',
                default_sound=True,
                default_vibrate_timings=True,
            )
        )
        apns_cfg = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=badge_count)
            )
        )

        chunk_size = 500
        for i in range(0, len(valid_tokens), chunk_size):
            chunk = valid_tokens[i:i + chunk_size]
            multicast_message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=fcm_data,
                android=android_cfg,
                apns=apns_cfg,
                tokens=chunk,
            )
            response = messaging.send_each_for_multicast(multicast_message)
            logger.info(f"FCM multicast sent to {len(chunk)} devices: {response.success_count} success, {response.failure_count} failures.")
        return True
    except Exception as e:
        logger.warning(f"Failed to send FCM multicast message: {e}")
        return False


