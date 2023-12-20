import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailClient:
    def __init__(self, settings):
        self.settings = settings
        self.smtp_server = settings.email_settings["smtp_server"]
        self.smtp_port = settings.email_settings["smtp_port"]
        self.sender_email = settings.email_settings["email"]
        self.sender_password = settings.email_settings["password"]

        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)


    def send_email(self, subject, message=None, recipient_email=None):
        if message is None:
            message = subject
        if recipient_email is None:
            recipient_email = self.settings.email_settings["recipient_email"]
        try:
            # Create a multipart message and set headers
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject

            # Add body to the email
            msg.attach(MIMEText(message, 'plain'))

            # Create SMTP session for sending the email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            self.logger.info("Email sent successfully!")
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
