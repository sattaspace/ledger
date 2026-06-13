"""
DEALERCORE v3.0 — Custom User Manager
---------------------------------------
Custom manager for DsrUser model with email-based authentication.

DSRs log in with email + password (phone is optional).
"""

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class DsrUserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    
    DSRs log in with email + password.
    Phone is optional and used only for contact purposes.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_("The Email field must be set"))
        
        # Normalize email
        email = self.normalize_email(email)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "ADMIN")
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        
        return self.create_user(email, password, **extra_fields)
    
    async def acreate_user(self, email, password=None, **extra_fields):
        """Async version of create_user."""
        if not email:
            raise ValueError(_("The Email field must be set"))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        await user.asave(using=self._db)
        return user
    
    async def acreate_superuser(self, email, password=None, **extra_fields):
        """Async version of create_superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "ADMIN")
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        
        return await self.acreate_user(email, password, **extra_fields)
    
    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for consistent storage.
        Removes spaces, dashes, parentheses.
        """
        if not phone:
            return phone
        # Remove common formatting characters
        return ''.join(c for c in phone if c.isdigit() or c == '+')
