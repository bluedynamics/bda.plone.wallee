from bda.plone.shop.interfaces import IShopSettingsProvider
from plone.supermodel import model
from zope import schema
from zope.i18nmessageid import MessageFactory
from zope.interface import provider

_ = MessageFactory("bda.plone.wallee")


@provider(IShopSettingsProvider)
class IWalleeSettings(model.Schema):
    """Wallee controlpanel schema.
    """

    model.fieldset(
        'wallee',
        label=_(u'Wallee', default=u'Wallee'),
        fields=[
            'space_id',
            'user_id',
            'api_secret',
        ],
    )

    space_id = schema.ASCIILine(
        title=_(u"label_secret_key", default=u'Space ID'),
        required=True,
        default=""
    )

    user_id = schema.ASCIILine(
        title=_(u"label_user_id", default=u'User ID'),
        required=True,
        default=""
    )

    api_secret = schema.ASCIILine(
        title=_(u"label_api_secret", default=u'API Secret'),
        required=True,
        default=""
    )
