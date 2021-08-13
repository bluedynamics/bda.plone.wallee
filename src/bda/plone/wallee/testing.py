from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import (
    FunctionalTesting,
    IntegrationTesting,
    PloneSandboxLayer,
    applyProfile,
)
from plone.testing import z2

import bda.plone.wallee


class BdaPloneWalleeLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.restapi

        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=bda.plone.wallee)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "bda.plone.wallee:default")


BDA_PLONE_WALLEE_FIXTURE = BdaPloneWalleeLayer()


BDA_PLONE_WALLEE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(BDA_PLONE_WALLEE_FIXTURE,),
    name="BdaPloneWalleeLayer:IntegrationTesting",
)


BDA_PLONE_WALLEE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(BDA_PLONE_WALLEE_FIXTURE,),
    name="BdaPloneWalleeLayer:FunctionalTesting",
)


BDA_PLONE_WALLEE_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        BDA_PLONE_WALLEE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="BdaPloneWalleeLayer:AcceptanceTesting",
)
