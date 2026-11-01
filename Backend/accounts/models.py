"""Custom user and property owner profile models."""

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify

mobile_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{9,14}$",
    message="Enter a valid mobile number with 10 to 15 digits.",
)


class UserManager(DjangoUserManager):
    """Create users with normalized email addresses and generated usernames."""

    def _create_user(self, username, email, password, **extra_fields):
        if not email and not username:
            raise ValueError("An email address or username is required.")

        if email:
            email = self.normalize_email(email).strip().lower()
        else:
            base_slug = slugify(username) or "user"
            email = f"{base_slug}@example.com"
            candidate_email = email
            suffix = 1
            while self.model.objects.filter(email__iexact=candidate_email).exists():
                suffix += 1
                candidate_email = f"{base_slug}{suffix}@example.com"
            email = candidate_email

        username = username or self.model.generate_unique_username(email)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusers must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_superuser=True.")

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """Application user with student, property owner and admin roles."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        OWNER = "owner", "Property Owner"
        ADMIN = "admin", "Admin"

    full_name = models.CharField("full name", max_length=150, blank=True)
    email = models.EmailField("email address", unique=True)
    mobile_number = models.CharField(
        "mobile number",
        max_length=16,
        blank=True,
        validators=[mobile_validator],
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["full_name", "username"]

    def __str__(self):
        return self.get_full_name()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if not self.username and self.email:
            self.username = self.generate_unique_username(self.email)
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name.strip() or self.first_name.strip() or self.username

    def get_short_name(self):
        full = self.get_full_name()
        return full.split()[0] if full else self.username

    @classmethod
    def generate_unique_username(cls, email):
        prefix = email.split("@", 1)[0].replace(".", "-").replace("_", "-")
        base = slugify(prefix)[:120] or "user"
        candidate = base
        suffix = 1
        while cls.objects.filter(username__iexact=candidate).exists():
            suffix += 1
            candidate = f"{base}-{suffix}"[:150]
        return candidate

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT and not self.is_platform_admin

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER and not self.is_platform_admin

    @property
    def is_platform_admin(self):
        return self.is_superuser or self.is_staff or self.role == self.Role.ADMIN


class OwnerProfile(models.Model):
    """Business profile for users who list properties."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="owner_profile",
    )
    owner_name = models.CharField(max_length=150, blank=True)
    contact_number = models.CharField(
        max_length=16,
        blank=True,
        validators=[mobile_validator],
    )
    business_name = models.CharField(max_length=200, blank=True)
    profile_photo = models.ImageField(
        upload_to="owner-profiles/%Y/%m/",
        blank=True,
    )
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_name", "owner_name"]

    def __str__(self):
        return self.business_name or self.owner_name or self.user.get_full_name()
