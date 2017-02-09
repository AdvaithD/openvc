from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from data.models import Person, Company

class CusomUserManager(BaseUserManager):
    def create_user(self, email, role, password=None):
        """
        Creates and saves a user with the given email and password.
        Called via command line user creation.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(email=self.normalize_email(email), role=role,)

        user.set_password(password)
        user.save(using=self._db)
        #Person.objects.update_or_create(email=email)
        return user

    def create_superuser(self, email, role, password):
        """
        Creates and saves a superuser with the given email and password.
        Called via command line user creation.
        """
        user = self.create_user(email, role=role, password=password,)
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    """
    Inherited fields:
    last_login   | timestamp with time zone | 
    password     | character varying(128)   | not null
    """
    ROLES = {
        'Investor': 'Investor',
        'Founder': 'Founder',
    }
    ROLE_CHOICES = [(v, k) for k, v in ROLES.iteritems()]

    email      = models.EmailField(max_length=255, unique=True)
    person     = models.OneToOneField(Person, unique=True, related_name='user',
                                      null=True, blank=True)
    role       = models.CharField(max_length=50, choices=ROLE_CHOICES)
    is_active  = models.BooleanField(default=True)
    is_admin   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Inherited from AbstractUser
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']

    objects = CusomUserManager()

    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __unicode__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        # TODO
        return True

    def has_module_perms(self, app_label):
        # TODO
        return True

    @property
    def is_staff(self):
        # TODO
        return self.is_admin

class Account(models.Model):
    company    = models.OneToOneField(Company, unique=True,
                                      related_name='company')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UserAccounts(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   related_name='user_accounts')
    acount     = models.ForeignKey(Account, related_name='account_users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
