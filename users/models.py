from django.db import models

class FirebaseUser(models.Model):
    uid = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
