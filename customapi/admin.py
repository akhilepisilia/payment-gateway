from django.contrib import admin
from .models import clientInfo, SubscriptionData, PaymentData, User
# Register your models here.
admin.site.register(SubscriptionData)
admin.site.register(PaymentData)
admin.site.register(User)
admin.site.register(clientInfo)
