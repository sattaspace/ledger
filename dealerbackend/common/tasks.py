"""
DEALERCORE v3.0 — Async Tasks
==============================
Celery tasks for background processing.

Tasks:
- send_dsr_invitation_email: Send invitation email to new DSR
- send_dsr_notification_email: Send notification to registered DSR
- send_password_reset_email: Send password reset email
"""

import logging
from typing import Optional

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL SENDING TASKS
# ═══════════════════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_dsr_invitation_email(
    self,
    email: str,
    dealer_name: str,
    dealer_business: str,
    role: str,
    registration_url: str,
    expires_at: Optional[str] = None,
    message: Optional[str] = None,
):
    """
    Send DSR invitation email with registration link.
    
    This is sent when a DSR is NOT registered in the system.
    They receive a link to register and accept the invitation.
    
    Args:
        email: DSR email address
        dealer_name: Name of the dealer inviting them
        dealer_business: Business name of the dealer
        role: Role being offered (DSR, Manager, etc.)
        registration_url: URL to register and accept invitation
        expires_at: When the invitation expires
        message: Optional personal message from dealer
    """
    try:
        context = {
            "email": email,
            "dealer_name": dealer_name,
            "dealer_business": dealer_business,
            "role": _format_role(role),
            "registration_url": registration_url,
            "expires_at": expires_at,
            "message": message,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }
        
        # Render email templates
        text_content = render_to_string("emails/dsr_invitation.txt", context)
        html_content = render_to_string("emails/dsr_invitation.html", context)
        
        # Create email
        subject = f"You're invited to join {dealer_name} on {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send
        msg.send()
        
        logger.info(f"DSR invitation email sent to {email} from dealer {dealer_name}")
        return {"success": True, "email": email}
        
    except Exception as e:
        logger.error(f"Failed to send DSR invitation email to {email}: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_dsr_notification_email(
    self,
    email: str,
    dsr_name: str,
    dealer_name: str,
    dealer_business: str,
    role: str,
    invitation_id: str,
    message: Optional[str] = None,
    password_setup_url: Optional[str] = None,
):
    """
    Send notification email to already-registered DSR.
    
    This is sent when a DSR already has an account.
    They'll see the invitation in their dashboard, but we also
    send an email notification.
    
    Args:
        email: DSR email address
        dsr_name: DSR's name
        dealer_name: Name of the dealer inviting them
        dealer_business: Business name of the dealer
        role: Role being offered
        invitation_id: ID of the invitation (for dashboard link)
        message: Optional personal message from dealer
        password_setup_url: Optional URL for DSR to set their password
            (sent when DSR has an unusable password, e.g. migrated from
            old DSR model)
    """
    try:
        # Build dashboard URL
        dashboard_url = f"{settings.DEALER_FRONTEND_URL}/dsr/invitations"
        
        context = {
            "email": email,
            "dsr_name": dsr_name,
            "dealer_name": dealer_name,
            "dealer_business": dealer_business,
            "role": _format_role(role),
            "dashboard_url": dashboard_url,
            "password_setup_url": password_setup_url,
            "message": message,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }
        
        # Render email templates
        text_content = render_to_string("emails/dsr_notification.txt", context)
        html_content = render_to_string("emails/dsr_notification.html", context)
        
        # Create email
        subject = f"New invitation from {dealer_name} on {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send
        msg.send()
        
        logger.info(f"DSR notification email sent to {email} from dealer {dealer_name}")
        return {"success": True, "email": email}
        
    except Exception as e:
        logger.error(f"Failed to send DSR notification email to {email}: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_password_reset_email(
    self,
    email: str,
    reset_url: str,
    expires_hours: int = 24,
):
    """
    Send password reset email to DSR.
    
    Args:
        email: DSR email address
        reset_url: URL to reset password
        expires_hours: Hours until link expires
    """
    try:
        context = {
            "email": email,
            "reset_url": reset_url,
            "expires_hours": expires_hours,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }
        
        # Render email templates
        text_content = render_to_string("emails/password_reset.txt", context)
        html_content = render_to_string("emails/password_reset.html", context)
        
        # Create email
        subject = f"Reset your {settings.SITE_NAME} password"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send
        msg.send()
        
        logger.info(f"Password reset email sent to {email}")
        return {"success": True, "email": email}
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_welcome_email(
    self,
    email: str,
    dsr_name: str,
):
    """
    Send welcome email to newly registered DSR.
    
    Args:
        email: DSR email address
        dsr_name: DSR's name
    """
    try:
        dashboard_url = f"{settings.DEALER_FRONTEND_URL}/dsr/dashboard"
        
        context = {
            "email": email,
            "dsr_name": dsr_name,
            "dashboard_url": dashboard_url,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }
        
        # Render email templates
        text_content = render_to_string("emails/welcome_dsr.txt", context)
        html_content = render_to_string("emails/welcome_dsr.html", context)
        
        # Create email
        subject = f"Welcome to {settings.SITE_NAME}!"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send
        msg.send()
        
        logger.info(f"Welcome email sent to {email}")
        return {"success": True, "email": email}
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        raise self.retry(exc=e)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _format_role(role: str) -> str:
    """Format role for display in emails."""
    role_map = {
        "DSR": "DSR (Sales Representative)",
        "Senior_DSR": "Senior DSR",
        "Manager": "Manager",
        "Order Collector": "Order Collector",
        "Collector": "Order Collector",
    }
    return role_map.get(role, role)


