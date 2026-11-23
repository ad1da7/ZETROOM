import subprocess
from django.core.mail.backends.base import BaseEmailBackend


class SendmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        count = 0
        for message in email_messages:
            try:
                p = subprocess.Popen(
                    ['/usr/sbin/sendmail', '-t', '-f', message.from_email],
                    stdin=subprocess.PIPE
                )
                p.communicate(message.message().as_bytes())
                if p.returncode == 0:
                    count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return count
