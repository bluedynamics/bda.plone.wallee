from bda.plone.cart.browser.portlet import SKIP_RENDER_CART_PATTERNS
from bda.plone.cart.cart import get_data_provider
from bda.plone.cart.cartitem import purge_cart
from bda.plone.cart.utils import get_catalog_brain
from bda.plone.cart.utils import get_object_by_uid
from bda.plone.checkout import CheckoutDone
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
from bda.plone.orders.datamanagers.order import OrderData
from bda.plone.payment import Payment
from bda.plone.payment import Payments
from bda.plone.payment.interfaces import IPaymentData
from bda.plone.shop.utils import get_shop_settings
from bda.plone.shop.utils import get_shop_shipping_settings
from bda.plone.wallee import interfaces
from plone import api
from plone.protect.utils import addTokenToUrl
from plone.registry.interfaces import IRegistry
from Products.Five import BrowserView
from wallee import Configuration
from wallee.api import TransactionLightboxServiceApi
from wallee.api import TransactionPaymentPageServiceApi
from wallee.api import TransactionServiceApi
from wallee.models import LineItem
from wallee.models import LineItemType
from wallee.models import Tax
from wallee.models import TransactionCreate
from yafowil.base import factory
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.event import notify
from zope.i18nmessageid import MessageFactory

import logging
import pycountry
import transaction


logger = logging.getLogger(__name__)
_ = MessageFactory("bda.plone.wallee")

SKIP_RENDER_CART_PATTERNS.append("@@wallee_payment")
SKIP_RENDER_CART_PATTERNS.append("@@wallee_payment_success")


def get_country_code(country_id):
    if not country_id:
        return None
    country = pycountry.countries.get(numeric=country_id)
    return country.alpha_2


def get_wallee_settings():
    return getUtility(IRegistry).forInterface(interfaces.IWalleeSettings)


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


class WalleePaymentLightbox(Payment):
    pid = "wallee_payment_lightbox"
    label = _("wallee_payment", "Wallee Payment Lightbox")
    clear_session = False

    def init_url(self, uid):
        return addTokenToUrl(
            "%s/@@wallee_payment?uid=%s" % (self.context.absolute_url(), uid)
        )


