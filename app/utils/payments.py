from datetime import datetime, timedelta
import uuid
import enum
import base64
import httpx
import logging
import asyncio
import traceback

from bson import ObjectId
from app.utils.mongodb import MongoDB
from app.routers import safe_warnings_hook

client = httpx.AsyncClient()

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    WAITING_FOR_CAPTURE = "waiting_for_capture"

class YookassaApiException(Exception):
    pass
class InvalidRequestException(YookassaApiException):
    type: str
    id: str
    code: str
    description: str
    parameter: str

    def __init__(self, type, id, code, description, parameter) -> None:
        self.type = type
        self.id = id
        self.code = code
        self.description = description
        self.parameter = parameter
    
class YookassaPayment():    
    id: str
    status: PaymentStatus
    url: str
    def __init__(self, id, status, url) -> None:
        self.id = id
        self.status = PaymentStatus(status)
        self.url = url

    def __str__(self) -> str:
        return f'{self.id} {self.status.value} {self.url}'

class YookassaApi():
    __authorization: str

    @classmethod
    def setup(cls, account_id, secret_key):
        b = f'{account_id}:{secret_key}'.encode()
        cls.__authorization = "Basic " + base64.b64encode(b).decode("utf-8")

    @classmethod
    async def cancel_payment(cls, payment_id: str):
        idempotence_key = uuid.uuid4()
        print(payment_id)
        result = await client.post(
            url=f'https://api.yookassa.ru/v3/payments/{payment_id}/cancel',
            headers={
                "Authorization": cls.__authorization,
                "Idempotence-Key": str(idempotence_key),
                "Content-Type": "application/json"
            }
        )
        print(result.text)

    @classmethod
    async def get_succeeded_payments(cls):
        idempotence_key = uuid.uuid4()
        response = await client.get(
            url='https://api.yookassa.ru/v3/payments?limit=20&status=succeeded',
            headers={
                "Authorization": cls.__authorization,
                "Idempotence-Key": str(idempotence_key),
                "Content-Type": "application/json"
            }
        )
        return response

    @classmethod
    async def create_payment(
        cls,
        value: float,
        product_name: str,
        customer_email: str = "test@mail.ru",
        currency: str = 'RUB',
        redirect_url: str = "https://www.studgpt.ru/"
    ) -> YookassaPayment:
        idempotence_key = uuid.uuid4()
        response = await client.post(
            url='https://api.yookassa.ru/v3/payments',
            headers={
                "Authorization": cls.__authorization,
                "Idempotence-Key": str(idempotence_key),
                "Content-Type": "application/json"
            },
            json={
                "test": True,
                "amount": {
                    "value": value,
                    "currency": currency
                },
                "capture": True,
                "receipt": {
                    "customer": {
                        "email": customer_email
                    },
                    "items": [
                        {
                            "description": product_name,
                            "amount": {
                                "value": value,
                                "currency": currency
                            },
                            "vat_code": 1,
                            "quantity": 1
                        }
                    ]
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": redirect_url
                }
            }
        )
        data = response.json()
        if response.status_code == 400:
            raise InvalidRequestException(**data)
        return YookassaPayment(
            id=data.get('id'), 
            status=data.get('status'),
            url=data.get('confirmation').get('confirmation_url')
        )
    
    @classmethod
    async def get_payment(
        cls,
        payment_id: str
    ) -> YookassaPayment:
        idempotence_key = uuid.uuid4()
        response = await client.get(
            url=f'https://api.yookassa.ru/v3/payments/{payment_id}',
            headers={
                "Authorization": cls.__authorization,
                "Idempotence-Key": str(idempotence_key),
                "Content-Type": "application/json"
            }
        )
        data = response.json()
        if response.status_code == 400:
            raise InvalidRequestException(**data)
        print("expires_at", data.get('expires_at'))
        return YookassaPayment(
            id=data.get('id'), 
            status=data.get('status'),
            url=data.get('confirmation', dict()).get('confirmation_url')
        )

status_changed_handlers = []

def register_payment_status_changed_handler(handler):
    global status_changed_handlers
    status_changed_handlers.append(handler)

async def create_subscription_payment(
    user_id: str,
    subscription_id: ObjectId,
    customer_email: str = "test@mail.ru",
    redirect_url: str = "https://www.studgpt.ru/"
) -> YookassaPayment:
    sub = await MongoDB.get_subscription_by_id(ObjectId(subscription_id))
    product_name = sub.get('name')
    price = sub.get('price')
    payment =  await YookassaApi.create_payment(
        value=price,
        product_name=f"{product_name} подписка StudGPT",
        customer_email=customer_email,
        currency='RUB',
        redirect_url=redirect_url
    )
    await MongoDB.insert_payment(
        user_id=user_id,
        payment_id=payment.id,
        status=payment.status.value,
        product=product_name,
        price=price
    )
    return payment

async def check_payment_loop():
    while True:
        try:
            payments = await YookassaApi.get_succeeded_payments()
            for payment in payments.json()['items']:
                db_payment = await MongoDB.db.payments.find_one({"payment_id": payment['id']})
                if not db_payment:
                    continue
                if db_payment.get('status') == payment.get('status'):
                    continue
                await MongoDB.update_payment(
                    payment_id=payment['id'],
                    status='succeeded'
                )
                db_payment['status'] = 'succeeded'
                for handler in status_changed_handlers:
                    await handler(db_payment)
        except Exception as e:
            print(e)
        await asyncio.sleep(10)