.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

.. image:: https://github.com/collective/bda.plone.wallee/actions/workflows/plone-package.yml/badge.svg
    :target: https://github.com/collective/bda.plone.wallee/actions/workflows/plone-package.yml

.. image:: https://coveralls.io/repos/github/collective/bda.plone.wallee/badge.svg?branch=main
    :target: https://coveralls.io/github/collective/bda.plone.wallee?branch=main
    :alt: Coveralls

.. image:: https://codecov.io/gh/collective/bda.plone.wallee/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/collective/bda.plone.wallee

.. image:: https://img.shields.io/pypi/v/bda.plone.wallee.svg
    :target: https://pypi.python.org/pypi/bda.plone.wallee/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/status/bda.plone.wallee.svg
    :target: https://pypi.python.org/pypi/bda.plone.wallee
    :alt: Egg Status

.. image:: https://img.shields.io/pypi/pyversions/bda.plone.wallee.svg?style=plastic   :alt: Supported - Python Versions

.. image:: https://img.shields.io/pypi/l/bda.plone.wallee.svg
    :target: https://pypi.python.org/pypi/bda.plone.wallee/
    :alt: License


================
bda.plone.wallee
================

Wallee payment integration for bda.plone.shop


Features
--------

- Lightbox Payment for https://wallee.com/



Installation
------------

Install bda.plone.wallee by adding it to your buildout::

    [buildout]

    ...

    eggs =
        bda.plone.wallee


and then running ``bin/buildout``

Activate the bda.plone.wallee in Plone controlpanel and add your wallee credentials 
in corresponding tab of the bda.plone.shop settings.

Important: This integration does NOT initiate email sendouts. 
Email sendout is expected to be configured and done from within wallee. 


Contributors
------------

We'd be happy to see many forks and pull-requests to make this program even better.
Professional support is offered by the maintainers and some of the authors.

- Issue Tracker: https://github.com/collective/bda.plone.wallee/issues
- Source Code: https://github.com/collective/bda.plone.wallee


Authors
-------

- Peter Holzer

Contact: `dev@bluedynamics.com <mailto:dev@bluedynamics.com>`_


License
-------

The project is licensed under the GPLv2.
