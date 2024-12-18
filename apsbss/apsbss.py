#!/usr/bin/env python

"""
Retrieve specific records from the APS Proposal and ESAF databases.

This code provides the command-line application: ``apsbss``

.. note:: BSS: APS Beamline Scheduling System

EXAMPLES::

    apsbss now 19-ID-D
    apsbss esaf 276575
    apsbss proposal 1010753 2024-3 12-ID-B

.. rubric:: Application
.. autosummary::

    ~cmd_esaf
    ~cmd_list
    ~cmd_now
    ~cmd_proposal
    ~cmd_runs
    ~cmd_search
    ~get_options
    ~main


.. rubric:: EPICS Support
.. autosummary::

    ~connect_epics
    ~epicsClear
    ~epicsReport
    ~epicsSetup
    ~epicsUpdate
"""

import datetime
import logging
import os
import sys
import time

import pyRestTable
import yaml

from .core import iso2dt
from .core import printColumns
from .core import table_list
from .server_interface import Server

CONNECT_TIMEOUT = 3
logger = logging.getLogger(__name__)
parser = None
server = Server(creds_file=os.environ.get("APSBSS_CREDS_FILE"))


class EpicsNotConnected(Exception):
    """No connection to EPICS PV."""


def connect_epics(prefix, n=5):
    """
    Connect with the EPICS database instance.

    PARAMETERS

    prefix : str
        EPICS PV prefix
    n : int
        Number of connection events to attempt before raising EpicsNotConnected.
    """
    from .apsbss_ophyd import EpicsBssDevice

    t0 = time.time()
    while n > 0:
        bss = EpicsBssDevice(prefix, name="bss")
        try:
            bss.wait_for_connection(timeout=CONNECT_TIMEOUT)
            break
        except TimeoutError as reason:
            n -= 1
            if n == 0 and not bss.connected:
                msg = f"Did not connect with EPICS {prefix} in {CONNECT_TIMEOUT}s"
                raise EpicsNotConnected(msg) from reason
    t_connect = time.time() - t0
    logger.debug("connected in %.03fs", t_connect)
    return bss


def epicsClear(prefix):
    """
    Clear the EPICS database.
    Connect with the EPICS database instance.

    PARAMETERS

    prefix
        *str* :
        EPICS PV prefix
    """
    logger.debug("clear EPICS %s", prefix)
    bss = connect_epics(prefix)

    bss.status_msg.put("clear PVs ...")
    t0 = time.time()
    bss.clear()
    t_clear = time.time() - t0
    logger.debug("cleared in %.03fs", t_clear)
    bss.status_msg.put("Done")


