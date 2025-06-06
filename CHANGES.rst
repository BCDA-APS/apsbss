..
  This file describes user-visible changes between the versions.

  subsections could include these headings (in this order), omit if no content

    Notice
    Breaking Changes
    New Features and/or Enhancements
    Fixes
    Maintenance
    Deprecations
    Contributors

History
#######

The project `milestones <https://github.com/BCDA-APS/apsbss/milestones>`_
describe the future plans.

..
   2.0.2
   *****

2.0.1
*****

* Released 2025-06-06

Maintenance
----------------

* DTN ports changed.
* Pin caproto <1.2.0 (for testing only)

2.0.0
*****

* Released 2024-12-19

Notice
------

* Complete overhaul for APS-U era.

Breaking Changes
----------------

* Proposal ID is now an integer, was previously text.  (ESAF ID is integer,
  as before.)
* Standardize on the name **run** instead of **cycle** as the reference used
  for the name of an APS operations *run* period.

* Includes EPICS PV: ``record(stringout, "$(P)esaf:run")``

New Features
------------

* Add search for ESAFs & Proposals using Whoosh package.
* Add support for direct access to read IS database.
* Add Server class that chooses between DM or IS interface.
* Integer timestamp PVs for ESAF start & end and Proposal start, end, & submitted.
* User can override default DM URL by setting an environment variable.

Maintenance
-----------

* Add requests to project requirements.
* Code style enforced by pre-commit.
* Increased code coverage of unit testing.
* Moved report and table generation to new Server class.
* Refactored (and simplified) IOC report table.
* Relocated functions out of apsbss module.
* Switch documentation to use pydata sphinx theme.
* Update to install and run with Python versions 3.9, 3.10, 3.11.

Deprecations
-------------

* Removed all items marked for deprecation.

-------------

1.5.6
*****

released 2022-03-24

Fixes
~~~~~

* add ``pyyaml`` to package requirements

1.5.5
*****

released 2022-01-12

Fixes
~~~~~

* install with Python 3.7+
* ``main()`` now found for command-line use

1.5.4
******

released 2022-01-05

This package (``apsbss``) was moved out of ``apstools`` release 1.5.4. See the
*apstools* `change history
<https://github.com/BCDA-APS/apstools/blob/main/CHANGES.rst>`_ for any previous
changes to this code base.
