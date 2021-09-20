from bda.plone.cart.browser.portlet import SKIP_RENDER_CART_PATTERNS
from bda.plone.cart.cartitem import purge_cart
from bda.plone.cart.cart import get_data_provider
from bda.plone.cart.utils import get_catalog_brain
from bda.plone.cart.utils import get_object_by_uid
from bda.plone.checkout.browser.form import checkout_button_factories
from bda.plone.checkout.browser.form import confirmation_button_factories
from bda.plone.checkout.browser.form import FieldsProvider
from bda.plone.checkout.browser.form import provider_registry
from bda.plone.checkout.browser.form import (
    provider_registry as checkout_provider_registry,
)
from bda.plone.checkout.browser.form import SVG_FINISH
from bda.plone.checkout.interfaces import CheckoutError
from bda.plone.checkout.interfaces import ICheckoutAdapter
from bda.plone.checkout.interfaces import ICheckoutSettings
from bda.plone.checkout import CheckoutDone
from bda.plone.payment import Payment
from bda.plone.payment import Payments
from bda.plone.payment.interfaces import IPaymentData
from bda.plone.orders.datamanagers.order import OrderData
from bda.plone.shop.utils import get_shop_settings
from bda.plone.wallee import interfaces
from decimal import Decimal
from plone.registry.interfaces import IRegistry
from plone import api
from plone.protect.utils import addTokenToUrl
from Products.Five import BrowserView
from wallee import Configuration
from wallee.api import TransactionLightboxServiceApi
from wallee.api import TransactionPaymentPageServiceApi
from wallee.api import TransactionServiceApi
from wallee.models import LineItem
from wallee.models import LineItemType
from wallee.models import TransactionCreate
from yafowil.base import factory
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18nmessageid import MessageFactory
from zope.event import notify

import transaction
import logging


_ = MessageFactory("bda.plone.wallee")

SKIP_RENDER_CART_PATTERNS.append('@@wallee_payment')
SKIP_RENDER_CART_PATTERNS.append('@@wallee_payment_success')
# SKIP_RENDER_CART_PATTERNS.append('@@wallee_payment_failed')


def get_wallee_settings():
    return getUtility(IRegistry).forInterface(interfaces.IWalleeSettings)


class WalleePaymentLightbox(Payment):
    pid = "wallee_payment_lightbox"
    label = _("wallee_payment", "Wallee Payment Lightbox")
    clear_session = False


    def init_url(self, uid):
        return addTokenToUrl('%s/@@wallee_payment?uid=%s' % (self.context.absolute_url(), uid))


class WalleeSettings:

    @property
    def space_id(self):
        return get_wallee_settings().space_id

    @property
    def user_id(self):
        return get_wallee_settings().user_id

    @property
    def api_secret(self):
        return get_wallee_settings().api_secret


