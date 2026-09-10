import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

import json

# مسار ملف المصادقة الخاص بـ Firebase Admin SDK أو المتغير البيئي
cred_path = os.getenv('FIREBASE_CRED_PATH', os.path.join(settings.BASE_DIR, 'firebase-adminsdk.json'))
firebase_json_env = os.getenv('FIREBASE_CREDENTIALS_JSON')

# تهيئة تطبيق فايربيس مرة واحدة فقط
if not firebase_admin._apps:
    try:
        if firebase_json_env:
            cred_dict = json.loads(firebase_json_env)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("Successfully initialized Firebase Admin SDK from FIREBASE_CREDENTIALS_JSON env.")
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Successfully initialized Firebase Admin SDK from file.")
        else:
            print(f"Firebase credential file not found at {cred_path} and FIREBASE_CREDENTIALS_JSON not set.")
    except Exception as e:
        print(f"Error initializing Firebase Admin: {e}")

def send_push_notification(user, title, body, data=None, badge_count=1):
    """
    إرسال إشعار دفع (Push Notification) لجهاز مستخدم معين عبر FCM
    """
    if not user.fcm_token:
        print(f"User {user.username} doesn't have an FCM token. Skipping push.")
        return False
    
    try:
        # تجهيز بيانات إضافية للتطبيق إن وُجدت
        extra_data = data or {}
        # تحويل كل القيم في dict إلى strings لأن FCM لا يقبل غيرها في الـ data payload
        fcm_data = {str(k): str(v) for k, v in extra_data.items()}

        android_cfg = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='daily_job_channel',
                sound='default',
                default_sound=True,
                default_vibrate_timings=True,
                icon='launcher_icon',
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
        print(f"FCM message sent successfully to user {user.username}. Response ID: {response}")
        return True
    except Exception as e:
        print(f"Failed to send FCM message to user {user.username}: {e}")
        return False

def send_topic_notification(topic, title, body, data=None, badge_count=1):
    """
    إرسال إشعار دفع (Push Notification) لموضوع معين (Topic) في FCM
    """
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
                icon='launcher_icon',
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
        print(f"FCM message sent successfully to topic {topic}. Response ID: {response}")
        return True
    except Exception as e:
        print(f"Failed to send FCM message to topic {topic}: {e}")
        return False

