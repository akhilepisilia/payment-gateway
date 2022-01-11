from django.http.response import HttpResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

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

# each uuid should have only one subscription only or one should be compleated or canceled  safe=False


def check_user_subscription_more_than_one(user_uuid):
    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    flag = 0
    for obj in SubscriptionData.objects.values():
        if (obj['user_uuid_id'] == user_uuid):
            if (obj['status'] == 'INITIALIZED' or obj['status'] == 'ACTIVE' or obj['status'] == 'BANK_APPROVAL_PENDING' or obj['status'] == 'ON_HOLD'):
                flag = flag+1
    if flag > 0:
        return True
    else:
        return False


def update_user_subscription_details(user_uuid):

    global cashfreeTestAPI
    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    clientinfo = clientInfo.objects.all()

    url = cashfreeTestAPI+"api/v2/subscriptions/"+data.subReferenceId

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("GET", url, headers=headers)
    pretty_json = json.loads(response.text)

    data.status = pretty_json['subscription']['status']
    data.currentCycle = pretty_json['subscription']['currentCycle']
    data.save()
    print("updated user sub details")


@api_view(['GET'])
def get_user_subscription_details(request, user_uuid):

    if isUserThere(user_uuid):
        return JsonResponse({'error': "incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)
    update_user_subscription_details(user_uuid)

    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    matchUser = User.objects.filter(user_uuid=user_uuid)
    res = matchUser[0]

    subscriptiondata = {
        "subscriptionId":   data.subscriptionId,
        "subReferenceId": data.subReferenceId,
        "planId":    data.planId,
        "status":   data.status,
        "addedon": data.addedon,
        "expiresOn":  data.expiresOn,
        "authLink": data.authLink,
        "currentCycle": data.currentCycle
    }

    return JsonResponse(subscriptiondata, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_user_subscription(request, user_uuid):

    global cashfreeTestAPI
    # SubscriptionData.objects.filter(user_uuid=user_uuid).exists()
    if SubscriptionData.objects.filter(user_uuid=user_uuid).exists():
        return JsonResponse({'error': "This user already has subscription"}, status=status.HTTP_400_BAD_REQUEST)

    body = json.loads(request.body.decode('utf-8'))

    url = cashfreeTestAPI + "api/v2/subscriptions"

    matchUser = User.objects.filter(user_uuid=user_uuid)
    if not matchUser:
        return JsonResponse({'error': "did not find "+user_uuid}, status=status.HTTP_400_BAD_REQUEST)
    res = matchUser[0]

    if res.name == '-':
        return JsonResponse({'error': "name not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)
    if res.email_id == '-':
        return JsonResponse({'error': "email not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)
    if res.phone == '-':
        return JsonResponse({'error': "phone no not found , Please update your details"}, status=status.HTTP_400_BAD_REQUEST)

    expiresOn = (datetime.now()+timedelta(days=730)
                 ).strftime("%Y-%m-%d %H:%M:%S")
    addedon = (datetime.now()+timedelta(days=0)).strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "subscriptionId":   body["subscriptionId"],
        "planId":   body["planId"],
        "customerName":    res.name,
        "customerEmail":  res.email_id,
        "customerPhone":  res.phone,
        "expiresOn": expiresOn,
        "returnUrl":   "https://www.episilia.com/",
        "subscriptionNote": "for api testing",
        "authAmount": 1
    }

    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    pretty_json = json.loads(response.text)
    if(response.status_code == 200):
        user = User.objects.get(user_uuid=user_uuid)
        data = SubscriptionData(
            user_uuid=user,
            subscriptionId=body['subscriptionId'],
            planId=body["planId"],
            expiresOn=expiresOn,
            subReferenceId=pretty_json['subReferenceId'],
            status=pretty_json['subStatus'],
            addedon=addedon,
            authLink=pretty_json['authLink'],
            currentCycle=0
        )
        print(pretty_json)
        try:
            data.save()
            update_user_subscription_details(user_uuid)
        except Exception as e:
            error_res = {'error': e}
            return Response(error_res)

        createsubscriptionResponse = {
            'status': 'OK',
            'subscription': {
                'subscriptionId': body['subscriptionId'],
                "status": pretty_json['subStatus'],
                'authLink': pretty_json['authLink']
            }
        }
        return JsonResponse(createsubscriptionResponse, status=status.HTTP_200_OK, safe=False)
    elif(response.status_code == 400):
        return Response(pretty_json, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(pretty_json)

# we need to inisate it
@api_view(['POST'])
def charge_user_subscription(request, user_uuid):

    global cashfreeTestAPI
    body = json.loads(request.body.decode('utf-8'))

    if isUserThere(user_uuid):
        return JsonResponse({'error': "incorrect user ID  " + user_uuid},
                            status=status.HTTP_400_BAD_REQUEST)
    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    data = SubscriptionData.objects.get(user_uuid=user_uuid)

    url = cashfreeTestAPI+"api/v2/subscriptions/"+data.subReferenceId+"/charge"
    amount = body['amount']
    payload = {
        "amount": amount,
        # (datetime.now()+timedelta(days=5)).strftime("%Y-%m-%d"),
        "scheduledOn": body['scheduledOn'],
        "remarks": "amount"
    }
    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }
    response = requests.request("POST", url, json=payload, headers=headers)
    pretty_json = json.loads(response.text)

    if(response.status_code == 200):

        paymentData = PaymentData(
            subReferenceId=data,
            paymentId=pretty_json['payment']['paymentId'],
            scheduledOn=pretty_json['payment']['scheduledOn'],
            initiatedOn=pretty_json['payment']['initiatedOn'],
            amount=pretty_json['payment']['amount'],
            paymentstatus=pretty_json['payment']['status'],
            retryAttempts=pretty_json['payment']['retryAttempts']
        )

        try:
            paymentData.save()
        except Exception as e:
            error_res = {'error': e}
            return Response(error_res)
        chargeResponse = {
            'status': 'OK',
            'payment': {
                'subReferenceId_id': pretty_json['payment']['subReferenceId'],
                "paymentId": pretty_json['payment']['paymentId'],
                'scheduledOn': pretty_json['payment']['scheduledOn'],
                'initiatedOn': pretty_json['payment']['initiatedOn'],
                "amount": pretty_json['payment']['amount'],
                'status': pretty_json['payment']['status'],
                'retryAttempts': pretty_json['payment']['retryAttempts'],
            }
        }
        return JsonResponse(chargeResponse, status=status.HTTP_200_OK)
    elif(response.status_code == 400):
        return Response(pretty_json, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(pretty_json)


'''
@api_view(['GET'])
def update_all_user_subscription_payment(request, user_uuid, lastpaymentId):
    global cashfreeTestAPI
    data = SubscriptionData.objects.get(user_uuid=user_uuid)

    isUserSubscribed(user_uuid)

    paymentId = int(lastpaymentId)+5
    url = cashfreeTestAPI+"api/v2/subscriptions/" + data.subReferenceId + \
        "/payments?lastId="+str(paymentId)+"&count=24"
    print(url)
    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("GET", url, headers=headers)
    pretty_json = json.loads(response.text)
    return JsonResponse(pretty_json, status=status.HTTP_200_OK)
'''


def update_subscription_payment_details(user_uuid, paymentId):
    global cashfreeTestAPI

    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    paymentdata = PaymentData.objects.get(paymentId=paymentId)

    url = cashfreeTestAPI+"api/v2/subscriptions/" + \
        data.subReferenceId + "/payments/"+str(paymentId)

    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("GET", url, headers=headers)
    pretty_json = json.loads(response.text)
    paymentdata.paymentstatus = pretty_json['payment']['status']
    paymentdata.retryAttempts = pretty_json['payment']['retryAttempts']
    paymentdata.save()


@api_view(['GET'])
def get_user_subscription_payment(request, user_uuid):
    #paymentdata = [obj for obj in PaymentData.objects.values()]
    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    matchUser = PaymentData.objects.filter(subReferenceId=data.subReferenceId)
    if not matchUser:
        return JsonResponse({'error': "did not find any paymment under the user subscription"}, status=status.HTTP_400_BAD_REQUEST)

    resData = []
    for obj in PaymentData.objects.values():
        print(obj)
        if (obj['subReferenceId_id'] == data.subReferenceId):
            update_subscription_payment_details(user_uuid, obj['paymentId'])
            paymentData = {
                'subReferenceId': obj['subReferenceId_id'],
                'paymentId': obj['paymentId'],
                'scheduledOn': obj['scheduledOn'],
                'initiatedOn': obj['initiatedOn'],
                'amount': obj['amount'],
                'paymentstatus': obj['paymentstatus'],
                'retryAttempts': obj['retryAttempts']
            }
            resData.append(paymentData)
    print(resData)
    return JsonResponse({"status": "OK", "payments": resData}, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def cancel_user_subscription(request, user_uuid):
    global cashfreeTestAPI

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    url = cashfreeTestAPI+"api/v2/subscriptions/"+data.subReferenceId+"/cancel"

    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("POST", url, headers=headers)
    pretty_json = json.loads(response.text)

    update_user_subscription_details(user_uuid)
    data.delete()
    if(response.status_code == 200):
        return JsonResponse(pretty_json, status=status.HTTP_200_OK)
    elif(response.status_code == 400):
        return JsonResponse(pretty_json, status=status.HTTP_400_BAD_REQUEST)
    elif(response.status_code == 404):
        return JsonResponse(pretty_json, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(pretty_json)


@api_view(['POST'])
def cancel_charge_subscription(request, user_uuid, paymentId):
    global cashfreeTestAPI

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    url = cashfreeTestAPI+"api/v2/subscription/" + \
        data.subReferenceId+"/charge/"+paymentId+"/cancel"
    print(url)
    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("POST", url, headers=headers)
    pretty_json = json.loads(response.text)
    print(pretty_json)
    update_user_subscription_details(user_uuid)

    if(response.status_code == 200):
        return JsonResponse(pretty_json, status=status.HTTP_200_OK)
    elif(response.status_code == 400):
        return JsonResponse(pretty_json, status=status.HTTP_400_BAD_REQUEST)
    elif(response.status_code == 404):
        return JsonResponse(pretty_json, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(pretty_json)


@api_view(['POST'])
def Retry_charge(request, user_uuid):
    global cashfreeTestAPI

    if isUserSubscribed(user_uuid):
        return JsonResponse({'error': "the user does not have any subscription"},
                            status=status.HTTP_400_BAD_REQUEST)

    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    url = cashfreeTestAPI+"api/v2/subscriptions/" + \
        data.subReferenceId+"/charge-retry"

    clientinfo = clientInfo.objects.all()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-client-id": clientinfo[0].clientId,
        "x-client-secret": clientinfo[0].clientSecret,
        "x-api-version": "2021-05-21"
    }

    response = requests.request("POST", url, headers=headers)
    pretty_json = json.loads(response.text)
    print(pretty_json)
    update_user_subscription_details(user_uuid)
    if(response.status_code == 200):
        return JsonResponse(pretty_json, status=status.HTTP_200_OK)
    elif(response.status_code == 400):
        return JsonResponse(pretty_json, status=status.HTTP_400_BAD_REQUEST)
    elif(response.status_code == 404):
        return JsonResponse(pretty_json, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(pretty_json)
