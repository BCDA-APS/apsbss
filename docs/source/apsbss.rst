

.. index:: apsbss

.. _apsbss_application:

======
apsbss
======

Provide information from APS Proposal and ESAF (experiment safety approval
form) databases as PVs at each beam line so that this information
(metadata) may be added to new data files.  The ``aps-dm-api``
(``dm`` for short) package [#]_
is used to access the APS databases as read-only.

*No information is written back to the APS
databases from this software.*

.. [#] ``dm``: https://anaconda.org/apsu/aps-dm-api

.. sidebar:: PVs for experiment metadata

	This information retreived from the APS databases is stored in PVs
	on the beam line subnet.  These PVs are available to *any* EPICS
	client as metadata (SPEC, area detector, Bluesky, GUI screens, logging, other).
	This design allows the local instrument team to override
	any values read from the APS databases, if that is needed.

Given: [#]_

* a beam line name (such as ``9-ID-B,C``)
* APS run name (such as ``2019-2``) to locate a specific proposal ID
* proposal ID number (such as ``66083``)
* ESAF ID number (such as ``226319``)

The typical information obtained includes:

* ESAF & proposal titles
* user names
* user institutional affiliations
* user emails
* applicable dates, reported in ISO8601 time format
* is proposal propietary?
* is experiment mail-in?

These PVs are loaded on demand by the local instrument team at the beam line.
See the :ref:`apsbss_ioc` section for details about
managing the EPICS PVs.

.. [#] Example uses a beamline name and APS run from before APSU.  This beamline
   name is no longer in use.  See :ref:`subcommand.beamlines`.

Overview
========

The ``apsbss`` command-line application provide its features through
subcommands. Running ``apsbss`` without a subcommand will show the usage
response (which lists the available commands): [#]_

.. code-block:: bash

    $ apsbss
    usage: apsbss [-h] [-v] {beamlines,runs,esaf,list,now,proposal,clear,setup,update,report} ...

The ``-v`` option prints the program version.  The ``-h`` option prints the help message:

.. code-block:: bash

    $ apsbss -h
    usage: apsbss [-h] [-v] {beamlines,runs,esaf,list,now,proposal,clear,setup,update,report} ...

    Retrieve specific records from the APS Proposal and ESAF databases.

    options:
      -h, --help            show this help message and exit
      -v, --version         print version number and exit

    subcommand:
      {beamlines,runs,list,proposal,esaf,clear,setup,update,report}
        beamlines           print list of beamlines
        runs                print APS run names
        list                print proposals and ESAFs for beamline and run
        now                 print information of proposals & ESAFs running now
        proposal            print specific proposal for beamline and run
        esaf                print specific ESAF
        search              print proposals and ESAFs for beamline and run matching the query
        clear               EPICS PVs: clear
        setup               EPICS PVs: setup
        update              EPICS PVs: update from BSS
        report              EPICS PVs: report what is in the PVs

.. [#] Here and below, the initial ``$`` in the example is the command prompt
    from the Linux bash shell.  Do not type that.

Subcommands
===========

See :ref:`api` for the source code documentation of each of these subcommands.

.. _subcommand.beamlines:

beamlines
---------

List the names of beamlines defined.

.. code-block:: bash

    usage: apsbss beamlines [-h]

    options:
      -h, --help  show this help message and exit

That list as of 2024-12:

.. code-block:: bash

    $ apsbss beamlines
    1-BM-B,C       10-ID-B        17-ID-B        28-ID-B,C
    1-ID-B,C,E     11-BM-B        18-ID-D        28-ID-D,E
    2-BM-A,B       11-ID-B        19-BM-D        28-ID-F
    2-ID-D         11-ID-C        19-ID-E        28-ID-G
    2-ID-E         11-ID-D        20-BM-B        29-ID-C,D
    3-ID-B,C,D     12-BM-B        20-ID-D,E      30-ID-B,C
    4-ID-B,G,H     12-ID-B        21-ID-D        31-ID-D
    5-BM-B         12-ID-E        21-ID-F        31-ID-E
    5-ID-B,C,D     13-BM-C        21-ID-G        32-ID-B,C
    6-BM-A,B       13-BM-D        22-ID-D        33-BM-C
    6-ID-B,C       13-ID-C,D      22-ID-E        33-ID-C
    6-ID-D         13-ID-E        23-ID-B        34-ID-E
    7-BM-B         14-ID-B        23-ID-D        34-ID-F
    7-ID-B,C,D     15-ID-B,E      24-ID-C        35-BM-C
    8-BM-B         15-ID-C,D      24-ID-E        35-ID-B,C,D,E
    8-ID-E,I       16-BM-B,D      25-ID-C        38-AM-A
    9-BM-B,C       16-ID-B        25-ID-D,E
    9-ID-D         16-ID-D,E      26-ID-C
    10-BM-B        17-BM-B        27-ID-B


Some names include multiple stations.  For example, use ``8-ID-E,I`` for either
station at beamline 8-ID.

.. raw:: html

    <details>
    <summary>Pre-APSU Beamlines</summary>
    <pre>
    Names defined on 2020-07-10:

    $ apsbss beamlines
    1-BM-B,C       8-ID-I         15-ID-B,C,D    23-BM-B
    1-ID-B,C,E     9-BM-B,C       16-BM-B        23-ID-B
    2-BM-A,B       9-ID-B,C       16-BM-D        23-ID-D
    2-ID-D         10-BM-A,B      16-ID-B        24-ID-C
    2-ID-E         10-ID-B        16-ID-D        24-ID-E
    3-ID-B,C,D     11-BM-B        17-BM-B        26-ID-C
    4-ID-C         11-ID-B        17-ID-B        27-ID-B
    4-ID-D         11-ID-C        18-ID-D        29-ID-C,D
    5-BM-C         11-ID-D        19-BM-D        30-ID-B,C
    5-BM-D         12-BM-B        19-ID-D        31-ID-D
    5-ID-B,C,D     12-ID-B        20-BM-B        32-ID-B,C
    6-BM-A,B       12-ID-C,D      20-ID-B,C      33-BM-C
    6-ID-B,C       13-BM-C        21-ID-D        33-ID-D,E
    6-ID-D         13-BM-D        21-ID-E        34-ID-C
    7-BM-B         13-ID-C,D      21-ID-F        34-ID-E
    7-ID-B,C,D     13-ID-E        21-ID-G        35-ID-B,C,D,E
    8-BM-B         14-BM-C        22-BM-D
    8-ID-E         14-ID-B        22-ID-D
    </pre>
    </details>

runs
----

List the names of APS runs defined.

.. code-block:: bash

    usage: apsbss runs [-h] [-f] [-a]

    options:
      -h, --help       show this help message and exit
      -f, --full       full report including dates (default is compact)
      -a, --ascending  full report by ascending names (default is descending)

That list, as of 2024-12:

.. code-block:: bash

    $ apsbss runs
    2008-3    2011-2    2014-1    2016-3    2019-2
    2009-1    2011-3    2014-2    2017-1    2019-3
    2009-2    2012-1    2014-3    2017-2    2020-1
    2009-3    2012-2    2015-1    2017-3    2020-2
    2010-1    2012-3    2015-2    2018-1
    2010-2    2013-1    2015-3    2018-2
    2010-3    2013-2    2016-1    2018-3
    2011-1    2013-3    2016-2    2019-1

Pick the run of interest.  Here, we pick ``2020-2``.

To print the full report (including start and end of each run):

.. code-block:: bash

    $ apsbss runs --full
    ====== =================== ===================
    run    start               end
    ====== =================== ===================
    2020-2 2020-06-09 07:00:00 2020-10-01 07:00:00
    2020-1 2020-01-28 08:00:00 2020-06-09 07:00:00
    2019-3 2019-09-24 07:00:00 2020-01-28 08:00:00
    2019-2 2019-05-21 07:00:00 2019-09-24 07:00:00
    ...    ...                 ...
    2009-1 2009-01-21 08:00:00 2009-05-20 07:00:00
    2008-3 2008-09-24 07:00:00 2009-01-21 08:00:00
    ====== =================== ===================

list
----

List the proposals for a specific beamline and run.

.. code-block:: bash

    $ apsbss list -h
    usage: apsbss list [-h] [-r RUN] beamlineName

    positional arguments:
      beamlineName       Beamline name

    options:
      -h, --help         show this help message and exit
      -r RUN, --run RUN  APS run name. One of the names returned by 'apsbss runs' or one of these ('past', 'prior', 'previous') for the previous run,
                        ('current' or 'now') for the current run, ('future' or 'next') for the next run, or 'recent' for the past two years.

Such as:

.. code-block:: bash

    $ apsbss list -r 2024-3 19-ID-D
    Proposal(s): beam line 19-ID-D, run: 2024-3
    == === ===== === ======= =====
    id run start end user(s) title
    == === ===== === ======= =====
    == === ===== === ======= =====

    ESAF(s): sector 19, run(s) 2024-3
    ====== ======== ====== ========== ========== ==================== ========================================
    id     status   run    start      end        user(s)              title
    ====== ======== ====== ========== ========== ==================== ========================================
    276922 Approved 2024-3 2024-11-22 2024-12-19 Wieghold,Mercado ... 19-ID-A,C,D Technical Commissioning
    276575 Approved 2024-3 2024-10-31 2024-12-19 Wieghold,Lai,Luo,... 19-ID-C,D,E Operations Commissioning
    276558 Approved 2024-3 2024-10-25 2024-12-19 Lai,Guerrero,Luo,... 19-ID-A Temporary Technical Commissio...
    275933 Approved 2024-3 2024-10-24 2024-12-19 Wieghold,Luo,Mase... 19-ID-A Operations Commissioning
    ====== ======== ====== ========== ========== ==================== ========================================

Note: No proposals for this beamline in run 2024-3.  New beamline commissioning
started during this run.

now
---

List the proposals and ESAFS active now.

.. code-block:: bash

    $ apsbss now -h
    usage: apsbss now [-h] beamlineName

    positional arguments:
      beamlineName  Beamline name

    options:
      -h, --help    show this help message and exit

Such as:

.. code-block:: bash

    $ apsbss now 19-ID-D
    Proposal(s): beam line 19-ID-D, 2024-12-17 12:08:19.891573-06:00
    == === ===== === ======= =====
    id run start end user(s) title
    == === ===== === ======= =====
    == === ===== === ======= =====

    ESAF(s): sector 19, 2024-12-17 12:08:19.891573-06:00
    ====== ======== ====== ========== ========== ==================== ========================================
    id     status   run    start      end        user(s)              title
    ====== ======== ====== ========== ========== ==================== ========================================
    276922 Approved 2024-3 2024-11-22 2024-12-19 Wieghold,Mercado ... 19-ID-A,C,D Technical Commissioning
    276575 Approved 2024-3 2024-10-31 2024-12-19 Wieghold,Lai,Luo,... 19-ID-C,D,E Operations Commissioning
    276558 Approved 2024-3 2024-10-25 2024-12-19 Lai,Guerrero,Luo,... 19-ID-A Temporary Technical Commissio...
    275933 Approved 2024-3 2024-10-24 2024-12-19 Wieghold,Luo,Mase... 19-ID-A Operations Commissioning
    ====== ======== ====== ========== ========== ==================== ========================================

To get details on a specific proposal or ESAF, see the subcommand for each.

proposal
--------

List the proposal details for a specific beamline and run.

.. code-block:: bash

    $ apsbss proposal -h
    usage: apsbss proposal [-h] proposalId run beamlineName

    positional arguments:
      proposalId    proposal ID number
      run           APS run name
      beamlineName  Beamline name

    options:
      -h, --help    show this help message and exit

Note the run name here is required (not an option).  Such as:

.. code-block:: bash

    $ apsbss proposal 78674 2022-2 12-ID-B
    activities:
    - duration: 108000
      endTime: '2022-07-20 14:00:00-05:00'
      startTime: '2022-07-19 08:00:00-05:00'
    duration: 108000
    endTime: '2022-07-20 14:00:00-05:00'
    experimenters:
    - badge: '87100'
      email: ychoi@anl.gov
      firstName: Yongseong
      id: 516580
      instId: 3927
      institution: Argonne National Laboratory
      lastName: Choi
    id: 78674
    mailInFlag: N
    proprietaryFlag: N
    startTime: '2022-07-19 08:00:00-05:00'
    submittedDate: '2022-03-01 10:16:27-06:00'
    title: National School on Neutron and X-ray Scattering, experimental tutorials, 12-ID-B
    totalShiftsRequested: 12

esaf
----

.. code-block:: bash

    $ apsbss esaf 258638
    description: In the practical sessions for X-ray summer school student, we will demonstrate
      and practice on surface X-ray diffraction and coherent Bragg rod measurements and
      data processing. We will only ex-situ measure a few representative oxide or 2D materials
      thin films for the practical session. No other chemicals are included. No need to
      use the chemical room at 433 E030.
    esafId: 258638
    esafStatus: Approved
    esafTitle: National School on Neutron and X-ray Scattering, experimental tutorials,
      12-ID-D
    experimentEndDate: '2022-07-22 16:00:00'
    experimentStartDate: '2022-07-21 08:00:00'
    experimentUsers:
    - badge: '87100'
      badgeNumber: '87100'
      email: ychoi@anl.gov
      firstName: Yongseong
      lastName: Choi
      piFlag: 'Yes'
    - badge: '1234567890'
      badgeNumber: '1234567890'
      email: r.e.searcher@example.org
      firstName: R.E.
      lastName: Searcher
      piFlag: 'No'
    - other experimentUsers omitted here
    sector: '12'

.. _subcommand.search:

search
------

Search for ESAFs and Proposals.  See
:meth:`~apsbss.server_interface.Server.search` for more hints about how to
search.

.. code-block:: bash

    usage: apsbss search [-h] [-r RUN] beamlineName query

    positional arguments:
      beamlineName       Beamline name
      query              query

    options:
      -h, --help         show this help message and exit
      -r RUN, --run RUN  APS run name. One of the names returned by 'apsbss runs' or one of these ('past', 'prior', 'previous') for the previous run,
                        ('current' or 'now') for the current run, ('future' or 'next') for the next run, or 'recent' for the past two years.

Example (2024-12-18):

.. code-block:: bash

    $ apsbss search 12-ID-B "title:School AND pi:Choi"
    Search: beamline='12-ID-B' runs='recent' query='title:School AND pi:Choi'
    ====== ============================== ====== ======================================== ========
    id     pi                             run    title                                    type
    ====== ============================== ====== ======================================== ========
    78674  Yongseong Choi <ychoi@anl.gov> 2022-2 National School on Neutron and X-ray ... proposal
    258606 Yongseong Choi <ychoi@anl.gov> 2022-2 National School on Neutron and X-ray ... ESAF
    258638 Yongseong Choi <ychoi@anl.gov> 2022-2 National School on Neutron and X-ray ... ESAF
    ====== ============================== ====== ======================================== ========


EPICS-related subcommands
-------------------------

These commands are for use of a local EPICS database to cache details locally at
the beamline.

clear
++++++++++++

To clear the information from the EPICS PVs, use this command:

.. code-block:: bash

    $ apsbss clear 9id:bss:
    clear EPICS 9id:bss:
    connected in 0.104s
    cleared in 0.011s

setup
++++++++++++

To configure ``9id:bss:`` PVs for beam line ``9-ID-B,C`` and run ``2020-2``, use
this command:

.. code-block:: bash

    $ apsbss setup 9id:bss: 9-ID-B,C 2020-2
    connected in 0.143s
    setup EPICS 9id:bss: 9-ID-B,C run=2020-2 sector=9

Or you could enter them into the appropriate boxes on the GUI.

update
++++++++++++

To update the EPICS PVs with Proposal and Information from the APS database,
first enter the proposal and ESAF ID numbers into the GUI (or set
``9id:bss:proposal:id`` and ``9id:bss:esaf:id``, respectively). Note that for
this ESAF ID, we had to change the run to `2019-2`.

Then, use this command to retrieve the information and update the PVs:

.. code-block:: bash

    $ apsbss update 9id:bss:
    update EPICS 9id:bss:
    connected in 0.105s

If there is a problem with the update process, it should be
reported in the `status` PV (such as `9id:bss:status`).

.. figure:: ./_static//ui_error_status.png
   :width: 95%

   Image of ``apsbss.ui`` screen GUI in caQtDM showing
   `update` command error due to missing beam line name.

report
++++++++++++

To view all the information in the EPICS PVs, use this command:

.. code-block:: bash

    $ apsbss report 9id:bss:
    clear EPICS 9id:bss:

Since this content is rather large, it is available
for download: :download:`apsbss report <./_static//apsbss_report.txt>`

Demonstration
=============

We'll demonstrate ``apsbss`` with information for APS beam
line 9-ID, using PV prefix ``9id:bss:``.

#. Create the PVs in an EPICS IOC (see section :ref:`apsbss_ioc`)
#. Initialize PVs with beam line name and APS run number
#. Set PVs with the Proposal and ESAF ID numbers
#. Retrieve (& update PVs) information from APS databases

**Enter beam line and APS run info**

.. figure:: ./_static//ui_initialized.png
   :width: 95%

   Image of ``apsbss.ui`` screen GUI in caQtDM showing PV prefix
   (``9id:bss:``), APS run ``2019-2`` and beam line ``9-ID-B,C``.

   * beam line name PV: ``9id:bss:proposal:beamline``
   * APS run PV: ``9id:bss:esaf:run``


**Enter Proposal and ESAF ID numbers**

Note we had to use the APS run of `2019-2`
to match what is in the proposal's information.

.. figure:: ./_static//ui_id_entered.png
   :width: 95%

   Image of ``apsbss.ui`` screen GUI in caQtDM with Proposal
   and ESAF ID numbers added.

   * proposal ID number PV: ``9id:bss:proposal:id``
   * ESAF ID number PV: ``9id:bss:esaf:id``

**Update PVs from APS databases**

In the GUI, press the button labeled ``get Proposal and ESAF info``.
This button executes the command line: ``apsbss update 9id:bss:``

Here's a view of the GUI after running the update.  The
information shown in the GUI is only part of the PVs,
presented in a compact format. A full report of the
information received, including PV names, is available for
:download:`download <./_static//apsbss_report.txt>`.

.. figure:: ./_static//ui_updated.png
   :width: 95%

   Image of ``apsbss.ui`` screen GUI in caQtDM showing Proposal
   and ESAF information.

To clear the PVs, in the GUI, press the button labeled ``clear PVs``.
This button executes the command line: ``apsbss clear 9id:bss:``


Initialize PVs for beam line and APC run
----------------------------------------

After creating the PVs in an IOC, the next step is to
initialize them with the beam line name and the APS
run name.  Both of these must match exactly
with values known in the data management (``dm``) system.

For any of these commands, you must know the EPICS
PV prefix to be used.  The examples above are for
beam line 9-ID.  The PV prefix in these examples
is ``9id:bss:``.

.. _beamlines:

Run ``apsbss beamlines`` to pick a beamline name:

.. code-block:: bash

    $ apsbss beamlines
    1-BM-B,C       10-ID-B        17-ID-B        28-ID-B,C
    1-ID-B,C,E     11-BM-B        18-ID-D        28-ID-D,E
    2-BM-A,B       11-ID-B        19-BM-D        28-ID-F
    2-ID-D         11-ID-C        19-ID-E        28-ID-G
    2-ID-E         11-ID-D        20-BM-B        29-ID-C,D
    3-ID-B,C,D     12-BM-B        20-ID-D,E      30-ID-B,C
    4-ID-B,G,H     12-ID-B        21-ID-D        31-ID-D
    5-BM-B         12-ID-E        21-ID-F        31-ID-E
    5-ID-B,C,D     13-BM-C        21-ID-G        32-ID-B,C
    6-BM-A,B       13-BM-D        22-ID-D        33-BM-C
    6-ID-B,C       13-ID-C,D      22-ID-E        33-ID-C
    6-ID-D         13-ID-E        23-ID-B        34-ID-E
    7-BM-B         14-ID-B        23-ID-D        34-ID-F
    7-ID-B,C,D     15-ID-B,E      24-ID-C        35-BM-C
    8-BM-B         15-ID-C,D      24-ID-E        35-ID-B,C,D,E
    8-ID-E,I       16-BM-B,D      25-ID-C        38-AM-A
    9-BM-B,C       16-ID-B        25-ID-D,E
    9-ID-D         16-ID-D,E      26-ID-C
    10-BM-B        17-BM-B        27-ID-B

Run ``apsbss runs`` to pick an APS run name:

.. code-block:: bash

    $ apsbss runs
    2008-3    2012-1    2015-2    2018-3    2022-1
    2009-1    2012-2    2015-3    2019-1    2022-2
    2009-2    2012-3    2016-1    2019-2    2022-3
    2009-3    2013-1    2016-2    2019-3    2023-1
    2010-1    2013-2    2016-3    2020-1    2024-2
    2010-2    2013-3    2017-1    2020-2    2024-3
    2010-3    2014-1    2017-2    2020-3    2025-1
    2011-1    2014-2    2017-3    2021-1    2025-2
    2011-2    2014-3    2018-1    2021-2
    2011-3    2015-1    2018-2    2021-3

For this example, we pick ``2020-2`` and beamline ``9-ID-B,C``.
(Note: this beamline name is no longer in use.)

Write the beam line name and run to the EPICS PVs. To configure ``9id:bss:`` PVs
for beam line ``9-ID-B,C`` and run ``2020-2``, use this command:

.. code-block:: bash

    $ apsbss setup 9id:bss: 9-ID-B,C 2020-2
    connected in 0.143s
    setup EPICS 9id:bss: 9-ID-B,C run=2020-2 sector=9

Or you could enter them into the appropriate boxes on the GUI.


What Proposal and ESAF ID numbers to use?
+++++++++++++++++++++++++++++++++++++++++

Proposals are usually valid for two years.  To learn what
proposals are valid for your beam line, use this command
with your own beam line's name.  The report will provide
two tables, one for Proposals and the other for ESAFs,
both with entries in the current APS run::

    $ apsbss list 9-ID-B,C
    Proposal(s):  beam line 9-ID-B,C,  run(s) now

    ===== ====== =================== =================== ==================== ========================================
    id    run    start               end                 user(s)              title
    ===== ====== =================== =================== ==================== ========================================
    70118 2020-3 2020-12-05 08:00:00 2020-12-05 16:00:00 Beaucage,Gogia,Ku... In situ structural modification and d...
    63765 2020-3 2020-11-19 08:00:00 2020-11-23 08:00:00 Swantek,Powell,Ka... USAXS Measurements of Fuel Injection ...
    71000 2020-3 2020-11-15 08:00:00 2020-11-16 08:00:00 Shapiro,Sattar,O'... Quantification of subcellular iron lo...
    65742 2020-3 2020-11-11 08:00:00 2020-11-15 08:00:00 Miller,Victor,Smith  Using Lanthanide Binding Tags to Moni...
    70080 2020-3 2020-11-06 08:00:00 2020-11-09 08:00:00 Shapiro,Sattar,O'... Quantification of subcellular iron lo...
    45287 2020-3 2020-11-03 08:00:00 2020-11-06 08:00:00 Hong,O'Halloran,C... Quantitative Mapping of subcellular t...
    68468 2020-3 2020-10-29 07:00:00 2020-11-02 07:00:00 Devabathini,Bury,... Sub Micron-XRF imaging of SVZ, Hippoc...
    71437 2020-3 2020-10-20 07:00:00 2020-10-26 07:00:00 Paunesku             Tissue microarrays for Bionanoprobe use
    72088 2020-3 2020-10-09 07:00:00 2020-10-19 07:00:00 Chen,Deng,Maxey       setup and test vacuum flight tube at...
    71891 2020-3 2020-10-05 07:00:00 2020-10-09 07:00:00 Ralle,Chen           Copper Distribution in Cyrptococcus N...
    ===== ====== =================== =================== ==================== ========================================

    ESAF(s):  sector 9,  run(s) now

    ====== ======== ========== ========== ==================== ========================================
    id     status   start      end        user(s)              title
    ====== ======== ========== ========== ==================== ========================================
    233214 Pending  2020-12-05 2020-12-05 Rishi,Camara,Okol... In situ structural modification and d...
    233897 Pending  2020-12-03 2020-12-07 Li,Arai              Effect of (bi)carbonate on the transf...
    232646 Approved 2020-11-19 2020-11-25 Sforzo,Tekawade,P... USAXS Measurements of Prototype Stand...
    233888 Pending  2020-11-17 2020-11-20 Balasubramanian,D... Studies of calcium local structure in...
    234023 Approved 2020-11-16 2020-12-17 Ilavsky,Krzysko,K... USAXS comissioning and mail-in experi...
    234093 Approved 2020-11-15 2020-11-16 Chen                 Quantitative Mapping of subcellular t...
    233213 Approved 2020-11-12 2020-11-13 Bryson,Wu,Sterbinsky XANES and EXAFS analysis of novel Ni-...
    233148 Approved 2020-11-11 2020-11-12 Miller,LiBretto,Wu   Miller-Purdue_CuChitosan_Oct2020
    233644 Approved 2020-11-11 2020-11-16 Victor,Ambi,Mille... Using Lanthanide Binding Tags to Moni...
    232832 Approved 2020-11-07 2020-11-09 Dong,Wang,Wu         Exploring bi-atom catalysts for therm...
    233566 Approved 2020-11-06 2020-11-09 Sattar,Shapiro       Quantification of subcellular iron lo...
    230906 Approved 2020-11-03 2020-11-07 Finfrock,Grosvenor   A Partner User Proposal to Continue t...
    233318 Approved 2020-11-03 2020-11-09 Chen                 Quantitative Mapping of subcellular t...
    233058 Approved 2020-10-31 2020-11-02 Wu                   TW 2020-3: Battery and/or Catalysis E...
    233217 Approved 2020-10-27 2020-10-31 Devabathini,Chen,... Sub Micron-XRF imaging of SVZ, Hippoc...
    232672 Approved 2020-10-27 2020-10-31 Sham,Motta Meira,... XAFS of semiconducting and metallic n...
    232345 Approved 2020-10-20 2020-10-26 Smith,Islam          Tracking aquatic redox conditions and...
    232905 Approved 2020-10-20 2020-10-23 Chen                 Tissue microarrays for Bionanoprobe use
    232020 Approved 2020-10-13 2020-10-19 Siebecker,Schmidt... Potassium speciation in cotton-produc...
    232231 Approved 2020-10-06 2020-10-12 Hettiarachchi,Gal... Use of Different Organic Polymers in ...
    232126 Approved 2020-10-05 2020-11-15 Chen,Deng,Maxey      setup and test vacuum flight tube at ...
    232154 Approved 2020-10-05 2020-10-09 Chen,Ralle           Copper Distribution in Cyrptococcus N...
    230928 Approved 2020-10-01 2020-12-18 Chen,Deng,Luo,Yao... Bionanoprobe commissioning
    230845 Approved 2020-10-01 2020-12-17 Sterbinsky,Heald,... 9BM Beamline Commissioning 2020-3
    231809 Approved 2020-10-01 2020-12-17 Ilavsky,Maxey,Kuz... Commission 9ID, USAXS
    231811 Approved 2020-10-01 2020-12-31 Ilavsky,chen,Maxe... Commission 9ID and USAXS
    ====== ======== ========== ========== ==================== ========================================


View Proposal Information
+++++++++++++++++++++++++

To view information about a specific proposal, you
must be able to provide the proposal's ID number and
the APS run name.

::

    $ apsbss proposal 64629 2019-2 9-ID-B,C
    duration: 36000
    endTime: '2019-06-25 17:00:00'
    experimenters:
    - badge: '86312'
      email: ilavsky@aps.anl.gov
      firstName: Jan
      id: 424292
      instId: 3927
      institution: Argonne National Laboratory
      lastName: Ilavsky
    - badge: '85283'
      email: okasinski@aps.anl.gov
      firstName: John
      id: 424308
      instId: 3927
      institution: Argonne National Laboratory
      lastName: Okasinski
      piFlag: Y
    id: 64629
    mailInFlag: N
    proprietaryFlag: N
    startTime: '2019-06-25 07:00:00'
    submittedDate: '2019-03-01 18:35:02'
    title: 2019 National School on Neutron & X-ray Scattering Beamline Practicals - CMS
    totalShiftsRequested: 12

The report is formatted in *YAML* (https://yaml.org)
which is easy to read and easily converted into a Python
data structure using ``yaml.load(report_text)``.
See section :ref:`reading_yaml`.


Get ESAF Information
++++++++++++++++++++

To view information about a specific ESAF, you
must be able to provide the ESAF ID number.

::

    $ apsbss esaf 226319
    description: We will commission beamline and  USAXS instrument. We will perform experiments
      with safe beamline standards and test samples (all located at beamline and used
      for this purpose routinely) to evaluate performance of beamline and instrument.
      We will perform hardware and software development as needed.
    esafId: 226319
    esafStatus: Approved
    esafTitle: Commission 9ID and USAXS
    experimentEndDate: '2020-09-28 08:00:00'
    experimentStartDate: '2020-05-26 08:00:00'
    experimentUsers:
    - badge: '86312'
      badgeNumber: '86312'
      email: ilavsky@aps.anl.gov
      firstName: Jan
      lastName: Ilavsky
    - badge: '53748'
      badgeNumber: '53748'
      email: emaxey@aps.anl.gov
      firstName: Evan
      lastName: Maxey
    - badge: '64065'
      badgeNumber: '64065'
      email: kuzmenko@aps.anl.gov
      firstName: Ivan
      lastName: Kuzmenko
    sector: 09

The report is formatted in *YAML* (https://yaml.org)
which is easy to read and easily converted into a Python
data structure using ``yaml.load(report_text)``.
See section :ref:`reading_yaml`.


Update EPICS PVs with Proposal and ESAF
+++++++++++++++++++++++++++++++++++++++

Reference
=========

.. TODO: Move to some other place.  Standalone files?

.. _apsbss_epics_gui_screens:

Displays for MEDM & caQtDM
---------------------------

Display screen files are provided for viewing some of the EPICS PVs
using either MEDM (``apsbss.adl``) or caQtDM (``apsbss.ui``).

* caQtDM screen: :download:`apsbss.ui <../../apsbss/apsbss.ui>`
* MEDM screen: :download:`apsbss.adl <../../apsbss/apsbss.adl>`

Start caQtDM with this command: ``caQtDM -macro "P=9id:bss:" apsbss.ui &``

Start MEDM with this command: ``medm -x -macro "P=9id:bss:" apsbss.ui &``

Here's an example starter script for caQtDM from APS 9-ID-C (USAXS):

.. code-block:: bash

    #!/bin/bash

    BLUESKY_ROOT=/APSshare/anaconda3/Bluesky
    APSBSS_PKG=${BLUESKY_ROOT}/lib/python3.7/site-packages/apsbss
    GUI_SCREEN=${APSBSS_PKG}/apsbss.ui
    CAQTDM=/APSshare/bin/caQtDM

    source ${BLUESKY_ROOT}/bin/activate
    ${CAQTDM} -macro P=9idc:bss: ${GUI_SCREEN} &


IOC Management
---------------------------

The EPICS PVs are provided by running an instance of ``apsbss.db``
either in an existing EPICS IOC or using the ``softIoc`` application
from EPICS base.  A shell script (``apsbss_ioc.sh``) is included
for loading Proposal and ESAF information from the
APS databases into the IOC.

* :download:`apsbss.db <../../apsbss/apsbss.db>`

See the section titled ":ref:`apsbss_ioc`"
for the management of the EPICS IOC.

.. _reading_yaml:

Reading YAML in Python
---------------------------

It's easy to read a YAML string and convert it into a
Python structure.  Take the example ESAF information shown
above.  It is available in EPICS PV ``9id:bss:esaf:raw`` which
is a waveform record containing up to 8kB of text.  This IPython
session uses PyEpics and YAML to show how to read the text
from EPICS and convert it back into a Python structure.

.. code-block:: python

    In [1]: import epics, yaml

    In [2]: msg = epics.caget("9id:bss:esaf:raw", as_string=True)

    In [3]: msg
    Out[3]: "description: We will commission beamline and  USAXS instrument. We will perform experiments\n  with safe beamline standards and test samples (all located at beamline and used\n  for this purpose routinely) to evaluate performance of beamline and instrument.\n  We will perform hardware and software development as needed.\nesafId: 226319\nesafStatus: Approved\nesafTitle: Commission 9ID and USAXS\nexperimentEndDate: '2020-09-28 08:00:00'\nexperimentStartDate: '2020-05-26 08:00:00'\nexperimentUsers:\n- badge: '86312'\n  badgeNumber: '86312'\n  email: ilavsky@aps.anl.gov\n  firstName: Jan\n  lastName: Ilavsky\n- badge: '53748'\n  badgeNumber: '53748'\n  email: emaxey@aps.anl.gov\n  firstName: Evan\n  lastName: Maxey\n- badge: '64065'\n  badgeNumber: '64065'\n  email: kuzmenko@aps.anl.gov\n  firstName: Ivan\n  lastName: Kuzmenko\nsector: 09"

    In [4]: ymsg = yaml.load(msg)
    /home/beams/JEMIAN/.conda/envs/bluesky_2020_5/bin/ipython:1: YAMLLoadWarning: calling yaml.load() without Loader=... is deprecated, as the default Loader is unsafe. Please read https://msg.pyyaml.org/load for full details.
      #!/home/beams/JEMIAN/.conda/envs/bluesky_2020_5/bin/python

    In [5]: ymsg
    Out[5]:
    {'description': 'We will commission beamline and  USAXS instrument. We will perform experiments with safe beamline standards and test samples (all located at beamline and used for this purpose routinely) to evaluate performance of beamline and instrument. We will perform hardware and software development as needed.',
    'esafId': 226319,
    'esafStatus': 'Approved',
    'esafTitle': 'Commission 9ID and USAXS',
    'experimentEndDate': '2020-09-28 08:00:00',
    'experimentStartDate': '2020-05-26 08:00:00',
    'experimentUsers': [{'badge': '86312',
      'badgeNumber': '86312',
      'email': 'ilavsky@aps.anl.gov',
      'firstName': 'Jan',
      'lastName': 'Ilavsky'},
      {'badge': '53748',
      'badgeNumber': '53748',
      'email': 'emaxey@aps.anl.gov',
      'firstName': 'Evan',
      'lastName': 'Maxey'},
      {'badge': '64065',
      'badgeNumber': '64065',
      'email': 'kuzmenko@aps.anl.gov',
      'firstName': 'Ivan',
      'lastName': 'Kuzmenko'}],
    'sector': '09'}

    In [6]:


Downloads
---------

* EPICS database: :download:`apsbss.db <../../apsbss/apsbss.db>`
* EPICS IOC shell script :download:`apsbss_ioc.sh <../../apsbss/apsbss_ioc.sh>`
* MEDM screen: :download:`apsbss.adl <../../apsbss/apsbss.adl>`
* caQtDM screen: :download:`apsbss.ui <../../apsbss/apsbss.ui>`

Source code documentation
---------------------------

See :ref:`api` for the source code documentation.