class WalleePaymentLightboxView(BrowserView, WalleeSettings):
    @property
    def shop_admin_mail(self):
        # This is a soft dependency indirection on bda.plone.shop
        entry = "bda.plone.shop.interfaces.IShopSettings.admin_email"
        shop_email = api.portal.get_registry_record(name=entry, default=None)
        if shop_email is not None:
            return shop_email
        logger.warning("No shop master email was set.")
        return "(no shopmaster email set)"

    @property
    def shop_admin_name(self):
        # This is a soft dependency indirection on bda.plone.shop
        entry = "bda.plone.shop.interfaces.IShopSettings.admin_name"
        shop_name = api.portal.get_registry_record(name=entry, default=None)
        if shop_name is not None:
            return shop_name
        logger.warning("No shop master name was set.")
        return "(no shopmaster name set)"

    def lightbox_script_url(self):

        order = OrderData(self.context, uid=self.request.get("uid"))
        order_data = order.order.attrs

        if order_data.get("personal_data.gender", "") not in ("male", "female"):
            gender = ""
        else:
            gender = order_data.get("personal_data.gender")

        billing_address = {
            "gender": gender.upper(),
            "givenName": order_data.get("personal_data.firstname", ""),
            "familyName": order_data.get("personal_data.lastname", ""),
            "organisationName": order_data.get("personal_data.company", ""),
            "emailAddress": order_data.get("personal_data.email", ""),
            "phoneNumber": order_data.get("personal_data.phone", ""),
            "street": order_data.get("billing_address.street", ""),
            "postCode": order_data.get("billing_address.zip", ""),
            "city": order_data.get("billing_address.city", ""),
            "country": get_country_code(order_data.get("billing_address.country", "")),
        }

        if order_data.get("delivery_address.alternative_delivery", ""):
            shipping_address = {
                "givenName": order_data.get("delivery_address.firstname", ""),
                "familyName": order_data.get("delivery_address.lastname", ""),
                "organisationName": order_data.get("delivery_address.company", ""),
                "street": order_data.get("delivery_address.street", ""),
                "postCode": order_data.get("delivery_address.zip", ""),
                "city": order_data.get("delivery_address.city", ""),
                "country": get_country_code(
                    order_data.get("delivery_address.country", "")
                ),
            }
        else:
            shipping_address = billing_address

        # create line items
        line_items = []

        for booking in order.bookings:
            booking_data = booking.attrs
            article = get_object_by_uid(self.context, booking_data["buyable_uid"])

            name = booking_data["title"]
            if booking_data.get("buyable_comment", ""):
                name = f"{name} - {booking_data['buyable_comment']}"
            unique_id = booking_data["buyable_uid"]

            sku = article.get("item_number", article.id)
            vat = booking_data["vat"]

            quantity = int(booking_data["buyable_count"])

            undiscounted_unit_price_excluding_tax = booking_data["net"]
            undiscounted_unit_price_including_tax = (
                undiscounted_unit_price_excluding_tax / 100 * (100 + vat)
            )

            unit_price_excluding_tax = (
                undiscounted_unit_price_excluding_tax - booking_data["discount_net"]
            )
            unit_price_including_tax = unit_price_excluding_tax / 100 * (100 + vat)

            undiscounted_amount_excluding_tax = (
                undiscounted_unit_price_excluding_tax * quantity
            )
            undiscounted_amount_including_tax = (
                undiscounted_unit_price_including_tax * quantity
            )

            amount_excluding_tax = unit_price_excluding_tax * quantity
            amount_including_tax = unit_price_including_tax * quantity

            tax_type = _("tax_type", default="Vat.")
            taxes = []
            taxes.append(
                Tax(
                    title=api.portal.translate(tax_type),
                    rate=float(booking_data["vat"]),
                )
            )

            tax_amount_per_unit = unit_price_excluding_tax / 100 * vat
            tax_amount = amount_excluding_tax / 100 * vat

            line_items.append(
                LineItem(
                    name=name,
                    unique_id=unique_id,
                    sku=sku,
                    quantity=quantity,
                    undiscounted_unit_price_excluding_tax=float(
                        f"{undiscounted_unit_price_excluding_tax:.2f}"
                    ),
                    undiscounted_unit_price_including_tax=float(
                        f"{undiscounted_unit_price_including_tax:.2f}"
                    ),
                    unit_price_excluding_tax=float(f"{unit_price_excluding_tax:.2f}"),
                    unit_price_including_tax=float(f"{unit_price_including_tax:.2f}"),
                    undiscounted_amount_excluding_tax=float(
                        f"{undiscounted_amount_excluding_tax:.2f}"
                    ),
                    undiscounted_amount_including_tax=float(
                        f"{undiscounted_amount_including_tax:.2f}"
                    ),
                    amount_including_tax=float(f"{amount_including_tax:.2f}"),
                    amount_excluding_tax=float(f"{amount_excluding_tax:.2f}"),
                    aggregated_tax_rate=float(vat),
                    tax_amount_per_unit=float(f"{tax_amount_per_unit:.2f}"),
                    tax_amount=float(f"{tax_amount:.2f}"),
                    taxes=taxes,
                    type=LineItemType.PRODUCT,
                )
            )

        if "shipping" in order_data and order_data["shipping"]:

            name = _("shipping", default="Shipping")
            quantity = 1

            settings = get_shop_shipping_settings()

            taxes = []
            taxes.append(
                Tax(
                    title=api.portal.translate(tax_type),
                    rate=float(settings.shipping_vat),
                )
            )

            line_items.append(
                LineItem(
                    name=api.portal.translate(name),
                    unique_id="shipping",
                    quantity=quantity,
                    aggregated_tax_rate=float(order_data["shipping_vat"]),
                    amount_excluding_tax=float(f"{order_data['shipping_net']:.2f}"),
                    amount_including_tax=float(f"{order_data['shipping']:.2f}"),
                    taxes=taxes,
                    type=LineItemType.SHIPPING,
                )
            )

        if "cart_discount_net" in order_data and order_data["cart_discount_net"]:

            net = order_data["cart_discount_net"]
            vat = order_data["cart_discount_vat"]

            amountIncludingTax = (net + vat) * -1
            name = _("cart_discount", default="Discount")
            quantity = 1

            line_items.append(
                LineItem(
                    name=api.portal.translate(name),
                    unique_id="cart_discount",
                    quantity=quantity,
                    amount_including_tax=float(f"{amountIncludingTax:.2f}"),
                    type=LineItemType.DISCOUNT,
                )
            )

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

        # create transaction model
        transaction = TransactionCreate(
            language=api.portal.get_current_language(),
            currency=order.currency,
            line_items=line_items,
            billing_address=billing_address,
            shipping_address=shipping_address,
            merchant_reference=order_data["ordernumber"],
        )

        # create transaction with transaction_service
        try:
            transaction = transaction_service.create(
                space_id=space_id, transaction=transaction
            )
        except Exception:
            logger.exception(
                "Could not create transaction and initalize wallee lightbox"
            )
            self.request.response.redirect(
                f"{self.context.absolute_url()}/@@wallee_error"
            )

        transaction.success_url = addTokenToUrl(
            f"{base}/@@wallee_payment_success/?order_uid={str(order.uid)}&transaction_id={transaction.id}"
        )

        transaction.failed_url = addTokenToUrl(
            f"{base}/@@wallee_payment_failed/?order_uid={str(order.uid)}&transaction_id={transaction.id}"
        )

        # update transaction with transaction_service
        try:
            transaction_service.update(
                space_id=space_id,
                entity=transaction,
            )
        except Exception:
            logger.exception("Could not update transaction for wallee lightbox")
            self.request.response.redirect(
                f"{self.context.absolute_url()}/@@wallee_error"
            )

        return transaction_lightbox_service_api.javascript_url(space_id, transaction.id)


class TransactionView(BrowserView, WalleeSettings):
    """Handling of Wallee Transaction Respone"""

    @property
    def transaction(self):
        if "transaction_id" in self.request:
            transaction_id = self.request.get("transaction_id")

            config = Configuration(user_id=self.user_id, api_secret=self.api_secret)
            transaction_service = TransactionServiceApi(configuration=config)
            transaction = transaction_service.read(
                space_id=self.space_id, id=transaction_id
            )
            return transaction

    @property
    def message(self):
        try:
            return self.transaction.user_failure_message
        except:
            logger.warn("Could not extract user_failure_message")

    def status(self):
        try:
            return self.transaction.state
        except:
            logger.warn("Could not extract user_failure_message")


class TransactionSuccessView(TransactionView):
    """On Success empty cart & mark order as salaried"""

    def status_update(self):
        if "order_uid" in self.request and "transaction_id" in self.request:
            transaction_id = self.request.get("transaction_id")
            order_uid = self.request.get("order_uid")
            order = OrderData(self.context, order_uid)
            order_tid = order.tid.pop()
            if order_tid == transaction_id:
                order.salaried = "yes"
                purge_cart(self.request)
            return order.salaried
