from bda.plone.cart.cartitem import purge_cart
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


def wallee_checkout_lightbox(view):

    space_id = get_wallee_settings().space_id

    config = Configuration(
        user_id=get_wallee_settings().user_id,
        api_secret=get_wallee_settings().api_secret,
    )
    transaction_service = TransactionServiceApi(configuration=config)
    transaction_lightbox_service_api = TransactionLightboxServiceApi(configuration=config)

    providers = [
        fields_factory(view.context, view.request)
        for fields_factory in view.provider_registry
    ]

    to_adapt = (view.context, view.request)
    checkout_adapter = getMultiAdapter(to_adapt, ICheckoutAdapter)

    # create line item
    line_item = LineItem(
        name='Red T-Shirt',
        unique_id='5412',
        sku='red-t-shirt-123',
        quantity=1,
        amount_including_tax=29.95,
        type=LineItemType.PRODUCT
    )

    # create transaction model
    transaction = TransactionCreate(
        line_items=[line_item],
        auto_confirmation_enabled=True,
        currency='EUR',
    )

    transaction_create = transaction_service.create(
        space_id=space_id, transaction=transaction
    )

    return transaction_lightbox_service_api.javascript_url(space_id, transaction_create.id)

    # payment_page_url = transaction_payment_page_service.payment_page_url(space_id=space_id, id=transaction_create.id)
    # redirect your customer to this payment_page_url



def wallee_lightbox_renderer(widget, data):
    view = widget.properties["view"]
    lightbox_url = wallee_checkout_lightbox(view)
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
    wallee_checkout_lightbox(view)
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
