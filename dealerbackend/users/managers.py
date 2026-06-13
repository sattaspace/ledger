"""
DEALERCORE v3.0 — Custom User Manager
---------------------------------------
Custom manager for DsrUser model with phone-based authentication.

DSRs log in with phone + password (email is optional).
"""

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class DsrUserManager(BaseUserManager):
    """
    Custom user manager for phone-based authentication.
    
    DSRs log in with phone + password (not email or username).
    Email is optional and used only for notifications.
    """
    
    def create_user(self, phone, password=None, **extra_fields):
        """Create and save a regular user with the given phone and password."""
        if not phone:
            raise ValueError(_("The Phone field must be set"))
        
        # Normalize phone (remove spaces, dashes, etc.)
        phone = self.normalize_phone(phone)
        
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and save a superuser with the given phone and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "ADMIN")
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        
        return self.create_user(phone, password, **extra_fields)
    
    async def acreate_user(self, phone, password=None, **extra_fields):
        """Async version of create_user."""
        if not phone:
            raise ValueError(_("The Phone field must be set"))
        
        phone = self.normalize_phone(phone)
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        await user.asave(using=self._db)
        return user
    
    async def acreate_superuser(self, phone, password=None, **extra_fields):
        """Async version of create_superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "ADMIN")
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        
        return await self.acreate_user(phone, password, **extra_fields)
    
    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for consistent storage.
        Removes spaces, dashes, parentheses.
        """
        if not phone:
            return phone
        # Remove common formatting characters
        return ''.join(c for c in phone if c.isdigit() or c == '+')
    
    def get_by_phone_or_email(self, identifier: str):
        """
        Get user by phone or email.
        Useful for login where user might enter either.
        """
        # Try phone first
        try:
            return self.get(phone=identifier)
        except self.model.DoesNotExist:
            pass
        
        # Try email
        try:
            return self.get(email__iexact=identifier)
        except self.model.DoesNotExist:
            pass
        
        return None
