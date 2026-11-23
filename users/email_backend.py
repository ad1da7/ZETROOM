import json
import subprocess
from django.core.mail.backends.base import BaseEmailBackend


class SendmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        count = 0
        for message in email_messages:
            payload = json.dumps({
                "to": ", ".join(message.to),
                "subject": message.subject,
                "body": message.body
            })
            p = subprocess.Popen(
                ["php", "/var/www/u3734581/data/www/zetroom.ru/send_cli.php"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            out, _ = p.communicate(payload.encode("utf-8"))
            if out.decode().strip() == "OK":
                count += 1
        return count