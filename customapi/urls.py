from django.urls import path

from . import views

urlpatterns = [
    path("v1/subscription/create/user/<str:user_uuid>",
         views.create_user_subscription, name="create_user_subscription"),

    path("v1/subscription/charge/user/<str:user_uuid>",
         views.charge_user_subscription, name="charge_user_subscription"),

    path("v1/subscription/details/user/<str:user_uuid>",
         views.get_user_subscription_details, name="get_user_subscription_details"),

    path("v1/subscription/paymentDetails/user/<str:user_uuid>",
         views.get_user_subscription_payment, name="get_user_subscription_payment"),

    path("v1/subscription/cancelCharge/user/<str:user_uuid>/paymentId/<str:paymentId>",
         views.cancel_charge_subscription, name="cancel_charge_subscription"),

    path("v1/subscription/cancel/user/<str:user_uuid>",
         views.cancel_user_subscription, name="cancel_user_subscription"),

]
