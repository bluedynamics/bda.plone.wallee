"""Setup tests for this package."""
from bda.plone.wallee.testing import BDA_PLONE_WALLEE_INTEGRATION_TESTING  # noqa: E501
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


class TestSetup(unittest.TestCase):
    """Test that bda.plone.wallee is properly installed."""

    layer = BDA_PLONE_WALLEE_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")

    def test_product_installed(self):
        """Test if bda.plone.wallee is installed."""
        self.assertTrue(self.installer.isProductInstalled("bda.plone.wallee"))


class TestUninstall(unittest.TestCase):

    layer = BDA_PLONE_WALLEE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstallProducts(["bda.plone.wallee"])
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if bda.plone.wallee is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled("bda.plone.wallee"))