def epicsReport(args):
    """
    Subcommand ``report``: EPICS PVs: report the PV values.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    bss = connect_epics(args.prefix)
    print(bss._table(length=30))


def epicsSetup(prefix, beamline, run=None):
    """
    Define the beamline name and APS run in the EPICS database.
    Connect with the EPICS database instance.

    PARAMETERS

    prefix
        *str* :
        EPICS PV prefix
    beamline
        *str* :
        Name of beam line (as defined by the BSS)
    run
        *str* :
        Name of APS run (as defined by the BSS).
        optional: default is current APS run name.
    """
    bss = connect_epics(prefix)

    run = run or server.current_run
    sector = int(beamline.split("-")[0])
    logger.debug(
        "setup EPICS %s %s run=%s sector=%s",
        prefix,
        beamline,
        run,
        sector,
    )

    bss.status_msg.wait_for_connection()
    bss.status_msg.put("clear PVs ...")

    bss.wait_for_connection()
    bss.clear()

    bss.status_msg.put("write PVs ...")
    bss.esaf.aps_run.put(run)
    bss.proposal.beamline_name.put(beamline)
    bss.esaf.sector.put(str(sector))
    bss.status_msg.put("Done")

    return bss


def epicsUpdate(prefix):
    """
    Update EPICS database instance with current ESAF & proposal info.
    Connect with the EPICS database instance.

    PARAMETERS

    prefix
        *str* :
        EPICS PV prefix
    """
    logger.debug("update EPICS %s", prefix)
    bss = connect_epics(prefix)

    bss.status_msg.put("clearing PVs ...")
    bss.clear()

    run = bss.esaf.aps_run.get()

    beamline = bss.proposal.beamline_name.get()
    # sector = bss.esaf.sector.get()
    esaf_id = bss.esaf.esaf_id.get().strip()
    proposal_id = int(bss.proposal.proposal_id.get().strip())

    if len(beamline) == 0:
        bss.status_msg.put(f"undefined: {bss.proposal.beamline_name.pvname}")
        raise ValueError("must set beamline name in " f"{bss.proposal.beamline_name.pvname}")
    elif beamline not in server.beamlines:
        bss.status_msg.put(f"unrecognized: {beamline}")
        raise ValueError(f"{beamline} is not recognized")
    if len(run) == 0:
        bss.status_msg.put(f"undefined: {bss.esaf.aps_run.pvname}")
        raise ValueError(f"must set APS run name in {bss.esaf.aps_run.pvname}")
    elif run not in server.runs:
        bss.status_msg.put(f"unrecognized: {run}")
        raise ValueError(f"{run} is not recognized")

    if len(esaf_id) > 0:
        bss.status_msg.put(f"get ESAF {esaf_id} from APS ...")
        esaf = server.esaf(esaf_id)

        bss.status_msg.put("set ESAF PVs ...")
        bss.esaf.description.put(esaf["description"])
        dt = iso2dt(esaf["experimentEndDate"])
        bss.esaf.end_date.put(str(dt))
        bss.esaf.end_date_timestamp.put(round(dt.timestamp()))
        bss.esaf.esaf_status.put(esaf["esafStatus"])
        bss.esaf.raw.put(yaml.dump(esaf))
        dt = iso2dt(esaf["experimentStartDate"])
        bss.esaf.start_date.put(str(dt))
        bss.esaf.start_date_timestamp.put(round(dt.timestamp()))
        bss.esaf.title.put(esaf["esafTitle"])

        bss.esaf.user_last_names.put(",".join([user["lastName"] for user in esaf["experimentUsers"]]))
        bss.esaf.user_badges.put(",".join([user["badge"] for user in esaf["experimentUsers"]]))
        bss.esaf.number_users_in_pvs.put(0)
        for i, user in enumerate(esaf["experimentUsers"]):
            obj = getattr(bss.esaf, f"user{i+1}")
            obj.badge_number.put(user["badge"])
            obj.email.put(user["email"])
            obj.first_name.put(user["firstName"])
            obj.last_name.put(user["lastName"])
            bss.esaf.number_users_in_pvs.put(i + 1)
            if i == 8:
                break
        bss.esaf.number_users_total.put(len(esaf["experimentUsers"]))

    if proposal_id not in ("", None):
        bss.status_msg.put(f"get Proposal {proposal_id} from APS ...")
        proposal = server.proposal(proposal_id, beamline, run)

        bss.status_msg.put("set Proposal PVs ...")
        bss.proposal.end_date.put(str(proposal.endDate))
        bss.proposal.end_date_timestamp.put(round(proposal.endDate.timestamp()))
        bss.proposal.mail_in_flag.put(proposal.mail_in)
        bss.proposal.proprietary_flag.put(proposal.proprietary)
        bss.proposal.raw.put(yaml.dump(proposal))
        bss.proposal.start_date.put(str(proposal.startDate))
        bss.proposal.start_date_timestamp.put(round(proposal.startDate.timestamp()))
        bss.proposal.submitted_date.put(str(proposal.submittedDate))
        bss.proposal.submitted_date_timestamp.put(round(proposal.submittedDate.timestamp()))
        bss.proposal.title.put(proposal.title)

        bss.proposal.user_last_names.put(",".join(proposal.lastNames))
        bss.proposal.user_badges.put(",".join(proposal.badges))
        bss.proposal.number_users_in_pvs.put(0)
        for i, user in enumerate(proposal._users):
            obj = getattr(bss.proposal, f"user{i+1}")
            obj.badge_number.put(user.badge)
            obj.email.put(user.email)
            obj.first_name.put(user.firstName)
            obj.last_name.put(user.lastName)
            obj.institution.put(user.institution)
            obj.institution_id.put(user.institution_id)
            obj.user_id.put(user.user_id)
            obj.pi_flag.put(user.is_pi)
            bss.proposal.number_users_in_pvs.put(i + 1)
            if i == 8:
                break
        bss.proposal.number_users_total.put(len(proposal.users))

    bss.status_msg.put("Done")


def get_options():
    """Handle command line arguments."""
    global parser
    import argparse

    from .__init__ import __version__

    parser = argparse.ArgumentParser(
        prog=os.path.split(sys.argv[0])[-1],
        description=__doc__.strip().splitlines()[0],
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="print version number and exit",
        version=__version__,
    )

    subcommand = parser.add_subparsers(dest="subcommand", title="subcommand")

    subcommand.add_parser("beamlines", help="print list of beamlines")

    p_sub = subcommand.add_parser("runs", help="print APS run names")
    p_sub.add_argument(
        "-f",
        "--full",
        action="store_true",
        default=False,
        help="full report including dates (default is compact)",
    )
    p_sub.add_argument(
        "-a",
        "--ascending",
        action="store_false",
        default=True,
        help="full report by ascending names (default is descending)",
    )

    p_sub = subcommand.add_parser(
        "list",
        help="print proposals and ESAFs for beamline and run",
    )
    msg = (
        "APS run name."
        "  One of the names returned by 'apsbss runs'"
        " or one of these ('past',  'prior', 'previous')"
        " for the previous run, ('current' or 'now')"
        " for the current run, ('future' or 'next')"
        " for the next run, or 'recent' for the past two years."
    )
    p_sub.add_argument(
        "-r",
        "--run",
        type=str,
        default="now",
        help=msg,
    )
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

    p_sub = subcommand.add_parser(
        "now",
        help="print information of proposals & ESAFs running now",
    )
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

    p_sub = subcommand.add_parser(
        "proposal",
        help="print specific proposal for beamline and run",
    )
    p_sub.add_argument("proposalId", type=int, help="proposal ID number")
    p_sub.add_argument("run", type=str, help="APS run name")
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

    p_sub = subcommand.add_parser("esaf", help="print specific ESAF")
    p_sub.add_argument("esafId", type=int, help="ESAF ID number")

    p_sub = subcommand.add_parser(
        "search",
        help="print proposals and ESAFs for beamline and run matching the query",
    )
    msg = (
        "APS run name."
        "  One of the names returned by 'apsbss runs'"
        " or one of these ('past',  'prior', 'previous')"
        " for the previous run, ('current' or 'now')"
        " for the current run, ('future' or 'next')"
        " for the next run, or 'recent' for the past two years."
    )
    p_sub.add_argument(
        "-r",
        "--run",
        type=str,
        default="recent",
        help=msg,
    )
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")
    p_sub.add_argument("query", type=str, help="query")

    p_sub = subcommand.add_parser("clear", help="EPICS PVs: clear")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")

    p_sub = subcommand.add_parser("setup", help="EPICS PVs: setup")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")
    p_sub.add_argument("run", type=str, help="APS run name")

    p_sub = subcommand.add_parser("update", help="EPICS PVs: update from BSS")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")

    p_sub = subcommand.add_parser("report", help="EPICS PVs: report what is in the PVs")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")

    return parser.parse_args()


def cmd_esaf(args):
    """
    Subcommand ``esaf``: print list of beamlines.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    try:
        esaf = server.esaf(args.esafId)
        print(yaml.dump(esaf))
    except Exception as reason:
        print(f"Exception: {reason}")


