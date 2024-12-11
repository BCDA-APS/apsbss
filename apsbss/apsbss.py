#!/usr/bin/env python

"""
Retrieve specific records from the APS Proposal and ESAF databases.

This code provides the command-line application: ``apsbss``

.. note:: BSS: APS Beamline Scheduling System

EXAMPLES::

    apsbss current
    apsbss esaf 226319
    apsbss proposal 66083 2020-2 9-ID-B,C

.. rubric:: Application
.. autosummary::

    ~cmd_esaf
    ~cmd_list
    ~cmd_proposal
    ~cmd_report
    ~cmd_runs
    ~get_options
    ~main


.. rubric:: EPICS Support
.. autosummary::

    ~connect_epics
    ~epicsClear
    ~epicsSetup
    ~epicsUpdate
"""

import logging
import os
import sys
import time

import pyRestTable
import yaml

from .core import printColumns
from .server_interface import Server

CONNECT_TIMEOUT = 3
logger = logging.getLogger(__name__)
parser = None
server = Server()


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
        bss.esaf.end_date.put(esaf["experimentEndDate"])
        bss.esaf.esaf_status.put(esaf["esafStatus"])
        bss.esaf.raw.put(yaml.dump(esaf))
        bss.esaf.start_date.put(esaf["experimentStartDate"])
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
        bss.proposal.end_date.put(str(proposal.endTime))
        bss.proposal.mail_in_flag.put(proposal._raw.get("mailInFlag") in ("Y", "y"))
        bss.proposal.proprietary_flag.put(proposal._raw.get("proprietaryFlag") in ("Y", "y"))
        bss.proposal.raw.put(yaml.dump(proposal))
        bss.proposal.start_date.put(str(proposal.startTime))
        bss.proposal.submitted_date.put(proposal._raw["submittedDate"])
        bss.proposal.title.put(proposal.title)

        bss.proposal.user_last_names.put(",".join([user.lastName for user in proposal._users]))
        bss.proposal.user_badges.put(",".join([user.badge for user in proposal._users]))
        bss.proposal.number_users_in_pvs.put(0)
        for i, user in enumerate(proposal._users):
            obj = getattr(bss.proposal, f"user{i+1}")
            obj.badge_number.put(user.badge)
            obj.email.put(user.email)
            obj.first_name.put(user.firstName)
            obj.last_name.put(user.lastName)
            obj.institution.put(user._raw["institution"])
            obj.institution_id.put(str(user._raw["instId"]))
            obj.user_id.put(str(user._raw["id"]))
            obj.pi_flag.put(user.is_pi)
            bss.proposal.number_users_in_pvs.put(i + 1)
            if i == 8:
                break
        bss.proposal.number_users_total.put(len(proposal.users))

    bss.status_msg.put("Done")


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

    p_sub = subcommand.add_parser("esaf", help="print specific ESAF")
    p_sub.add_argument("esafId", type=int, help="ESAF ID number")

    p_sub = subcommand.add_parser("list", help="list by run")
    msg = (
        "APS run name."
        "  One of the names returned by ``apsbss runs``"
        " or one of these (``past``,  ``prior``, ``previous``)"
        " for the previous run, (``current`` or ``now``)"
        " for the current run, (``future`` or ``next``)"
        " for the next run,"
        " or ``recent`` for the past two years."
    )
    p_sub.add_argument(
        "-r",
        "--run",
        type=str,
        default="now",
        help=msg,
    )
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

    p_sub = subcommand.add_parser("proposal", help="print specific proposal")
    p_sub.add_argument("proposalId", type=str, help="proposal ID number")
    p_sub.add_argument("run", type=str, help="APS run name")
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

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
    Handle ``esaf`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    try:
        esaf = server.esaf(args.esafId)
        print(yaml.dump(esaf))
    except Exception as reason:
        print(f"DM reported: {reason}")


def cmd_list(args):
    """
    Handle ``list`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``

    New in release 1.3.9
    """
    run = str(args.run).strip().lower()
    sector = int(args.beamlineName.split("-")[0])

    logger.debug("run(s): %s", run)

    print(f"Proposal(s): beam line {args.beamlineName}, run(s) {args.run}")
    print(server._proposal_table(args.beamlineName, args.run))

    print(f"ESAF(s): sector {sector}, run(s) {args.run}")
    print(server._esaf_table(sector, args.run))


def cmd_proposal(args):
    """
    Handle ``proposal`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    try:
        proposal = server.proposal(args.proposalId, args.beamlineName, args.run)
        print(yaml.dump(proposal))
    except Exception as reason:
        print(f"DM reported: {reason}")


def cmd_report(args):
    """
    Handle ``report`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    bss = connect_epics(args.prefix)
    print(bss._table(length=30))


def cmd_runs(args):
    """
    Handle ``runs`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    if args.full:
        table = pyRestTable.Table()
        table.labels = "run start end".split()

        def sorter(entry):
            return entry["startTime"]

        for entry in sorted(server._runs, key=sorter, reverse=args.ascending):
            table.addRow(
                (
                    entry["name"],
                    entry["startTime"],
                    entry["endTime"],
                )
            )
        print(str(table))
    else:
        printColumns(server.runs)


def main():
    """Command-line interface for ``apsbss`` program."""
    args = get_options()
    if args.subcommand == "beamlines":
        printColumns(server.beamlines, numColumns=4, width=15)  # TODO: untested

    elif args.subcommand == "clear":
        epicsClear(args.prefix)  # TODO: untested

    elif args.subcommand == "runs":
        cmd_runs(args)  # TODO: untested

    elif args.subcommand == "esaf":
        cmd_esaf(args)  # TODO: untested

    elif args.subcommand == "list":
        cmd_list(args)

    elif args.subcommand == "proposal":  # TODO: untested
        cmd_proposal(args)

    elif args.subcommand == "setup":  # TODO: untested
        epicsSetup(args.prefix, args.beamlineName, args.run)

    elif args.subcommand == "update":  # TODO: untested
        epicsUpdate(args.prefix)

    elif args.subcommand == "report":  # TODO: untested
        cmd_report(args)

    else:
        parser.print_usage()  # TODO: untested


if __name__ == "__main__":
    main()  # TODO: untested

# -----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     jemian@anl.gov
# :copyright: (c) 2017-2025, UChicago Argonne, LLC
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------