class WalleePaymentLightboxView(BrowserView, WalleeSettings):

    def lightbox_script_url(self):
        breakpoint()
        
        order = OrderData(self.context, uid=self.request.get("uid"))
        order_data = order.order.attrs

        billing_address = {
            "gender": order_data.get("personal_data.gender", "").upper(),
            "givenName": order_data.get("personal_data.firstname", ""),
            "familyName": order_data.get("personal_data.lastname", ""),
            "organisationName": order_data.get("personal_data.company", ""),
            "emailAddress": order_data.get("personal_data.email", ""),
            "phoneNumber": order_data.get("personal_data.phone", ""),
            "street": order_data.get("billing_address.street", ""),
            "postCode": order_data.get("billing_address.zip", ""),
            "city": order_data.get("billing_address.city", ""),
            "country": order_data.get("billing_address.country", ""),
        }

        if order_data.get("delivery_address.alternative_delivery", ""):
            shipping_address = {
                # "gender": order_data.get("checkout.personal_data.gender", "").upper(),
                "givenName": order_data.get("delivery_address.firstname", ""),
                "familyName": order_data.get("delivery_address.lastname", ""),
                "organisationName": order_data.get("delivery_address.company", ""),
                # "emailAddress": order_data.get("checkout.personal_data.email", ""),
                # "phoneNumber": order_data.get("checkout.personal_data.phone", ""),
                "street": order_data.get("delivery_address.street", ""),
                "postCode": order_data.get("delivery_address.zip", ""),
                "city": order_data.get("delivery_address.city", ""),
                "country": order_data.get("delivery_address.country", ""),
            }
        else:
            shipping_address = billing_address


        # create line items
        line_items = []
        breakpoint()

        for booking in order.bookings:
            booking_data = booking.attrs
            article = get_object_by_uid(self.context, booking_data["buyable_uid"])

            name = booking_data["title"]
            if booking_data.get("buyable_comment", ""):
                name = f"{name} - {booking_data['buyable_comment']}"
            unique_id = booking_data["buyable_uid"]

            sku = article.get("item_number", article.id)

            quantity = int(booking_data["buyable_count"])
            # if booking.get("quantity_unit_float", ""):
            #     quantity = float(booking.get("cart_item_count"))

            # amountIncludingTax = booking_data.get("cart_item_price", ""))
            amountIncludingTax = booking_data["net"] + (booking_data["net"] / 100 * booking_data["vat"])

            if booking_data.get("cart_item_discount", ""):
                discounted_net = booking_data["net"] - booking_data["discount_net"]
                amountIncludingTax = discounted_net + (discounted_net / 100 * booking_data["vat"])

            line_items.append(
                LineItem(
                    name=name,
                    unique_id=unique_id,
                    sku=sku,
                    quantity=quantity,
                    amount_including_tax=float(f"{amountIncludingTax:.2f}"),
                    type=LineItemType.PRODUCT,
                )
            )

        # static line_item
        # line_items.append(
        #     LineItem(
        #         name="Red T-Shirt",
        #         unique_id="5412",
        #         sku="red-t-shirt-123",
        #         quantity=1,
        #         amount_including_tax=29.95,
        #         type=LineItemType.PRODUCT,
        #     )
        # )

        if "shipping" in order_data and order_data["shipping"]:

            # net = shipping.get("net")
            # vat = shipping.get("vat")

            # amountIncludingTax = net + vat
            name = _("shipping", default="Shipping")
            quantity = 1

            # sku = needed?
            line_items.append(
                LineItem(
                    name=name,
                    unique_id="shipping",
                    quantity=quantity,
                    amount_including_tax=float(f"{order_data['shipping']:.2f}"),
                    type=LineItemType.SHIPPING,
                )
            )

        if "cart_discount_net" in order_data and order_data["cart_discount_net"]:

            net = order_data["cart_discount_net"]
            vat = order_data["cart_discount_vat"]

            amountIncludingTax = (net + vat) * -1
            name = _("cart_discount", default="Discount")
            quantity = 1

            # sku = needed?
            line_items.append(
                LineItem(
                    name=name,
                    unique_id="cart_discount",
                    quantity=quantity,
                    amount_including_tax=float(f"{amountIncludingTax:.2f}"),
                    type=LineItemType.DISCOUNT,
                )
            )

        breakpoint()

        nav_root = api.portal.get_navigation_root(self)
        base = nav_root.absolute_url()
        space_id = get_wallee_settings().space_id

        config = Configuration(
            user_id=get_wallee_settings().user_id,
            api_secret=get_wallee_settings().api_secret,
        )
        transaction_service = TransactionServiceApi(configuration=config)
        transaction_lightbox_service_api = TransactionLightboxServiceApi(
            configuration=config
        )

        # create minimal transaction model
        transaction = TransactionCreate(
            language=api.portal.get_current_language(),
            currency=order.currency,
        )

        # breakpoint()
        transaction_create = transaction_service.create(
            space_id=space_id, transaction=transaction
        )


        transaction_id = transaction_create.id


        # create transaction model
        transaction = TransactionCreate(
            id=transaction_id,
            merchant_reference=str(order.uid),
            language=api.portal.get_current_language(),
            success_url=addTokenToUrl(f"{base}/@@wallee_payment_success/?order_uid={str(order.uid)}&transaction_id={transaction_id}"),
            failed_url=addTokenToUrl(f"{base}/@@wallee_payment_failed/?order_uid={str(order.uid)}&transaction_id={transaction_id}"),
            line_items=line_items,
            # auto_confirmation_enabled=True,
            currency=order.currency,
            billing_address=billing_address,
            shipping_address=shipping_address,
        )

        transaction_service.update(space_id=space_id, entity=transaction_create)

        # try / except / catch error
        transaction_create = transaction_service.create(
            space_id=space_id, transaction=transaction
        )

        # transaction_id = transaction_create.id
        # transaction_service.read(space_id=space_id, id=transaction_id)
        # transaction.success_url = f"{transaction.success_url}/transaction_id={transaction_id}"
        # transaction.failed_url = f"{transaction.failed_url}/transaction_id={transaction_id}"

        print(transaction)
        order.tid = transaction_id
        # breakpoint()

        return transaction_lightbox_service_api.javascript_url(
            space_id, transaction_create.id
        )


class TransactionView(BrowserView, WalleeSettings):
    """Handling of Wallee Transaction Respone"""

    @property
    def message(self):
        if "transaction_id" in self.request:
            transaction_id = self.request.get("transaction_id")

            config = Configuration(
                user_id=self.user_id,
                api_secret=self.api_secret
            )
            transaction_service = TransactionServiceApi(configuration=config)
            transaction = transaction_service.read(space_id=self.space_id, id=transaction_id)

        print(transaction)
        breakpoint()
        return transaction
