"""
Email Utility Service
Handles sending emails via SMTP
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from loguru import logger
from app.core.config import settings


class EmailService:
    """Email sending service using SMTP"""

    @staticmethod
    def send_email(
        to_email: str | List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        發送郵件

        Args:
            to_email: 收件人郵箱（單個或列表）
            subject: 郵件主旨
            html_content: HTML 郵件內容
            text_content: 純文字郵件內容（選填，作為 fallback）

        Returns:
            發送成功返回 True，失敗返回 False
        """
        # 檢查 SMTP 是否已配置
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP not configured, skipping email send")
            logger.info(f"[Email Mock] To: {to_email}, Subject: {subject}")
            logger.debug(f"[Email Mock] Content: {html_content[:200]}...")
            return False

        try:
            # 創建郵件
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
            message["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)
            message["Subject"] = subject

            # 添加純文字版本（fallback）
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                message.attach(part1)

            # 添加 HTML 版本
            part2 = MIMEText(html_content, "html", "utf-8")
            message.attach(part2)

            # 連接到 SMTP 服務器
            if settings.SMTP_SSL:
                smtp = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
            else:
                smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

            # 如果使用 TLS（通常是 port 587）
            if settings.SMTP_TLS and not settings.SMTP_SSL:
                smtp.starttls()

            # 登入
            if settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            # 發送郵件
            recipients = [to_email] if isinstance(to_email, str) else to_email
            smtp.sendmail(
                settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                recipients,
                message.as_string(),
            )

            smtp.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            logger.exception(e)
            return False

    @staticmethod
    def send_verification_email(to_email: str, username: str, verification_url: str) -> bool:
        """
        發送郵箱驗證郵件

        Args:
            to_email: 收件人郵箱
            username: 用戶名
            verification_url: 驗證連結

        Returns:
            發送成功返回 True
        """
        subject = "QuantLab - 請驗證您的郵箱"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9fafb;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #3b82f6;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #6b7280;
                    font-size: 0.9em;
                }}
                .warning {{
                    background: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>歡迎加入 QuantLab！</h1>
            </div>
            <div class="content">
                <p>嗨 {username}，</p>

                <p>感謝您註冊 QuantLab 量化交易平台！</p>

                <p>請點擊下方按鈕驗證您的郵箱：</p>

                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">驗證我的郵箱</a>
                </p>

                <p>或複製以下連結到瀏覽器：</p>
                <p style="word-break: break-all; background: white; padding: 10px; border-radius: 5px;">
                    {verification_url}
                </p>

                <div class="warning">
                    <strong>⚠️ 重要提醒：</strong><br>
                    • 此驗證連結將在 24 小時後失效<br>
                    • 如果您沒有註冊 QuantLab，請忽略此郵件
                </div>

                <p>驗證完成後，您就可以開始使用我們的量化交易功能了！</p>
            </div>
            <div class="footer">
                <p>© 2025 QuantLab. All rights reserved.</p>
                <p>這是一封自動發送的郵件，請勿直接回覆。</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        歡迎加入 QuantLab！

        嗨 {username}，

        感謝您註冊 QuantLab 量化交易平台！

        請點擊以下連結驗證您的郵箱：
        {verification_url}

        ⚠️ 重要提醒：
        • 此驗證連結將在 24 小時後失效
        • 如果您沒有註冊 QuantLab，請忽略此郵件

        驗證完成後，您就可以開始使用我們的量化交易功能了！

        © 2025 QuantLab. All rights reserved.
        """

        return EmailService.send_email(to_email, subject, html_content, text_content)

    @staticmethod
    def send_password_reset_email(to_email: str, username: str, reset_url: str) -> bool:
        """
        發送密碼重設郵件（未來功能）

        Args:
            to_email: 收件人郵箱
            username: 用戶名
            reset_url: 重設連結

        Returns:
            發送成功返回 True
        """
        subject = "QuantLab - 密碼重設請求"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>密碼重設請求</h2>
            <p>嗨 {username}，</p>
            <p>我們收到了您的密碼重設請求。</p>
            <p>請點擊以下連結重設密碼：</p>
            <p><a href="{reset_url}" style="color: #3b82f6;">{reset_url}</a></p>
            <p>此連結將在 1 小時後失效。</p>
            <p>如果您沒有請求重設密碼，請忽略此郵件。</p>
        </body>
        </html>
        """

        text_content = f"嗨 {username}，\n\n請點擊以下連結重設密碼：\n{reset_url}\n\n此連結將在 1 小時後失效。"

        return EmailService.send_email(to_email, subject, html_content, text_content)
