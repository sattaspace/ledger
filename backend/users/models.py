from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # Add your custom fields here (e.g., bio, profile_pic)
    pass