# ═══════════════════════════════════════════════════════════════════════════
# FIX DSR-005/018: EMAIL VERIFICATION TASK
# ═══════════════════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_email_verification(
    self,
    email: str,
    dsr_name: str,
    verification_url: str,
    expires_hours: int = 24,
):
    """
    Send email verification link to DSR after self-registration.

    FIX DSR-005/018: DSRs must verify their email before accepting
    invitations. This prevents spam accounts and email impersonation.

    Args:
        email: DSR email address
        dsr_name: DSR's display name
        verification_url: URL with token for email verification
        expires_hours: Hours until verification link expires
    """
    try:
        context = {
            "email": email,
            "dsr_name": dsr_name,
            "verification_url": verification_url,
            "expires_hours": expires_hours,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }

        # Render email templates
        text_content = render_to_string("emails/email_verification.txt", context)
        html_content = render_to_string("emails/email_verification.html", context)

        # Create email
        subject = f"Verify your email for {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")

        # Send
        msg.send()

        logger.info(f"Email verification sent to {email}")
        return {"success": True, "email": email}

    except Exception as e:
        logger.error(f"Failed to send email verification to {email}: {e}")
        raise self.retry(exc=e)


# ═══════════════════════════════════════════════════════════════════════════
# FIX DSR-019: LIFECYCLE NOTIFICATION TASKS
# ═══════════════════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_invitation_accepted_notification(
    self,
    dealer_email: str,
    dealer_name: str,
    dsr_name: str,
    dsr_email: str,
    role: str,
):
    """
    FIX DSR-019: Notify dealer when their invitation is accepted.
    """
    try:
        context = {
            "dealer_name": dealer_name,
            "dsr_name": dsr_name,
            "dsr_email": dsr_email,
            "role": _format_role(role),
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/invitation_accepted.txt", context)
        html_content = render_to_string("emails/invitation_accepted.html", context)

        subject = f"{dsr_name} accepted your invitation on {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[dealer_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Invitation accepted notification sent to dealer {dealer_email}")
        return {"success": True, "email": dealer_email}

    except Exception as e:
        logger.error(f"Failed to send invitation accepted notification: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_invitation_rejected_notification(
    self,
    dealer_email: str,
    dealer_name: str,
    dsr_name: str,
    dsr_email: str,
    role: str,
):
    """
    FIX DSR-019: Notify dealer when their invitation is rejected.
    """
    try:
        context = {
            "dealer_name": dealer_name,
            "dsr_name": dsr_name,
            "dsr_email": dsr_email,
            "role": _format_role(role),
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/invitation_rejected.txt", context)
        html_content = render_to_string("emails/invitation_rejected.html", context)

        subject = f"{dsr_name} declined your invitation on {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[dealer_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Invitation rejected notification sent to dealer {dealer_email}")
        return {"success": True, "email": dealer_email}

    except Exception as e:
        logger.error(f"Failed to send invitation rejected notification: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_dsr_removed_notification(
    self,
    dsr_email: str,
    dsr_name: str,
    dealer_name: str,
    dealer_business: str,
    reason: str = "",
):
    """
    FIX DSR-019: Notify DSR when they are removed from a dealer's team.
    """
    try:
        context = {
            "dsr_name": dsr_name,
            "dealer_name": dealer_name,
            "dealer_business": dealer_business,
            "reason": reason,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/dsr_removed.txt", context)
        html_content = render_to_string("emails/dsr_removed.html", context)

        subject = f"You have been removed from {dealer_name} on {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[dsr_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"DSR removal notification sent to {dsr_email}")
        return {"success": True, "email": dsr_email}

    except Exception as e:
        logger.error(f"Failed to send DSR removal notification: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_dsr_left_notification(
    self,
    dealer_email: str,
    dealer_name: str,
    dsr_name: str,
    dsr_email: str,
    reason: str = "",
):
    """
    FIX DSR-019: Notify dealer when a DSR leaves their team.
    """
    try:
        context = {
            "dealer_name": dealer_name,
            "dsr_name": dsr_name,
            "dsr_email": dsr_email,
            "reason": reason,
            "site_name": settings.SITE_NAME,
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/dsr_left.txt", context)
        html_content = render_to_string("emails/dsr_left.html", context)

        subject = f"{dsr_name} has left your team on {settings.SITE_NAME}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[dealer_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"DSR left notification sent to dealer {dealer_email}")
        return {"success": True, "email": dealer_email}

    except Exception as e:
        logger.error(f"Failed to send DSR left notification: {e}")
        raise self.retry(exc=e)
