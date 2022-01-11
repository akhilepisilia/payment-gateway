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


# each uuid should have only one subscription only or one should be compleated or canceled  safe=False

#not using
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

    url = cashfreeTestAPI+"api/v2/subscriptions/"+data.subReferenceId

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
    if(response.status_code == 200):
        data.status = pretty_json['subscription']['status']
        data.currentCycle = pretty_json['subscription']['currentCycle']
        data.save()
        return True
    else:
        return False


def getSubscription(user_uuid):

    update_user_subscription_details(user_uuid)

    data = SubscriptionData.objects.get(user_uuid=user_uuid)

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

    return subscriptiondata


def createsubscription(user_uuid, subscriptionId, planId):

    global cashfreeTestAPI
    # SubscriptionData.objects.filter(user_uuid=user_uuid).exists()
    matchUser = User.objects.filter(user_uuid=user_uuid)
    res = matchUser[0]

    url = cashfreeTestAPI + "api/v2/subscriptions"

    expiresOn = (datetime.now()+timedelta(days=730)
                 ).strftime("%Y-%m-%d %H:%M:%S")
    addedon = (datetime.now()+timedelta(days=0)).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "subscriptionId":   subscriptionId,
        "planId":   planId,
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
            subscriptionId=subscriptionId,
            planId=planId,
            expiresOn=expiresOn,
            subReferenceId=pretty_json['subReferenceId'],
            status=pretty_json['subStatus'],
            addedon=addedon,
            authLink=pretty_json['authLink'],
            currentCycle=0
        )
        try:
            data.save()
            update_user_subscription_details(user_uuid)
            return True
        except Exception as e:
            print({'error': e})
            return False
    else:
        return pretty_json

# we need to inisate it


def chargesubscription(user_uuid, amount, scheduledOn):

    global cashfreeTestAPI

    data = SubscriptionData.objects.get(user_uuid=user_uuid)

    url = cashfreeTestAPI+"api/v2/subscriptions/"+data.subReferenceId+"/charge"

    payload = {
        "amount": amount,
        # (datetime.now()+timedelta(days=5)).strftime("%Y-%m-%d"),
        "scheduledOn": scheduledOn,
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
            return {'subCode': '200', 'paymentId': pretty_json['payment']['paymentId']}
        except Exception as e:
            print({'error': e})
            return False

    else:
        return pretty_json


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


def getsubscriptionpayment(user_uuid):
    #paymentdata = [obj for obj in PaymentData.objects.values()]
    data = SubscriptionData.objects.get(user_uuid=user_uuid)
    matchUser = PaymentData.objects.filter(subReferenceId=data.subReferenceId)
    if not matchUser:
        return []

    resData = []
    for obj in PaymentData.objects.values():
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
    return resData


def cancelsubscription(user_uuid):
    global cashfreeTestAPI

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
    if(response.status_code == 200):
        update_user_subscription_details(user_uuid)
        try:
            data.delete()
            return True
        except Exception as e:
            print(e)
            return False

    else:
        return pretty_json


def cancelcharge(user_uuid, paymentId):

    global cashfreeTestAPI

    data = SubscriptionData.objects.get(user_uuid=user_uuid)

    url = cashfreeTestAPI+"api/v2/subscription/" + \
        data.subReferenceId+"/charge/"+paymentId+"/cancel"

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

    if(response.status_code == 200):
        update_user_subscription_details(user_uuid)
        return True
    else:
        return pretty_json


def retrycharge(user_uuid):

    global cashfreeTestAPI

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
    if(response.status_code == 200):
        update_user_subscription_details(user_uuid)
        return True
    else:
        return pretty_json
