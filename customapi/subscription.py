from .models import SubscriptionData, PaymentData, User, clientInfo
import json
import requests
from datetime import datetime, timedelta
import math
# Create your views here.


cashfreeTestAPI = "https://test.cashfree.com/"


# each uuid should have only one subscription only or one should be compleated or canceled  safe=False

# used to check for if user has an active subscription
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


# used to get subscription_id  if user has an active subscription
def getcurrentsubscriptionID(user_uuid):
    data = SubscriptionData.objects.filter(user_uuid=user_uuid)
    for obj in data:
        if (obj.status == 'INITIALIZED' or obj.status == 'ACTIVE' or obj.status == 'BANK_APPROVAL_PENDING' or obj.status == 'ON_HOLD'):
            return obj.subscriptionId

    return False


# used to get all the subReferenceId  for the user
def getallsubReferenceId(user_uuid):
    data = SubscriptionData.objects.filter(user_uuid=user_uuid)
    res = []
    for obj in data:
        res.append(obj.subReferenceId)

    return res

# update user subscription details if user has a active subscription


def update_user_subscription_details(user_uuid):

    global cashfreeTestAPI
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)

    url = cashfreeTestAPI+"api/v2/subscriptions/"+str(data.subReferenceId)

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


# used to make a subscriptionId
"""
def genSubscriptionId(user_uuid, i=1):
    count = SubscriptionData.objects.filter(user_uuid=user_uuid).count()
    sub = User.objects.get(user_uuid=user_uuid)
    if count != 0:
        sub1 = SubscriptionData.objects.filter(
            user_uuid=user_uuid).order_by('subscriptionId').last()
        word = sub1.subscriptionId
        li = word.split('_')
        return sub.client_id + "_" + str(int(li[1])+i)
    else:
        return sub.client_id + "_" + str(i)
"""


def genSubscriptionId(user_uuid):
    sub = User.objects.get(user_uuid=user_uuid)
    ct = datetime.now()
    ts = ct.timestamp()
    truncA = math.trunc(ts)
    return sub.client_id + "_" + str(truncA)

#  used to get activeg user_subscription_details from DB


def getSubscription(user_uuid):
    update_user_subscription_details(user_uuid)
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)

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


#  used for getting all user subscription details from DB
def getAllSubscription(user_uuid):

    data = SubscriptionData.objects.filter(user_uuid=user_uuid)
    resdata = []
    for obj in data:
        subscriptiondata = {
            "subscriptionId":   obj.subscriptionId,
            "subReferenceId": obj.subReferenceId,
            "planId":    obj.planId,
            "status":   obj.status,
            "addedon": obj.addedon,
            "expiresOn":  obj.expiresOn,
            "authLink": obj.authLink,
            "currentCycle": obj.currentCycle
        }
        resdata.append(subscriptiondata)

    return resdata

# used to create subscription if user does not have any active subscription


def createsubscription(user_uuid, planId):

    global cashfreeTestAPI
    # SubscriptionData.objects.filter(user_uuid=user_uuid).exists()
    matchUser = User.objects.filter(user_uuid=user_uuid)
    res = matchUser[0]

    url = cashfreeTestAPI + "api/v2/subscriptions"

    trunc = math.trunc(datetime.now().timestamp())
    subscriptionId = res.client_id + "_" + str(trunc)

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
        "authAmount": 1,
        "notificationChannels": ["EMAIL", "SMS"]
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
            return "True"
        except Exception as e:
            print({'error': e})
            return False

    elif(response.status_code == 400 and "Subscription already present for SubscriptionId" in pretty_json["message"]):

        createsubscription(user_uuid, planId)

    else:
        return pretty_json


# used to charge subscription if user has an active subscription
def chargesubscription(user_uuid, amount, scheduledOn):

    global cashfreeTestAPI
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)

    url = cashfreeTestAPI+"api/v2/subscriptions/" + \
        str(data.subReferenceId)+"/charge"

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

#  used to update subscription payment details


def update_subscription_payment_details(user_uuid, subReferenceId, paymentId):
    global cashfreeTestAPI
    print(subReferenceId)
    paymentdata = PaymentData.objects.get(paymentId=paymentId)

    url = cashfreeTestAPI+"api/v2/subscriptions/" + \
        str(subReferenceId) + "/payments/"+str(paymentId)

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

# used to update all subscriptions payments details under user will skip if payment status = CANCELLED


def update_all_subscription_payment_details(user_uuid):
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)
    for obj in PaymentData.objects.values():
        if (obj['subReferenceId_id'] == data.subReferenceId):
            if (not obj['paymentstatus'] == 'CANCELLED'):
                update_subscription_payment_details(
                    user_uuid, data.subReferenceId, obj['paymentId'])

# used to get  all  payment details  under active subscription


def getsubscriptionpayment(user_uuid):
    #paymentdata = [obj for obj in PaymentData.objects.values()]
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)
    matchUser = PaymentData.objects.filter(subReferenceId=data.subReferenceId)
    if not matchUser:
        return []

    resData = []
    update_all_subscription_payment_details(user_uuid)
    for obj in PaymentData.objects.values():
        if (obj['subReferenceId_id'] == data.subReferenceId):
            print(obj)
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
    return resData

# used to get  all  payment details  under all the  subscriptions user has


def getallsubscriptionpayment(user_uuid):
    #paymentdata = [obj for obj in PaymentData.objects.values()]
    subReferenceId = getallsubReferenceId(user_uuid)

    resData = []
    for subRefId in subReferenceId:
        data = SubscriptionData.objects.get(
            user_uuid=user_uuid, subReferenceId=subRefId)

        res = []
        for obj in PaymentData.objects.values():
            if (obj['subReferenceId_id'] == data.subReferenceId):
                if (not obj['paymentstatus'] == 'CANCELLED'):
                    update_subscription_payment_details(
                        user_uuid, data.subReferenceId, obj['paymentId'])
                paymentData = {
                    'subReferenceId': obj['subReferenceId_id'],
                    'paymentId': obj['paymentId'],
                    'scheduledOn': obj['scheduledOn'],
                    'initiatedOn': obj['initiatedOn'],
                    'amount': obj['amount'],
                    'paymentstatus': obj['paymentstatus'],
                    'retryAttempts': obj['retryAttempts']
                }
                res.append(paymentData)

        subscriptiondata = {
            'subscriptionId': data.subscriptionId,
            'subReferenceId': data.subReferenceId,
            'planId': data.planId,
            'addedon': data.addedon,
            "expiresOn": data.expiresOn,
            "status": data.status,
            'payment': res
        }
        resData.append(subscriptiondata)

    return resData


# used to cancel subscription if user has an active subscription
def cancelsubscription(user_uuid):
    global cashfreeTestAPI
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)
    url = cashfreeTestAPI+"api/v2/subscriptions/" + \
        str(data.subReferenceId)+"/cancel"

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

# used to cancel charge for subscription if user has an active subscription


def cancelcharge(user_uuid, paymentId):

    global cashfreeTestAPI
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)

    url = cashfreeTestAPI+"api/v2/subscription/" + \
        str(data.subReferenceId)+"/charge/"+paymentId+"/cancel"

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

# used to retry charge for subscription if user has an active subscription and if charge does not proceed


def retrycharge(user_uuid):

    global cashfreeTestAPI
    subscriptionId = getcurrentsubscriptionID(user_uuid)
    data = SubscriptionData.objects.get(
        user_uuid=user_uuid, subscriptionId=subscriptionId)

    url = cashfreeTestAPI+"api/v2/subscriptions/" + \
        str(data.subReferenceId)+"/charge-retry"

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
