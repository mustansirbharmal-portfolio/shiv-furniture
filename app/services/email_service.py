import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from flask import current_app

class EmailService:
    @staticmethod
    def send_email(to_email, subject, html_content, attachments=None):
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            email_address = os.getenv('EMAIL_ADDRESS')
            email_password = os.getenv('EMAIL_PASSWORD')
            
            if not email_address or not email_password:
                print("Email credentials not configured")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Shiv Furniture ERP <{email_address}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={attachment["filename"]}'
                    )
                    msg.attach(part)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.sendmail(email_address, to_email, msg.as_string())
            
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(user_email, user_name, temp_password=None):
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Shiv Furniture ERP</h1>
                </div>
                <div class="content">
                    <p>Dear {user_name},</p>
                    <p>Welcome to the Shiv Furniture Budget Accounting System. Your account has been created successfully.</p>
                    {'<p>Your temporary password is: <strong>' + temp_password + '</strong></p><p>Please change your password after logging in.</p>' if temp_password else ''}
                    <p>Click the button below to access the system:</p>
                    <p style="text-align: center;">
                        <a href="{frontend_url}/login" class="button">Login to Dashboard</a>
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Shiv Furniture Systems. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(user_email, "Welcome to Shiv Furniture ERP", html_content)
    
    @staticmethod
    def send_password_reset_email(user_email, user_name, reset_token):
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Dear {user_name},</p>
                    <p>We received a request to reset your password. Click the button below to reset it:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Shiv Furniture Systems. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(user_email, "Password Reset - Shiv Furniture ERP", html_content)
    
    @staticmethod
    def send_invoice_email(customer_email, customer_name, invoice_number, total_amount, due_date, pdf_content=None):
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .invoice-details {{ background: white; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Invoice from Shiv Furniture</h1>
                </div>
                <div class="content">
                    <p>Dear {customer_name},</p>
                    <p>Please find your invoice details below:</p>
                    <div class="invoice-details">
                        <p><strong>Invoice Number:</strong> {invoice_number}</p>
                        <p><strong>Total Amount:</strong> ₹{total_amount:,.2f}</p>
                        <p><strong>Due Date:</strong> {due_date}</p>
                    </div>
                    <p style="text-align: center;">
                        <a href="{frontend_url}/portal/invoices" class="button">View & Pay Invoice</a>
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Shiv Furniture Systems. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        attachments = None
        if pdf_content:
            attachments = [{'filename': f'Invoice_{invoice_number}.pdf', 'content': pdf_content}]
        
        return EmailService.send_email(customer_email, f"Invoice {invoice_number} - Shiv Furniture", html_content, attachments)
    
    @staticmethod
    def send_payment_confirmation_email(contact_email, contact_name, payment_number, amount, payment_date):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10b981; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .payment-details {{ background: white; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Confirmation</h1>
                </div>
                <div class="content">
                    <p>Dear {contact_name},</p>
                    <p>We have received your payment. Thank you!</p>
                    <div class="payment-details">
                        <p><strong>Payment Reference:</strong> {payment_number}</p>
                        <p><strong>Amount:</strong> ₹{amount:,.2f}</p>
                        <p><strong>Date:</strong> {payment_date}</p>
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Shiv Furniture Systems. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(contact_email, f"Payment Confirmation - {payment_number}", html_content)
    
    @staticmethod
    def send_daily_summary(admin_email, admin_name, summary_data):
        """Send daily summary email to admin"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: white; padding: 15px; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
                .stat-label {{ font-size: 12px; color: #666; }}
                .highlight {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Daily Summary Report</h1>
                    <p>{summary_data['date']}</p>
                </div>
                <div class="content">
                    <p>Good morning {admin_name},</p>
                    <p>Here's your daily business summary:</p>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{summary_data['new_orders']}</div>
                            <div class="stat-label">New Orders</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{summary_data['new_invoices']}</div>
                            <div class="stat-label">New Invoices</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">₹{summary_data['incoming_amount']:,.0f}</div>
                            <div class="stat-label">Payments Received ({summary_data['incoming_payments']})</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">₹{summary_data['outgoing_amount']:,.0f}</div>
                            <div class="stat-label">Payments Made ({summary_data['outgoing_payments']})</div>
                        </div>
                    </div>
                    
                    <div class="highlight">
                        <p><strong>Pending Receivables:</strong></p>
                        <p>{summary_data['pending_invoices']} invoices with ₹{summary_data['pending_amount']:,.2f} outstanding</p>
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Shiv Furniture Systems. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(admin_email, f"Daily Summary - {summary_data['date']} - Shiv Furniture", html_content)
