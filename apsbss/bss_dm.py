"""
BSS_DM
======

Schedule info via APS Data Management Interface to IS Service.

.. autosummary::

    ~DM_BeamtimeProposal
    ~DM_ScheduleInterface
"""

import datetime
import logging

import dm  # APS data management library

from .core import DM_APS_DB_WEB_SERVICE_URL
from .core import ProposalBase
from .core import ScheduleInterfaceBase

logger = logging.getLogger(__name__)


class DM_BeamtimeProposal(ProposalBase):
    """Content of a single beamtime request (proposal)."""


class DM_ScheduleInterface(ScheduleInterfaceBase):
    """APS Data Management interface to schedule system."""

    def __init__(self) -> None:
        super().__init__()
        self.api = dm.BssApsDbApi(DM_APS_DB_WEB_SERVICE_URL)

    @property
    def beamlines(self) -> list:
        """List of names of all known beamlines."""
        if "beamlines" not in self._cache:
            beamlines = self.api.listBeamlines()
            self._cache["beamlines"] = [bl["name"] for bl in beamlines]
        return self._cache["beamlines"]

    # @property
    # def current_run(self) -> dict:
    #     """All details about the current run."""
    #     now = datetime.datetime.now().astimezone()
    #     for run in self._runs:
    #         start = datetime.datetime.fromisoformat(run["startTime"])
    #         end = datetime.datetime.fromisoformat(run["endTime"])
    #         if start <= now <= end:
    #             return run
    #     return {}

    def proposals(self, beamline, run) -> dict:
        """
        Get all proposal (beamtime request) details for 'beamline' and 'run'.

        PARAMETERS

        beamline : str
            Name of beam line (as defined in 'self.beamlines').
        run : str
            APS run name (as defined in 'self.runs').

        Returns
        -------
        proposals : dict
            Dictionary of 'BeamtimeRequest' objects, keyed by proposal ID,
            scheduled on 'beamline' for 'run'.
        """
        key = f"proposals-{beamline!r}-{run!r}"
        if key not in self._cache:
            # Server will validate if data from 'beamline' & 'run' can be provided.
            proposals = self.api.listProposals(
                beamlineName=beamline,
                runName=run,
            )
            prop_dict = {}
            for prop in proposals:
                beamtime = DM_BeamtimeProposal(prop, run)
                prop_dict[beamtime.proposal_id] = beamtime
            self._cache[key] = prop_dict
        return self._cache[key]

    @property
    def _runs(self) -> list:
        """List of details of all known runs."""
        if "listRuns" not in self._cache:
            run_list = []
            for run in self.api.listRuns():
                rdict = {"name": run["name"]}
                for key in "startTime endTime".split():
                    value = datetime.datetime.fromisoformat(run[key]).astimezone()
                    rdict[key] = value
                run_list.append(rdict)
            self._cache["listRuns"] = run_list
        return self._cache["listRuns"]

    # @property
    # def runs(self) -> list:
    #     """List of names of all known runs."""
    #     if "runs" not in self._cache:
    #         self._cache["runs"] = [run["name"] for run in self._runs]
    #     return self._cache["runs"]