def cmd_list(args):
    """
    Subcommand ``list``: print proposals and ESAFs for beamline and run

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``

    New in release 1.3.9
    """
    beamline = args.beamlineName
    runs = server.parse_runs_arg(str(args.run).strip().lower())
    sector = int(beamline.split("-")[0])

    logger.debug("run(s): %s", runs)

    for run in sorted(runs, reverse=True):
        esafs = server.esafs(sector, run)
        proposals = server.proposals(beamline, run)

    print(f"Proposal(s): beam line {beamline}, run(s): {', '.join(runs)}")
    print(server.proposal_table(proposals))

    print(f"ESAF(s): sector {sector}, run(s): {', '.join(runs)}")
    print(server.esaf_table(esafs))


def cmd_now(args):
    """
    Subcommand ``now``: print information of proposals & ESAFs running now.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``

    New in release 2.0.0
    """
    beamline = args.beamlineName
    targetDate = datetime.datetime.now().astimezone()
    run = server.find_run(targetDate)
    sector = beamline.split("-")[0]
    esafs = [
        esaf
        for esaf in server.esafs(sector, run)
        # formatting comment
        if esaf.startDate <= targetDate <= esaf.endDate
    ]
    props = {
        prop.proposal_id: prop
        for prop in server.proposals(beamline, run).values()
        if prop.startDate <= targetDate <= prop.endDate
    }

    print(f"Proposal(s): beam line {beamline}, {targetDate}")
    print(server.proposal_table(props))

    print(f"ESAF(s): sector {sector}, {targetDate}")
    print(server.esaf_table(esafs))


