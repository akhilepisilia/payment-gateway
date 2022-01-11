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


@api_view(['GET'])
def get_user_subscription_details(request, user_uuid):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    res = subscription.getSubscription(user_uuid)

    return JsonResponse(res, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_user_subscription(request, user_uuid):

    body = json.loads(request.body.decode('utf-8'))

    matchUser = User.objects.filter(user_uuid=user_uuid)
    if not matchUser:
        return JsonResponse({'error': "incorrect user ID "+user_uuid}, status=status.HTTP_400_BAD_REQUEST)

    if SubscriptionData.objects.filter(user_uuid=user_uuid).exists():
        return JsonResponse({'error': "This user already has subscription"}, status=status.HTTP_400_BAD_REQUEST)

    res = matchUser[0]
    if res.name == '-':
        return JsonResponse({'error': "name not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)
    if res.email_id == '-':
        return JsonResponse({'error': "email not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)
    if res.phone == '-':
        return JsonResponse({'error': "phone no not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)

    result = subscription.createsubscription(
        user_uuid,  body['subscriptionId'], body['planId'])
    print(result)
    if (result == True):
        data = SubscriptionData.objects.get(user_uuid=user_uuid)
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
        return JsonResponse(result)

# we need to inisate it
@api_view(['POST'])
def charge_user_subscription(request, user_uuid):

    body = json.loads(request.body.decode('utf-8'))

    if isUserThere(user_uuid):
        return JsonResponse({'error': "incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.chargesubscription(
        user_uuid, body['amount'], body['scheduledOn']
    )
    print(result)
    if (result['subCode'] == '200'):
        paymentdata = PaymentData.objects.get(paymentId=result['paymentId'])
        chargeResponse = {
            'status': 'OK',
            'payment': {
                'subReferenceId_id': paymentdata.subReferenceId,
                "paymentId": paymentdata.paymentId,
                'scheduledOn': paymentdata.scheduledOn,
                'initiatedOn': paymentdata.initiatedOn,
                "amount": paymentdata.amount,
                'status': paymentdata.paymentstatus,
                'retryAttempts': paymentdata.retryAttempts,
            }
        }
        return JsonResponse(chargeResponse, status=status.HTTP_200_OK, safe=False)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse(result)


@api_view(['GET'])
def get_user_subscription_payment(request, user_uuid):

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.getsubscriptionpayment(user_uuid)
    if len(result) == 0:
        return JsonResponse({'error': "did not find any paymment under the user subscription"}, status=status.HTTP_400_BAD_REQUEST)\

    return JsonResponse({"status": "OK", "payments": result}, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def cancel_user_subscription(request, user_uuid):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.cancelsubscription(user_uuid)

    if(result == True):
        return JsonResponse({"status": "OK", "message": "Subscription Cancelled"}, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    elif(result['subCode'] == '404'):
        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(result)


@api_view(['POST'])
def cancel_charge_subscription(request, user_uuid, paymentId):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    # check if user has payment
    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    if PaymentData.objects.filter(subReferenceId=data.subReferenceId, paymentId=paymentId).exists():
        return JsonResponse({'error': "Did not find any payment under the user"}, status=status.HTTP_400_BAD_REQUEST)

    result = subscription.cancelcharge(user_uuid, paymentId=paymentId)
    if(result == True):
        paymentdata = PaymentData.objects.get(paymentId=paymentId)
        payment = {
            'subReferenceId': paymentdata['subReferenceId_id'],
            'paymentId': paymentdata['paymentId'],
            'scheduledOn': paymentdata['scheduledOn'],
            'initiatedOn': paymentdata['initiatedOn'],
            'amount': paymentdata['amount'],
            'paymentstatus': paymentdata['paymentstatus'],
            'retryAttempts': paymentdata['retryAttempts']
        }
        return JsonResponse({"status": "OK", 'payment': payment}, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    elif(result['subCode'] == '404'):
        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(result)


@api_view(['POST'])
def Retry_charge(request, user_uuid):

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    result = subscription.retrycharge(user_uuid)

    if(result == True):
        return JsonResponse({'status': 'ok'}, status=status.HTTP_200_OK)
    elif(result['subCode'] == '400'):
        return JsonResponse(result, status=status.HTTP_400_BAD_REQUEST)
    elif(result['subCode'] == '404'):
        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(result)
