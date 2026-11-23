import json
import urllib.request
from django.core.mail.backends.base import BaseEmailBackend


class SendmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        count = 0
        for message in email_messages:
            try:
                payload = json.dumps({
                    'token': 'ZETROOM_SECRET_KEY_2026',
                    'to': ', '.join(message.to),
                    'subject': message.subject,
                    'body': message.body,
                }).encode('utf-8')

                req = urllib.request.Request(
                    'http://zetroom.ru',
                    data=payload,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.read().decode('utf-8').strip() == 'OK':
                        count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return count
