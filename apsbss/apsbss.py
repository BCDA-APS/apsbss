#!/usr/bin/env python

"""
Retrieve specific records from the APS Proposal and ESAF databases.

This code provides the command-line application: ``apsbss``

.. note:: BSS: APS Beamline Scheduling System

EXAMPLES::

    apsbss current
    apsbss esaf 226319
    apsbss proposal 66083 2020-2 9-ID-B,C

EPICS SUPPORT

.. autosummary::

    ~connect_epics
    ~epicsClear
    ~epicsSetup
    ~epicsUpdate

APS ESAF & PROPOSAL ACCESS

.. autosummary::

    ~printColumns
    ~trim

APPLICATION

.. autosummary::

    ~cmd_current
    ~cmd_esaf
    ~cmd_list
    ~cmd_proposal
    ~get_options
    ~main
"""

# -----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     jemian@anl.gov
# :copyright: (c) 2017-2025, UChicago Argonne, LLC
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------

import datetime
import logging
import os
import sys
import time
import warnings

import pyRestTable
import yaml

from .servers import Server

CONNECT_TIMEOUT = 5
POLL_INTERVAL = 0.01
logger = logging.getLogger(__name__)
parser = None
server = Server()


class EpicsNotConnected(Exception): ...


def connect_epics(prefix):
    """
    Connect with the EPICS database instance.

    PARAMETERS

    prefix
        *str* :
        EPICS PV prefix
    """
    from .apsbss_ophyd import EpicsBssDevice

    t0 = time.time()
    t_timeout = t0 + CONNECT_TIMEOUT
    bss = EpicsBssDevice(prefix, name="bss")
    while not bss.connected and time.time() < t_timeout:
        time.sleep(POLL_INTERVAL)
    if not bss.connected:
        raise EpicsNotConnected(f"Did not connect with EPICS {prefix} in {CONNECT_TIMEOUT}s")
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
    proposal_id = bss.proposal.proposal_id.get().strip()

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
        esaf = server.get_esaf(esaf_id)

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

    if len(proposal_id) > 0:
        bss.status_msg.put(f"get Proposal {proposal_id} from APS ...")
        proposal = server.get_proposal(proposal_id, beamline, run)

        bss.status_msg.put("set Proposal PVs ...")
        bss.proposal.end_date.put(proposal["endTime"])
        bss.proposal.mail_in_flag.put(proposal.get("mailInFlag") in ("Y", "y"))
        bss.proposal.proprietary_flag.put(proposal.get("proprietaryFlag") in ("Y", "y"))
        bss.proposal.raw.put(yaml.dump(proposal))
        bss.proposal.start_date.put(proposal["startTime"])
        bss.proposal.submitted_date.put(proposal["submittedDate"])
        bss.proposal.title.put(proposal["title"])

        bss.proposal.user_last_names.put(",".join([user["lastName"] for user in proposal["experimenters"]]))
        bss.proposal.user_badges.put(",".join([user["badge"] for user in proposal["experimenters"]]))
        bss.proposal.number_users_in_pvs.put(0)
        for i, user in enumerate(proposal["experimenters"]):
            obj = getattr(bss.proposal, f"user{i+1}")
            obj.badge_number.put(user["badge"])
            obj.email.put(user["email"])
            obj.first_name.put(user["firstName"])
            obj.last_name.put(user["lastName"])
            obj.institution.put(user["institution"])
            obj.institution_id.put(str(user["instId"]))
            obj.user_id.put(str(user["id"]))
            obj.pi_flag.put(user.get("piFlag") in ("Y", "y"))
            bss.proposal.number_users_in_pvs.put(i + 1)
            if i == 8:
                break
        bss.proposal.number_users_total.put(len(proposal["experimenters"]))

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
        Name of APS run cycle (as defined by the BSS).
        optional: default is current APS run cycle name.
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

    bss.status_msg.put("clear PVs ...")
    bss.clear()

    bss.status_msg.put("write PVs ...")
    bss.esaf.aps_run.put(run)
    bss.proposal.beamline_name.put(beamline)
    bss.esaf.sector.put(str(sector))
    bss.status_msg.put("Done")


def printColumns(items, numColumns=5, width=10):
    """
    Print a list of ``items`` in column order.

    PARAMETERS

    items
        *[str]* :
        List of items to report
    numColumns
        *int* :
        number of columns, optional (default: 5)
    width
        *int* :
        width of each column, optional (default: 10)
    """
    n = len(items)
    rows = n // numColumns
    if n % numColumns > 0:
        rows += 1
    for base in range(0, rows):
        row = [items[base + k * rows] for k in range(numColumns) if base + k * rows < n]
        print("".join([f"{s:{width}s}" for s in row]))


def printEsafTable(records, title=""):
    """
    Print the list of ESAFs as a table.

    PARAMETERS

    records
        *[obj]* :
        List of ESAF dictionaries.
    title
        *str* :
        Text to print before the table.
    """

    def esaf_sorter(prop):
        return prop["experimentStartDate"]

    table = pyRestTable.Table()
    table.labels = "id status start end user(s) title".split()
    for item in sorted(records, key=esaf_sorter, reverse=True):
        users = trim(
            ",".join([user["lastName"] for user in item["experimentUsers"]]),
            20,
        )
        table.addRow(
            (
                item["esafId"],
                item["esafStatus"],
                item["experimentStartDate"].split()[0],
                item["experimentEndDate"].split()[0],
                users,
                trim(item["esafTitle"], 40),
            )
        )
    print(f"{title}\n\n{table}")


