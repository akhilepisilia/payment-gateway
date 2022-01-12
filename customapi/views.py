from django.http.response import HttpResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
import customapi.subscription as subscription
from .models import SubscriptionData, PaymentData, User, clientInfo
import json
import requests
from django.http import JsonResponse
from datetime import datetime, timedelta
# Create your views here.


cashfreeTestAPI = "https://test.cashfree.com/"


def isUserSubscribed(user_uuid):
    data = SubscriptionData.objects.filter(user_uuid=user_uuid)
    if not data:
        return True


def isUserThere(user_uuid):
    matchUser = User.objects.filter(user_uuid=user_uuid)
    if not matchUser:
        return True


def check_active_subscription(user_uuid):
    flag = 0
    for obj in SubscriptionData.objects.values():
        if (obj['user_uuid_id'] == user_uuid):
            if (obj['status'] == 'INITIALIZED' or obj['status'] == 'ACTIVE' or obj['status'] == 'BANK_APPROVAL_PENDING' or obj['status'] == 'ON_HOLD'):
                flag = flag+1
    if flag > 0 and flag == 1:
        return True
    else:
        return False


def getcurrentsubscriptionID(user_uuid):
    data = SubscriptionData.objects.filter(user_uuid=user_uuid)
    for obj in data:
        if (obj.status == 'INITIALIZED' or obj.status == 'ACTIVE' or obj.status == 'BANK_APPROVAL_PENDING' or obj.status == 'ON_HOLD'):
            return obj.subscriptionId

    return False


@api_view(['GET'])
def get_user_subscription_details(request, user_uuid):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "Incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if not check_active_subscription(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    res = subscription.getSubscription(user_uuid)

    return JsonResponse(res, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_user_all_subscription_details(request, user_uuid):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "Incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    res = subscription.getAllSubscription(user_uuid)

    return JsonResponse({"status": "OK", 'subscriptions': res}, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_user_subscription(request, user_uuid):

    body = json.loads(request.body.decode('utf-8'))

    matchUser = User.objects.filter(user_uuid=user_uuid)
    if not matchUser:
        return JsonResponse({'error': "Incorrect user ID "+user_uuid}, status=status.HTTP_400_BAD_REQUEST)

    if SubscriptionData.objects.filter(user_uuid=user_uuid).exists():
        if subscription.check_active_subscription(user_uuid):
            return JsonResponse({'error': "This user already has an active subscription"}, status=status.HTTP_400_BAD_REQUEST)

    res = matchUser[0]
    if res.name == '-':
        return JsonResponse({'error': "Mame not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)
    if res.email_id == '-':
        return JsonResponse({'error': "Email not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)
    if res.phone == '-':
        return JsonResponse({'error': "Phone no not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)

    result = subscription.createsubscription(user_uuid, body['planId'])

    if (result == True):
        subscriptionId = getcurrentsubscriptionID(user_uuid)
        data = SubscriptionData.objects.get(
            user_uuid=user_uuid, subscriptionId=subscriptionId)
        createsubscriptionResponse = {
            'status': 'OK',
            'subscription': {
                'subscriptionId': data.subscriptionId,
                'subReferenceId': data.subReferenceId,
                'planId': data.planId,
                "status": data.status,
                'authLink': data.authLink
            }
        }
        return JsonResponse(createsubscriptionResponse, status=status.HTTP_200_OK, safe=False)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# we need to inisate it
@api_view(['POST'])
def charge_user_subscription(request, user_uuid):

    body = json.loads(request.body.decode('utf-8'))

    if isUserThere(user_uuid):
        return JsonResponse({'error': "Incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.chargesubscription(
        user_uuid, body['amount'], body['scheduledOn']
    )

    if (result['subCode'] == '200'):
        paymentdata = PaymentData.objects.get(
            paymentId=str(result['paymentId']))
        chargeResponse = {
            'status': 'OK',
            'payment': {
                'subReferenceId_id': paymentdata.subReferenceId.subReferenceId,
                "paymentId": paymentdata.paymentId,
                'scheduledOn': paymentdata.scheduledOn,
                'initiatedOn': paymentdata.initiatedOn,
                "amount": paymentdata.amount,
                'status': paymentdata.paymentstatus,
                'retryAttempts': paymentdata.retryAttempts,
            }
        }
        return JsonResponse(chargeResponse, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_user_subscription_payment(request, user_uuid):

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    if not check_active_subscription(user_uuid):
        return JsonResponse({'error': "The user does not have any active subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.getsubscriptionpayment(user_uuid)
    if len(result) == 0:
        return JsonResponse({'error': "Did not find any paymment under the user subscription"}, status=status.HTTP_400_BAD_REQUEST)\

    return JsonResponse({"status": "OK", "payments": result}, status=status.HTTP_200_OK, safe=False)


@api_view(['GET'])
def get_users_all_subscription_payment(request, user_uuid):

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.getallsubscriptionpayment(user_uuid)
    if len(result) == 0:
        return JsonResponse({'error': "Did not find any paymment under the user subscription"}, status=status.HTTP_400_BAD_REQUEST)\

    return JsonResponse({"status": "OK", "subscriptions": result}, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def cancel_user_subscription(request, user_uuid):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "Incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)

    if not isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any active subscription to be cancelled"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.cancelsubscription(user_uuid)

    if(result == True):
        return JsonResponse({"status": "OK", "message": "Subscription Cancelled"}, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    elif(result['subCode'] == '404'):
        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def cancel_charge_subscription(request, user_uuid, paymentId):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "Incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    # check if user has payment
    subscriptionId = getcurrentsubscriptionID(user_uuid)

    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)

    """cannot cancel if there is no payment"""
    if not PaymentData.objects.filter(subReferenceId=data.subReferenceId, paymentId=paymentId).exists():
        return JsonResponse({'error': "Did not find paymentId "+paymentId+" under the user"}, status=status.HTTP_400_BAD_REQUEST)

    result = subscription.cancelcharge(user_uuid, paymentId)

    if(result == True):
        paymentdata = PaymentData.objects.get(paymentId=paymentId)
        payment = {
            'subReferenceId': paymentdata.subReferenceId.subReferenceId,
            'paymentId': paymentdata.paymentId,
            'scheduledOn': paymentdata.scheduledOn,
            'initiatedOn': paymentdata.initiatedOn,
            'amount': paymentdata.amount,
            'paymentstatus': paymentdata.paymentstatus,
            'retryAttempts': paymentdata.retryAttempts
        }

        return JsonResponse({"status": "OK", 'payment': payment}, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    elif(result['subCode'] == '404'):
        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def Retry_charge(request, user_uuid):

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "The user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)
    if not check_active_subscription(user_uuid):
        return JsonResponse({'error': "The user does not have any active subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.retrycharge(user_uuid)

    if(result == True):
        return JsonResponse({'status': 'ok'}, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    elif(result['subCode'] == '404'):
        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
