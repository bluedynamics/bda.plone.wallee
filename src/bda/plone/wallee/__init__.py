# -*- coding: utf-8 -*-
"""Init and utils."""
from zope.i18nmessageid import MessageFactory
from Products.Five import BrowserView
from bda.plone.cart.cartitem import purge_cart
from bda.plone.payment import Payment
from bda.plone.payment import Payments
from bda.plone.payment.interfaces import IPaymentData
from bda.plone.shop.utils import get_shop_settings
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from bda.plone.wallee import interfaces
import logging

_ = MessageFactory("bda.plone.wallee")


def get_wallee_settings():
    return getUtility(IRegistry).forInterface(interfaces.IWalleeSettings)


class WalleePayment(Payment):
    pid = 'wallee_payment'
    label = _('wallee_payment', 'Wallee Payment')
    clear_session = False


class WalleeSettings(object):

    @property
    def space_id(self):
        return get_wallee_settings().space_id

    @property
    def user_id(self):
        return get_wallee_settings().user_id

    @property
    def api_secret(self):
        return get_wallee_settings().api_secret
