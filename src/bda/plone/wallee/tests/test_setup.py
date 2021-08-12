# -*- coding: utf-8 -*-
"""Setup tests for this package."""
import unittest

from plone import api
from plone.app.testing import TEST_USER_ID, setRoles

from bda.plone.wallee.testing import BDA_PLONE_WALLEE_INTEGRATION_TESTING  # noqa: E501

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


class TestSetup(unittest.TestCase):
    """Test that bda.plone.wallee is properly installed."""

    layer = BDA_PLONE_WALLEE_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        if get_installer:
            self.installer = get_installer(self.portal, self.layer['request'])
        else:
            self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if bda.plone.wallee is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'bda.plone.wallee'))

    def test_browserlayer(self):
        """Test that IBdaPloneWalleeLayer is registered."""
        from plone.browserlayer import utils

        from bda.plone.wallee.interfaces import IBdaPloneWalleeLayer
        self.assertIn(
            IBdaPloneWalleeLayer,
            utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = BDA_PLONE_WALLEE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        if get_installer:
            self.installer = get_installer(self.portal, self.layer['request'])
        else:
            self.installer = api.portal.get_tool('portal_quickinstaller')
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.installer.uninstallProducts(['bda.plone.wallee'])
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if bda.plone.wallee is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'bda.plone.wallee'))

    def test_browserlayer_removed(self):
        """Test that IBdaPloneWalleeLayer is removed."""
        from plone.browserlayer import utils

        from bda.plone.wallee.interfaces import IBdaPloneWalleeLayer
        self.assertNotIn(IBdaPloneWalleeLayer, utils.registered_layers())