def printProposalTable(records, title=""):
    """
    Print the list of proposals as a table.

    PARAMETERS

    records
        *[obj]* :
        List of proposal dictionaries.
    title
        *str* :
        Text to print before the table.
    """

    def prop_sorter(prop):
        return prop.startTime

    table = pyRestTable.Table()
    table.labels = "id run start end user(s) title".split()
    for item in sorted(records.values(), key=prop_sorter, reverse=True):
        users = trim(
            ",".join([user.lastName for user in item._users]),
            20,
        )
        # logger.debug("%s %s %s", item["startTime"], tNow, item["endTime"])
        table.addRow(
            (
                item.proposal_id,
                item.run,
                item.startTime,
                item.endTime,
                users,
                trim(item.title),
            )
        )
    print(f"{title}\n\n{table}")


def trim(text, length=40):
    """
    Return a string that is no longer than ``length``.

    If a string is longer than ``length``, it is shortened
    to the ``length-3`` characters, then, ``...`` is appended.
    For very short length, the string is shortened to ``length``
    (and no ``...`` is appended).

    PARAMETERS

    text
        *str* :
        String, potentially longer than ``length``
    length
        *int* :
        maximum length, optional (default: 40)
    """
    if length < 1:
        raise ValueError(f"length must be positive, received {length}")
    if length < 5:
        text = text[:length]
    elif len(text) > length:
        text = text[: length - 3] + "..."
    return text


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

    p_sub = subcommand.add_parser("runs", help="print APS run cycle names")
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
        "APS run (cycle) name."
        "  One of the names returned by ``apsbss runs``"
        " or one of these (``past``,  ``prior``, ``previous``)"
        " for the previous run, (``current`` or ``now``)"
        " for the current run, (``future`` or ``next``)"
        " for the next run."
        # " or ``recent`` for the past two years."  # TODO: re-enable
    )
    p_sub.add_argument(
        "-r",
        "--run",
        type=str,
        default="now",
        # TODO: nargs="?",
        help=msg,
    )
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

    p_sub = subcommand.add_parser("proposal", help="print specific proposal")
    p_sub.add_argument("proposalId", type=str, help="proposal ID number")
    p_sub.add_argument("run", type=str, help="APS run (cycle) name")
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")

    p_sub = subcommand.add_parser("clear", help="EPICS PVs: clear")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")

    p_sub = subcommand.add_parser("setup", help="EPICS PVs: setup")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")
    p_sub.add_argument("beamlineName", type=str, help="Beamline name")
    p_sub.add_argument("run", type=str, help="APS run (cycle) name")

    p_sub = subcommand.add_parser("update", help="EPICS PVs: update from BSS")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")

    p_sub = subcommand.add_parser("report", help="EPICS PVs: report what is in the PVs")
    p_sub.add_argument("prefix", type=str, help="EPICS PV prefix")

    return parser.parse_args()


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


def cmd_esaf(args):
    """
    Handle ``esaf`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    try:
        esaf = server.get_esaf(args.esafId)
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

    if not len(run) or run in "now current".split():
        run = server.current_run
    # elif run == "all":  # TODO: re-enable
    #     run = server.runs
    elif run in "future next".split():
        runs = server.runs
        item = runs.index(server.current_run) + 1
        if item >= len(runs):
            print("No future run information available at this time.")
            return
        run = runs[item]
    elif run in "past previous prior".split():
        runs = server.runs
        item = runs.index(server.current_run) - 1
        if item < 0:
            print("No previous run information available.")
            return
        run = runs[item]
    # elif run == "recent":  # TODO re-enable
    #     run = server.recent_runs()

    if run not in server.runs:
        raise KeyError(f"Could not find APS {run=!r}")

    logger.debug("run(s): %s", run)

    printProposalTable(
        server.proposals(args.beamlineName, run),
        "Proposal(s): " f" beam line {args.beamlineName}" f",  run(s) {args.run}",
    )
    printEsafTable(
        server.esafs(sector, run),
        f"ESAF(s):  sector {sector},  run(s) {args.run}",
    )


def cmd_proposal(args):
    """
    Handle ``proposal`` command.

    PARAMETERS

    args
        *obj* :
        Object returned by ``argparse``
    """
    try:
        proposal = server.get_proposal(args.proposalId, args.beamlineName, args.run)
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
    from apstools.utils import listdevice  # TODO: HEAVY addition for one function

    bss = connect_epics(args.prefix)
    listdevice(bss)


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

    elif args.subcommand == "proposal":
        cmd_proposal(args)

    elif args.subcommand == "setup":
        epicsSetup(args.prefix, args.beamlineName, args.run)

    elif args.subcommand == "update":
        epicsUpdate(args.prefix)

    elif args.subcommand == "report":
        cmd_report(args)

    else:
        parser.print_usage()


if __name__ == "__main__":
    main()
