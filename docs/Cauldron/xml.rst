.. _xml:

KTL XML
=======

KTL XML describes keywords in a deterministic fashion which is used by clients and dispatchers to configure how keywords are typed and seralized. Cauldron supports using KTL XML in either a *strict* or *loose* fashion.

Cauldron bundles a copy of the :mod:`ktlxml` module for python which parses KTL XML files. When a copy of this module can be imported without using the bundled version, it will be used first. The bundled version only provides a fallback for when :mod:`ktlxml` is not otherwise available. Unlike ``ktl`` and ``DFW``, which are heavily ingrained in the KTL framework and make extensive use of ``stdiosvc``, :mod:`ktlxml` stands on its own, and so :mod:`Cauldron` attempts to use it as is.

Loose KTL XML
-------------

By default, Cauldron will use a *loose* support for KTL XML, and will raise warnings (specifically, :exc:`~Cauldron.exc.CauldronXMLWarning` category warnings) when various XML features are violated. In *loose* mode, it is possible to ignore essentially all of the KTL XML protocol, and to use KTL keywords and services without regard for what is defined in XML files. This is useful for code in development, where features may be added rapidly, and where it isn't necessary to ensure strict adherence to the KTL XML rules.

In *loose* mode, where correct KTL XML is available it will be used. This means that it is possible to use XML to define keyword types and values, and those types and values will be correctly applied to dispatchers. Simultaneously, it is possible to ignore XML for some keywords and add keywords which are not defined in XML programatically.

Strict KTL XML
--------------

Although the loose KTL XML mode is powerful, it can be too powerful. The XML keyword definition system provides as strong foundation to ensure that clients and services correctly use keywords. In *strict* mode, :mod:`Cauldron` will enforce all XML rules to the best of its ability, to mimic as close as possible the KTL production environment. To enable strict mode, use the api function :func:`~Cauldron.api.use_strict_xml`::

    >>> from Cauldron.api import use_strict_xml
    >>> use_strict_xml()

You can programmatically determine whether *strict* mode is enabled using the setting variable :attr:`~Cauldron.api.STRICT_KTL_XML`::

    >>> from Cauldron.api import STRICT_KTL_XML
    >>> STRICT_KTL_XML
    <Setting STRICT_KTL_XML=True>

Locating KTL XML
----------------

KTL XML is usually installed in a specific build location on UCO/Lick supported machines. Since this is probably not the case on local development machines, you might need to override the search paths for KTL XML files. The search path can be overridden using the ``LROOT`` or ``RELDIR`` environment variables. They should point to a directory two levels above your desired XML files, and the path to your XML files must be of the form ``data/{servicename}/*.xml``
