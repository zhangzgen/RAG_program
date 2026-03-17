# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import sys
import os
import socket

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from base import Config, logger


class EmailService:
    """邮箱服务类，用于发送验证码"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logger
        self.smtp_server = self.config.SMTP_SERVER
        self.smtp_port = self.config.SMTP_PORT
        self.sender_email = self.config.QQ_EMAIL
        self.sender_auth_code = self.config.QQ_AUTH_CODE
        self.dev_mode = os.environ.get('DEV_MODE', 'false').lower() == 'true'
    
    def generate_verification_code(self, length=6):
        """生成指定长度的数字验证码"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_code(self, to_email, code):
        """
        发送验证码到指定邮箱
        
        Args:
            to_email: 接收邮箱地址
            code: 验证码
            
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        try:
            message = MIMEMultipart()
            message['From'] = self.sender_email
            message['To'] = to_email
            message['Subject'] = '问答系统登录验证码'
            
            body = f"""
            <html>
            <body>
                <h2>问答系统登录验证码</h2>
                <p>您的验证码是：<strong style="font-size: 24px; color: #4CAF50;">{code}</strong></p>
                <p>验证码有效期为5分钟，请尽快使用。</p>
                <p>如果这不是您的操作，请忽略此邮件。</p>
                <br>
                <p>此致</p>
                <p>问答系统团队</p>
            </body>
            </html>
            """
            message.attach(MIMEText(body, 'html', 'utf-8'))
            
            socket.setdefaulttimeout(30)
            
            try:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(message)
            except (socket.error, OSError) as ssl_error:
                self.logger.warning(f"SMTP_SSL连接失败，尝试使用STARTTLS: {ssl_error}")
                with smtplib.SMTP(self.smtp_server, 587) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(message)
            
            self.logger.info(f"验证码发送成功: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP认证失败，请检查邮箱配置: {e}")
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP发送失败: {e}")
            return False
        except socket.timeout:
            self.logger.error("SMTP连接超时，请检查网络连接")
            return False
        except socket.error as e:
            self.logger.error(f"网络连接错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"验证码发送失败: {e}")
            return False


if __name__ == '__main__':
    email_service = EmailService()
    code = email_service.generate_verification_code()
    print(f"生成的验证码: {code}")
