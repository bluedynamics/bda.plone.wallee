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
from bda.plone.checkout.interfaces import ICheckoutAdapter
from bda.plone.payment import Payment
from bda.plone.payment import Payments
from bda.plone.payment.interfaces import IPaymentData
from bda.plone.shop.utils import get_shop_settings
from bda.plone.wallee import interfaces
from decimal import Decimal
from plone.registry.interfaces import IRegistry
from plone import api
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

import logging


_ = MessageFactory("bda.plone.wallee")


def get_wallee_settings():
    return getUtility(IRegistry).forInterface(interfaces.IWalleeSettings)


class WalleePayment(Payment):
    pid = "wallee_payment"
    label = _("wallee_payment", "Wallee Payment")
    clear_session = False


# class WalleeSettings:
#     @property
#     def space_id(self):
#         return get_wallee_settings().space_id

#     @property
#     def user_id(self):
#         return get_wallee_settings().user_id

#     @property
#     def api_secret(self):
#         return get_wallee_settings().api_secret


def wallee_checkout_lightbox(view, data):

    nav_root = api.portal.get_navigation_root(view)
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

    providers = [
        fields_factory(view.context, view.request)
        for fields_factory in view.provider_registry
    ]

    to_adapt = (view.context, view.request)
    checkout_adapter = getMultiAdapter(to_adapt, ICheckoutAdapter)

    cart_data = get_data_provider(view.context, view.request)

    form_data = view.request.form

    billing_address = {
        "gender": form_data.get("checkout.personal_data.gender", "").upper(),
        "givenName": form_data.get("checkout.personal_data.firstname", ""),
        "familyName": form_data.get("checkout.personal_data.lastname", ""),
        "organisationName": form_data.get("checkout.personal_data.company", ""),
        "emailAddress": form_data.get("checkout.personal_data.email", ""),
        "phoneNumber": form_data.get("checkout.personal_data.phone", ""),
        "street": form_data.get("checkout.billing_address.street", ""),
        "postCode": form_data.get("checkout.billing_address.zip", ""),
        "city": form_data.get("checkout.billing_address.city", ""),
        "country": form_data.get("checkout.billing_address.country", ""),
    }

    # shippingAddress = {
    #     "gender": "",
    #     "givenName": "Sam",
    #     "familyName": "Test",
    #     "emailAddress": "some-buyer@customweb.com",
    #     "mobilePhoneNumber": "",
    #     "organisationName": "customweb GmbH",
    #     "phoneNumber": "",
    #     "street": "General-Guisan-Strasse 47",
    #     "postCode": "8400",
    #     "city": "Winterthur",
    #     "country": "CH",
    #     # "salutation":"",
    # }

    cart_items = cart_data.data.get("cart_items", [])

    # create line items
    line_items = []
    # breakpoint()

    for item in cart_items:
        article = get_object_by_uid(view.context, item.get("cart_item_uid", ""))

        name = item.get("cart_item_title", "")
        if item.get("cart_item_comment", ""):
            name = f"{name} - {item['cart_item_discount']}"
        unique_id = item.get("cart_item_uid", "")
        sku = article.get("item_number", article.id)

        quantity = int(item.get("cart_item_count"))
        if item.get("quantity_unit_float", ""):
            quantity = float(item.get("cart_item_count"))

        amountIncludingTax = Decimal(item.get("cart_item_price", ""))

        if item.get("cart_item_discount", ""):
            amountIncludingTax = amountIncludingTax - Decimal(
                item["cart_item_discount"]
            )

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

    shipping = cart_data.shipping(checkout_adapter.items)
    if shipping and shipping.get("net", ""):

        net = shipping.get("net")
        vat = shipping.get("vat")

        amountIncludingTax = net + vat
        name = _("shipping", default="Shipping")
        quantity = 1

        # sku = needed?
        line_items.append(
            LineItem(
                name=name,
                unique_id="shipping",
                quantity=quantity,
                amount_including_tax=float(f"{amountIncludingTax:.2f}"),
                type=LineItemType.SHIPPING,
            )
        )

    discount = cart_data.discount(checkout_adapter.items)
    if discount and discount.get("net", ""):

        net = discount.get("net")
        vat = discount.get("vat")

        amountIncludingTax = (net + vat) * -1
        name = _("discount", default="Discount")
        quantity = 1

        # sku = needed?
        line_items.append(
            LineItem(
                name=name,
                unique_id="discount",
                quantity=quantity,
                amount_including_tax=float(f"{amountIncludingTax:.2f}"),
                type=LineItemType.DISCOUNT,
            )
        )

    # breakpoint()
    # create transaction model
    transaction = TransactionCreate(
        language=api.portal.get_current_language(),
        success_url=f"{base}/@@wallee_payment_success",
        failed_url=f"{base}/@@wallee_payment_failed",
        line_items=line_items,
        auto_confirmation_enabled=True,
        currency=cart_data.currency,
        billing_address=billing_address,
    )

    breakpoint()
    # try / except / catch error
    transaction_create = transaction_service.create(
        space_id=space_id, transaction=transaction
    )

    return transaction_lightbox_service_api.javascript_url(
        space_id, transaction_create.id
    )

    # payment_page_url = transaction_payment_page_service.payment_page_url(space_id=space_id, id=transaction_create.id)
    # redirect your customer to this payment_page_url


def wallee_lightbox_renderer(widget, data):
    view = widget.properties["view"]
    lightbox_url = wallee_checkout_lightbox(view, data)
    lightbox_script = f"<script src='{lightbox_url}' type='text/javascript'></script>"
    lightbox_init = """
        <script type="text/javascript">

            $(document).ready(function () {
                    $('#input-checkout-wallee_checkout_button').unbind()
                    $('#input-checkout-wallee_checkout_button').on('click', function(event){
                        event.preventDefault();
                        event.stopPropagation();
                        window.LightboxCheckoutHandler.startPayment(undefined, function(){
                                alert('An error occurred during the initialization of the payment lightbox.');
                            });
                    });
            });
        </script>
        """
    return lightbox_script + "\n" + lightbox_init


def wallee_checkout_button(view):
    # if not view.mode == "display":
    #     return

    lightbox_script = factory(
        "*wallee_lightbox",
        props={
            "class": "wallee_light_box",
            "view": view,
        },
        custom={
            "wallee_lightbox": {
                "edit_renderers": [wallee_lightbox_renderer],
                "display_renderers": [wallee_lightbox_renderer],
            }
        },
    )
    checkout_button = factory(
        "button",
        props={
            "text": _(
                "finish", "Order with Wallee now ${icon}", mapping={"icon": SVG_FINISH}
            ),
            "class": "btn btn-primary wallee-lightbox-payment",
            "type": "button",
        },
    )

    view.form["wallee_lightbox_script"] = lightbox_script
    view.form["wallee_checkout_button"] = checkout_button


confirmation_button_factories.append(wallee_checkout_button)