def cmd_proposal(args):
    """
    Subcommand ``proposal``: print specific proposal for beamline and run.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    try:
        proposal = server.proposal(args.proposalId, args.beamlineName, args.run)
        print(yaml.dump(proposal.to_dict()))
    except Exception as reason:
        print(f"Exception: {reason}")


def cmd_runs(args):
    """
    Subcommand ``runs``: print APS run names.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    if args.full:
        table = pyRestTable.Table()
        table.labels = "run start end".split()

        def sorter(run):
            return run.startDate

        for run in sorted(server._runs.values(), key=sorter, reverse=args.ascending):
            table.addRow((str(run), run.startDate, run.endDate))
        print(str(table))
    else:
        printColumns(server.runs)


def cmd_search(args):
    """
    Subcommand ``search``: Print proposals and ESAFs for beamline and run matching the query.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    beamline = args.beamlineName
    query = args.query
    runs = str(args.run).strip().lower()
    title = f"Search: {beamline=!r} {runs=!r} {query=!r}"

    runs = server.parse_runs_arg(runs)
    sector = int(beamline.split("-")[0])

    # Index the ESAFs & Proposals for the beamline & runs.
    esafs, props = [], []
    for run in server.parse_runs_arg(runs):
        esafs += server.esafs(sector, run)
        props += list(server.proposals(beamline, run).values())

    results = server.search(query)  # bare API
    logger.debug("search: %s, results=%r", title, results)

    if len(results) == 0:
        print(f"{title} -- no matches")
    else:
        print(f"{title}")
        print(table_list(results))  # CLI output


def main():
    """Command-line interface for ``apsbss`` program."""
    args = get_options()
    if args.subcommand == "beamlines":
        printColumns(server.beamlines, numColumns=4, width=15)

    elif args.subcommand == "clear":
        epicsClear(args.prefix)

    elif args.subcommand == "runs":
        cmd_runs(args)

    elif args.subcommand == "esaf":
        cmd_esaf(args)

    elif args.subcommand == "list":
        cmd_list(args)

    elif args.subcommand == "now":
        cmd_now(args)

    elif args.subcommand == "proposal":
        cmd_proposal(args)

    elif args.subcommand == "search":
        cmd_search(args)

    elif args.subcommand == "setup":
        epicsSetup(args.prefix, args.beamlineName, args.run)

    elif args.subcommand == "update":
        epicsUpdate(args.prefix)

    elif args.subcommand == "report":
        epicsReport(args)

    else:
        parser.print_usage()


if __name__ == "__main__":
    main()

# -----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     jemian@anl.gov
# :copyright: (c) 2017-2025, UChicago Argonne, LLC
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------
