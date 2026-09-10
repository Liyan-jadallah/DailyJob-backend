import os
import re
import json
import base64
import logging
import urllib.request
import urllib.error
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend

logger = logging.getLogger(__name__)


def _parse_sender(raw_sender):
    """
    Parses 'Name <email@example.com>' or 'email@example.com' into (name, email).
    """
    if not raw_sender:
        raw_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'dailyjob2026@gmail.com')
    match = re.match(r'^(.*?)\s*<(.+?)>$', raw_sender)
    if match:
        name = match.group(1).strip(' "\'') or 'Daily Job'
        email = match.group(2).strip()
        return name, email
    return 'Daily Job', raw_sender.strip()


class HttpApiEmailBackend(BaseEmailBackend):
    """
    Django Email Backend that sends emails via HTTPS API (Brevo or Resend) on port 443.
    This completely eliminates connection timeouts and 500 errors caused by cloud hosts
    (such as Render free tier) blocking outgoing SMTP ports (25, 465, 587).

    Loading priority:
      1. Brevo HTTP API  (if BREVO_API_KEY is configured)
      2. Resend HTTP API (if RESEND_API_KEY is configured)
      3. Fallback to standard Django SMTP EmailBackend
    """

    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brevo_api_key = (
            getattr(settings, 'BREVO_API_KEY', None) or os.getenv('BREVO_API_KEY', '')
        ).strip()
        self.resend_api_key = (
            getattr(settings, 'RESEND_API_KEY', None) or os.getenv('RESEND_API_KEY', '')
        ).strip()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if self.brevo_api_key:
            return self._send_all_via_brevo(email_messages)
        elif self.resend_api_key:
            return self._send_all_via_resend(email_messages)
        else:
            return self._send_all_via_smtp(email_messages)

    # ─────────────────────────────────────────────────────────────
    # Brevo HTTP API (Port 443 HTTPS)
    # ─────────────────────────────────────────────────────────────
    def _send_all_via_brevo(self, email_messages):
        sent_count = 0
        for msg in email_messages:
            try:
                sender_name, sender_email = _parse_sender(msg.from_email)
                recipients = [{"email": r.strip()} for r in msg.to if r.strip()]
                if not recipients:
                    continue

                html_content = None
                text_content = msg.body or ""

                # Check for HTML alternatives (e.g. EmailMultiAlternatives)
                if hasattr(msg, 'alternatives'):
                    for content, mimetype in msg.alternatives:
                        if mimetype == 'text/html':
                            html_content = content
                            break

                if not html_content:
                    html_content = f"<div style='font-family: Arial, sans-serif; line-height: 1.6; direction: rtl; text-align: right; white-space: pre-wrap;'>{text_content}</div>"

                payload = {
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": recipients,
                    "subject": msg.subject,
                    "textContent": text_content,
                    "htmlContent": html_content,
                }

                # Attachments handling
                if getattr(msg, 'attachments', None):
                    brevo_attachments = []
                    for att in msg.attachments:
                        att_name, att_data = self._extract_attachment_data(att)
                        if att_name and att_data:
                            b64_content = base64.b64encode(att_data).decode('ascii')
                            brevo_attachments.append({
                                "name": att_name,
                                "content": b64_content
                            })
                    if brevo_attachments:
                        payload["attachment"] = brevo_attachments

                req = urllib.request.Request(
                    self.BREVO_API_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        "api-key": self.brevo_api_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "DailyJob-Backend/1.0",
                    },
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=10) as response:
                    if 200 <= response.getcode() < 300:
                        sent_count += 1
                        logger.info(f"[Brevo HTTP] Email '{msg.subject}' sent successfully to {msg.to}")
                    else:
                        raise RuntimeError(f"Brevo returned status code {response.getcode()}")

            except Exception as e:
                logger.error(f"[Brevo HTTP Error] Failed to send email to {getattr(msg, 'to', [])}: {e}")
                if not self.fail_silently:
                    raise
        return sent_count

    # ─────────────────────────────────────────────────────────────
    # Resend HTTP API (Port 443 HTTPS)
    # ─────────────────────────────────────────────────────────────
    def _send_all_via_resend(self, email_messages):
        sent_count = 0
        for msg in email_messages:
            try:
                sender_name, sender_email = _parse_sender(msg.from_email)
                from_str = f"{sender_name} <{sender_email}>"
                recipients = [r.strip() for r in msg.to if r.strip()]
                if not recipients:
                    continue

                html_content = None
                text_content = msg.body or ""
                if hasattr(msg, 'alternatives'):
                    for content, mimetype in msg.alternatives:
                        if mimetype == 'text/html':
                            html_content = content
                            break

                payload = {
                    "from": from_str,
                    "to": recipients,
                    "subject": msg.subject,
                    "text": text_content,
                }
                if html_content:
                    payload["html"] = html_content
                else:
                    payload["html"] = f"<div style='font-family: Arial, sans-serif; line-height: 1.6; direction: rtl; text-align: right; white-space: pre-wrap;'>{text_content}</div>"

                if getattr(msg, 'attachments', None):
                    resend_attachments = []
                    for att in msg.attachments:
                        att_name, att_data = self._extract_attachment_data(att)
                        if att_name and att_data:
                            b64_content = base64.b64encode(att_data).decode('ascii')
                            resend_attachments.append({
                                "filename": att_name,
                                "content": b64_content
                            })
                    if resend_attachments:
                        payload["attachments"] = resend_attachments

                req = urllib.request.Request(
                    self.RESEND_API_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        "Authorization": f"Bearer {self.resend_api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "DailyJob-Backend/1.0",
                    },
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=10) as response:
                    if 200 <= response.getcode() < 300:
                        sent_count += 1
                        logger.info(f"[Resend HTTP] Email '{msg.subject}' sent successfully to {msg.to}")
                    else:
                        raise RuntimeError(f"Resend returned status code {response.getcode()}")

            except Exception as e:
                logger.error(f"[Resend HTTP Error] Failed to send email to {getattr(msg, 'to', [])}: {e}")
                if not self.fail_silently:
                    raise
        return sent_count

    # ─────────────────────────────────────────────────────────────
    # SMTP Fallback
    # ─────────────────────────────────────────────────────────────
    def _send_all_via_smtp(self, email_messages):
        try:
            smtp_backend = SmtpEmailBackend(
                host=getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com'),
                port=getattr(settings, 'EMAIL_PORT', 587),
                username=getattr(settings, 'EMAIL_HOST_USER', ''),
                password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
                use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 3),
                fail_silently=self.fail_silently,
            )
            return smtp_backend.send_messages(email_messages)
        except Exception as e:
            logger.warning(f"[HttpApiEmailBackend] Fallback SMTP failed: {e}")
            if not self.fail_silently:
                raise
            return 0

    @staticmethod
    def _extract_attachment_data(attachment):
        """
        Extracts (filename, bytes_content) from Django's various attachment formats.
        """
        try:
            if isinstance(attachment, tuple):
                name = attachment[0]
                content = attachment[1]
                if isinstance(content, str):
                    content = content.encode('utf-8')
                return name, content
            elif hasattr(attachment, 'get_filename'):
                name = attachment.get_filename()
                content = attachment.get_payload(decode=True)
                return name, content
        except Exception:
            pass
        return None, None
