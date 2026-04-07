# -*- coding: utf-8 -*-
import os
import random
import smtplib
import socket
import string
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from base import Config, logger


class EmailService:
    """Email service for sending verification codes."""

    def __init__(self):
        self.logger = logger
        self.dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
        self.reload_config()

    def reload_config(self):
        self.config = Config()
        self.smtp_server = self.config.SMTP_SERVER
        self.smtp_port = self.config.SMTP_PORT
        self.sender_email = self.config.QQ_EMAIL
        self.sender_auth_code = self.config.QQ_AUTH_CODE

    def generate_verification_code(self, length=6):
        return "".join(random.choices(string.digits, k=length))

    def send_verification_code(self, to_email, code):
        try:
            self.reload_config()

            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = to_email
            message["Subject"] = "问答系统登录验证码"

            body = f"""
            <html>
            <body>
                <h2>问答系统登录验证码</h2>
                <p>您的验证码是：<strong style=\"font-size: 24px; color: #4CAF50;\">{code}</strong></p>
                <p>验证码有效期为 5 分钟，请尽快使用。</p>
                <p>如果这不是您的操作，请忽略此邮件。</p>
                <br>
                <p>此致</p>
                <p>问答系统团队</p>
            </body>
            </html>
            """
            message.attach(MIMEText(body, "html", "utf-8"))

            socket.setdefaulttimeout(30)

            try:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(message)
            except (socket.error, OSError) as ssl_error:
                self.logger.warning(f"SMTP_SSL failed, fallback to STARTTLS: {ssl_error}")
                with smtplib.SMTP(self.smtp_server, 587) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(message)

            self.logger.info(f"Verification code sent: {to_email}")
            return True
        except smtplib.SMTPAuthenticationError as exc:
            self.logger.error(f"SMTP auth failed: {exc}")
            return False
        except smtplib.SMTPException as exc:
            self.logger.error(f"SMTP send failed: {exc}")
            return False
        except socket.timeout:
            self.logger.error("SMTP connection timeout")
            return False
        except socket.error as exc:
            self.logger.error(f"Network error while sending email: {exc}")
            return False
        except Exception as exc:
            self.logger.error(f"Failed to send verification code: {exc}")
            return False


if __name__ == "__main__":
    email_service = EmailService()
    code = email_service.generate_verification_code()
    print(f"Generated code: {code}")
