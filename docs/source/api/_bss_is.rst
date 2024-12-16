.. _bss_is:

APS IS Scheduling System
========================

Credentials from the IS group are required for this interface.  This interface
provides more proposal details than the :ref:`APS Data Management interface
<bss_dm>`, such as:

* Proposal type (general user proposal, partner user proposal, ...)
* Additional identifies, where applicable
* Other content from original proposal, such as equipment details

Define the environment variable ``APSBSS_CREDS_FILE=/path/to/creds_file.txt``
where the ``creds_file.txt`` contains the username and password (separated by
white space) authorized for access to these details.  If the file so-described
cannot be used, the DM interface will be used instead.

.. automodule:: apsbss.bss_is
    :members:
