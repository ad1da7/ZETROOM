import subprocess
from email.header import Header
from django.core.mail.backends.base import BaseEmailBackend


class SendmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        count = 0
        for message in email_messages:
            try:
                to_addr = ", ".join(message.to)
                subject = Header(message.subject, 'utf-8').encode()
                raw_email = (
                    f"To: {to_addr}\n"
                    f"From: {message.from_email}\n"
                    f"Subject: {subject}\n"
                    f"Content-Type: text/plain; charset=utf-8\n\n"
                    f"{message.body}"
                ).encode('utf-8')

                p = subprocess.Popen(
                    ['/usr/sbin/sendmail', '-t', '-f', message.from_email],
                    stdin=subprocess.PIPE
                )
                p.communicate(raw_email)
                if p.returncode == 0:
                    count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return count
