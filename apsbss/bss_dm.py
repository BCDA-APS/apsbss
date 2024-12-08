"""
BSS_DM
======

Schedule info via APS Data Management Interface to IS Service.
"""

import logging

import dm  # APS data management library

from .core import DM_APS_DB_WEB_SERVICE_URL
from .core import ProposalBase
from .core import ScheduleInterfaceBase

logger = logging.getLogger(__name__)


class DM_BeamtimeProposal(ProposalBase):
    """
    Content of a single beamtime request (proposal).

    .. autosummary::

        ~current
        ~emails
        ~endTime
        ~info
        ~pi
        ~proposal_id
        ~startTime
        ~title
        ~users
    """

    # def __init__(self, raw) -> None:
    #     self._raw = raw  # dict-like object

    # def __repr__(self) -> str:
    #     """Text representation."""
    #     n_truncate = 40
    #     title = self.title
    #     if len(title) > n_truncate:
    #         title = title[: n_truncate - 4] + " ..."
    #     # fmt: off
    #     return (
    #         "DM_BeamtimeProposal("
    #         f"proposal_id:{self.proposal_id!r}"
    #         f", current:{self.current}"
    #         f", title:{title!r}" ")"
    #         f", pi:{self.pi!r}"
    #         ")"
    #     )
    #     # fmt: on

    # @property
    # def current(self) -> bool:
    #     """Is this proposal scheduled now?"""
    #     now = datetime.datetime.now().astimezone()
    #     try:
    #         return self.startTime <= now <= self.endTime
    #     except Exception:
    #         # Can't determine one of the terms.
    #         return False

    # @property
    # def emails(self) -> datetime.datetime:
    #     """Return a list of the names of all experimenters."""
    #     return [user.email for user in self._users]

    # @property
    # def endTime(self) -> datetime.datetime:
    #     """Return the ending time of this proposal."""
    #     return datetime.datetime.fromisoformat(self._raw["endTime"])

    # @property
    # def info(self) -> dict:
    #     """Details provided with this proposal."""
    #     pi = self._pi

    #     info = {}
    #     info["Proposal GUP"] = self.proposal_id
    #     info["Proposal Title"] = self.title

    #     info["Start time"] = str(self.startTime)
    #     info["End time"] = str(self.endTime)

    #     pi = self._pi
    #     info["Users"] = [str(u) for u in self._users]
    #     info["PI Name"] = pi.fullName
    #     info["PI affiliation"] = pi.affiliation
    #     info["PI email"] = pi.email
    #     info["PI badge"] = pi.badge

    #     # DM's API provides no info for these parameters:
    #     # info["Equipment"] = self._dig("beamtime.equipment", "")
    #     # info["run"] = self._dig("run.runName")
    #     # if self._dig("proposalType", None) == "PUP":
    #     #     info["Proposal PUP"] = self._dig("proposal.pupId", "")

    #     return info

    # @property
    # def _pi(self) -> User:
    #     """Return first listed principal investigator or user."""
    #     default = None
    #     for user in self._users:
    #         if default is None:
    #             default = user  # Otherwise, pick the first one.
    #         if user.is_pi:
    #             return user
    #     return default

    # @property
    # def pi(self) -> str:
    #     """Return the full name and email of the principal investigator."""
    #     return str(self._pi)

    # @property
    # def proposal_id(self) -> int:
    #     """Return the proposal number."""
    #     return self._raw["id"]

    # @property
    # def startTime(self) -> int:
    #     """Return the starting time of this proposal."""
    #     return datetime.datetime.fromisoformat(self._raw["startTime"])

    # @property
    # def title(self) -> int:
    #     """Return the proposal title."""
    #     return self._raw["title"]

    # @property
    # def _users(self) -> object:
    #     """Return a list of all users, as 'User' objects."""
    #     return [User(u) for u in self._raw["experimenters"]]

    # @property
    # def users(self) -> list:
    #     """Return a list of the names of all experimenters."""
    #     return [user.fullName for user in self._users]

    # def to_dict(self) -> dict:
    #     """Return the proposal content as a dictionary."""
    #     return dict(self._raw)


class ApsDmScheduleInterface(ScheduleInterfaceBase):
    """APS Data Management interface to scheduling system."""

    def __init__(self) -> None:
        self._cache = {}
        self.api = dm.BssApsDbApi(DM_APS_DB_WEB_SERVICE_URL)

    @property
    def beamlines(self) -> list:
        """List of names of all known beamlines."""
        if "beamlines" not in self._cache:
            beamlines = self.api.listBeamlines()
            self._cache["beamlines"] = [bl["name"] for bl in beamlines]
        return self._cache["beamlines"]

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
        # Server will validate if data from 'beamline' & 'run' can be provided.
        key = f"proposals-{beamline!r}-{run!r}"
        if key not in self._cache:
            proposals = self.api.listProposals(
                beamlineName=beamline,
                runName=run,
            )
            prop_dict = {}
            for prop in proposals:
                beamtime = DM_BeamtimeProposal(prop)
                prop_dict[beamtime.proposal_id] = beamtime
            self._cache[key] = prop_dict
        return self._cache[key]

    @property
    def _runs(self) -> list:
        """List of details of all known runs."""
        if "listRuns" not in self._cache:
            self._cache["listRuns"] = self.api.listRuns()
        return self._cache["listRuns"]

    @property
    def runs(self) -> list:
        """List of names of all known runs."""
        if "runs" not in self._cache:
            self._cache["runs"] = [run["name"] for run in self._runs]
        return self._cache["runs"]
