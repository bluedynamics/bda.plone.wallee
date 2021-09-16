from bda.plone.shop.interfaces import IShopSettingsProvider
from plone.supermodel import model
from zope import schema
from zope.i18nmessageid import MessageFactory
from zope.interface import provider


_ = MessageFactory("bda.plone.wallee")


@provider(IShopSettingsProvider)
class IWalleeSettings(model.Schema):
    """Wallee controlpanel schema."""

    model.fieldset(
        "wallee",
        label=_("Wallee", default="Wallee"),
        fields=[
            "space_id",
            "user_id",
            "api_secret",
        ],
    )

    space_id = schema.ASCIILine(
        title=_("label_secret_key", default="Space ID"), required=True, default=""
    )

    user_id = schema.ASCIILine(
        title=_("label_user_id", default="User ID"), required=True, default=""
    )

    api_secret = schema.ASCIILine(
        title=_("label_api_secret", default="API Secret"), required=True, default=""
    )
