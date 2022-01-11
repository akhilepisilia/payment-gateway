from django.db import models

# Create your models here.


class SubscriptionData(models.Model):
    user_uuid = models.ForeignKey('User', on_delete=models.CASCADE)
    subscriptionId = models.CharField(max_length=10, unique=True)  # int
    planId = models.CharField(max_length=10)  # int
    expiresOn = models.CharField(max_length=40)
    subReferenceId = models.CharField(max_length=10, primary_key=True)  # int
    status = models.CharField(max_length=20)
    addedon = models.CharField(max_length=50)
    authLink = models.CharField(max_length=40)
    currentCycle = models.IntegerField()  # cycle


class PaymentData(models.Model):
    subReferenceId = models.ForeignKey(
        'SubscriptionData', on_delete=models.CASCADE)
    paymentId = models.CharField(max_length=10)  # int
    scheduledOn = models.CharField(max_length=40)
    initiatedOn = models.CharField(max_length=40)
    amount = models.IntegerField()
    paymentstatus = models.CharField(max_length=20)
    retryAttempts = models.IntegerField()


class clientInfo(models.Model):
    clientId = models.CharField(max_length=100)
    clientSecret = models.CharField(max_length=100)


class User(models.Model):
    email_id = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=30)
    phone = models.CharField(max_length=15)
    user_uuid = models.CharField(max_length=50, unique=True, primary_key=True)

    def __str__(self):
        return self.name


"""
class User(models.Model):
    email_id = models.CharField(max_length=40, unique=True)
    client_id = models.CharField(max_length=8)
    name = models.CharField(max_length=30)
    phone = models.CharField(max_length=15)
    created_date = models.CharField(max_length=20)
    updated_date = models.CharField(max_length=20)
    user_uuid = models.CharField(max_length=50, unique=True, primary_key=True)
    company = models.JSONField()
    subscription = models.TextField(null=True)
    zoho_lead_id = models.CharField(max_length=50,null=True)
"""
