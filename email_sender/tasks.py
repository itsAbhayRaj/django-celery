from celery import shared_task
import logging
from django.core.mail import send_mail , EmailMultiAlternatives , BadHeaderError
from django.template.loader import render_to_string
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

logger = logging.getLogger('email_tasks')

@shared_task(bind=True)
def send_email_task(self, recipient_email,subject, message, html_message=None, attachments=None, from_email=None):
    
    try:
        validate_email(recipient_email)
    except ValidationError:
        logger.error(f"Invalid email address: {recipient_email}")
        return "Invalid email address"

    from_email = from_email or None
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[recipient_email],
        )
        if html_message:
            msg.attach_alternative(html_message, "text/html")
        if attachments:
            for attachment in attachments:
                msg.attach(attachment['filename'], attachment['content'], attachment['mimetype'])
        msg.send()
        logger.info(f"Email sent to {recipient_email} (task id: {self.request.id})")
        return {'status': 'sent', 'recipient': recipient_email}
    
    except BadHeaderError:
        logger.exception(f"Bad header while sending email to {recipient_email}")
        return {'status': 'failed', 'reason': 'bad_header'}
    except Exception as e:
        logger.exception(f"Failed to send email to {recipient_email}: {e}")
        return {'status': 'failed', 'reason': str(e)}

@shared_task(bind=True)
def send_bulk_email_task(self, recipient_list, subject, message, html_message=None, attachments=None, from_email=None):
    results = []
    
    # BCC
    try:
        from_email = from_email or None
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[from_email] if from_email else [],
        )
        if html_message:
            msg.attach_alternative(html_message, "text/html")
        if attachments:
            for attachment in attachments:
                msg.attach(*attachment)
        msg.bcc = recipient_list
        msg.send()
        logger.info(f"Bulk email sent to {len(recipient_list)} recipients (task id: {self.request.id})")    
        return {'status': 'sent', 'recipients_count': len(recipient_list)}
    except Exception as e:
        logger.exception(f"Bulk email failed: {e}")
        # Fallback: send individually and collect per-recipient results
        for r in recipient_list:
            try:
                validate_email(r)
            except ValidationError:
                results.append({'recipient': r, 'status': 'invalid_email'})
                continue
            try:
                msg2 = EmailMultiAlternatives(subject=subject, body=message, from_email=from_email, to=[r])
                if html_message:
                    msg2.attach_alternative(html_message, 'text/html')
                if attachments:
                    for att in attachments:
                        msg2.attach(*att)
                msg2.send(fail_silently=False)
                results.append({'recipient': r, 'status': 'sent'})
            except Exception as e2:
                logger.exception(f"Failed to send to {r}: {e2}")
                results.append({'recipient': r, 'status': 'failed', 'reason': str(e2)})
        return {'status': 'partial' if any(r.get('status') != 'sent' for r in results) else 'sent', 'results': results}