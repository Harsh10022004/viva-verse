import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

def send_email_alert(recipient_email: str, query_text: str, experience_id: str):
    """Send an email alert using SMTP."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    
    if not smtp_user or not smtp_pass:
        logger.warning(f"Simulating Email Alert to {recipient_email} for query '{query_text}'. (SMTP_USER/SMTP_PASS not set)")
        print(f"\n[MOCK EMAIL] To: {recipient_email}\nSubject: New match for '{query_text}'\nLink: /experiences/{experience_id}\n")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = f"Viva-Verse Alert: New Interview Experience for '{query_text}'"

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f5; padding: 20px;">
                <div style="max-w-xl mx-auto bg-white p-8 rounded-xl shadow-lg border border-gray-200">
                    <h2 style="color: #18181b;">New Interview Experience Matched!</h2>
                    <p style="color: #3f3f46; font-size: 16px;">
                        A highly relevant new interview experience was just posted that matches your subscription for:
                        <br/>
                        <strong style="color: #2563eb;">"{query_text}"</strong>
                    </p>
                    <a href="http://localhost:5173/experiences/{experience_id}" 
                       style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px;">
                        Read the Experience
                    </a>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully sent email alert to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")


def send_whatsapp_alert(phone_number: str, query_text: str, experience_id: str):
    """Send a WhatsApp alert using Twilio."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_number = os.environ.get("TWILIO_WHATSAPP_NUMBER") # e.g. 'whatsapp:+14155238886'
    
    if not account_sid or not auth_token or not twilio_number:
        logger.warning(f"Simulating WhatsApp Alert to {phone_number} for query '{query_text}'. (Twilio credentials not set)")
        print(f"\n[MOCK WHATSAPP] To: {phone_number}\nMessage: 🔔 Viva-Verse Alert! New match for '{query_text}'. Link: /experiences/{experience_id}\n")
        return

    try:
        client = Client(account_sid, auth_token)
        
        # Ensure the phone number has 'whatsapp:' prefix
        if not phone_number.startswith('whatsapp:'):
            if not phone_number.startswith('+'):
                # Very basic normalization, assume US if not provided for now, but should ideally be validated on frontend
                phone_number = f"+1{phone_number}"
            phone_number = f"whatsapp:{phone_number}"
            
        message_body = f"🔔 *Viva-Verse Alert*\nA new, highly relevant interview experience was posted matching your subscription for: *'{query_text}'*.\n\nRead it here: http://localhost:5173/experiences/{experience_id}"
        
        message = client.messages.create(
            from_=twilio_number,
            body=message_body,
            to=phone_number
        )
        logger.info(f"Successfully sent WhatsApp alert to {phone_number}, SID: {message.sid}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {phone_number}: {e}")
