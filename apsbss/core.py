"""
Core components.

.. autosummary::

    ~ProposalBase
    ~ScheduleInterfaceBase
    ~User
"""

import abc
import datetime

DM_APS_DB_WEB_SERVICE_URL = "https://xraydtn01.xray.aps.anl.gov:11236"


class User:
    """A single user on a proposal (beamtime request)."""

    def __init__(self, raw):
        self._raw = raw  # dict-like object

    def __repr__(self) -> str:
        """firstName lastName <email>"""
        return f"{self.fullName} <{self.email}>"

    @property
    def affiliation(self):
        """Name of affiliation (institution)."""
        return self._raw["institution"]

    @property
    def badge(self) -> str:
        """ANL badge number"""
        return self._raw["badge"]

    @property
    def email(self) -> str:
        """Email address"""
        return self._raw.get("email", "")

    @property
    def firstName(self) -> str:
        """Given name."""
        return self._raw["firstName"]

    @property
    def fullName(self) -> str:
        """firstName lastName"""
        return f'{self._raw["firstName"]} {self._raw["lastName"]}'

    @property
    def lastName(self) -> str:
        """Family name."""
        return self._raw["lastName"]

    @property
    def is_pi(self) -> bool:
        """Is this user the principal investigator?"""
        return (self._raw.get("piFlag") or "n").lower()[0] == "y"


class ProposalBase(abc.ABC):
    """
    Base class for a single beam time request (proposal).

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

    def __init__(self, raw) -> None:
        self._raw = raw  # dict-like object

    def __repr__(self) -> str:
        """Text representation."""
        n_truncate = 40
        title = self.title
        if len(title) > n_truncate:
            title = title[: n_truncate - 4] + " ..."
        # fmt: off
        return (
            f"{self.__class__.__name__}("
            f"proposal_id:{self.proposal_id!r}"
            f", current:{self.current}"
            f", title:{title!r}" ")"
            f", pi:{self.pi!r}"
            ")"
        )
        # fmt: on

    @property
    def current(self) -> bool:
        """Is this proposal scheduled now?"""
        now = datetime.datetime.now().astimezone()
        try:
            return self.startTime <= now <= self.endTime
        except Exception:
            # Can't determine one of the terms.
            return False

    @property
    def emails(self) -> datetime.datetime:
        """Return a list of the names of all experimenters."""
        return [user.email for user in self._users]

    @property
    def endTime(self) -> datetime.datetime:
        """Return the ending time of this proposal."""
        return datetime.datetime.fromisoformat(self._raw["endTime"])

    @property
    def info(self) -> dict:
        """Details provided with this proposal."""
        info = {}
        info["Proposal GUP"] = self.proposal_id
        info["Proposal Title"] = self.title

        info["Start time"] = str(self.startTime)
        info["End time"] = str(self.endTime)

        info["Users"] = [str(u) for u in self._users]

        pi = self._pi
        info["PI Name"] = pi.fullName
        info["PI affiliation"] = pi.affiliation
        info["PI email"] = pi.email
        info["PI badge"] = pi.badge

        return info

    @property
    def _pi(self) -> User:
        """Return first listed principal investigator or user."""
        # TODO: Cache the value, once found?
        default = None
        for user in self._users:
            if default is None:
                default = user  # Otherwise, pick the first one.
            if user.is_pi:
                return user
        return default

    @property
    def pi(self) -> str:
        """Return the full name and email of the principal investigator."""
        return str(self._pi)

    @property
    def proposal_id(self) -> int:
        """Return the proposal number."""
        return self._raw["id"]

    @property
    def startTime(self) -> int:
        """Return the starting time of this proposal."""
        return datetime.datetime.fromisoformat(self._raw["startTime"])

    @property
    def title(self) -> int:
        """Return the proposal title."""
        return self._raw["title"]

    @property
    def _users(self) -> object:
        """Return a list of all users, as 'User' objects."""
        return [User(u) for u in self._raw["experimenters"]]

    @property
    def users(self) -> list:
        """Return a list of the names of all experimenters."""
        return [user.fullName for user in self._users]

    def to_dict(self) -> dict:
        """Return the proposal content as a dictionary."""
        return dict(self._raw)


class ScheduleInterfaceBase(abc.ABC):
    """Base class for interface to any scheduling system."""

    # TODO generalize from subclasses

    @property
    @abc.abstractmethod
    def beamlines(self) -> list:
        """List of all known beamlines, by name."""

    @property
    def current_run(self) -> dict:
        """All details about the current run."""
        now = datetime.datetime.now().astimezone()
        for run in self.runs:
            start = run.startTime
            end = run.endTime
            if start <= now <= end:
                return run
        return {}

    def getProposal(self, proposal_id, beamline, cycle):
        """Get 'proposal_id' for 'beamline' during 'run'.  None if not found."""
        return self.proposals(beamline, cycle).get(proposal_id)

    @abc.abstractmethod
    def proposals(self, beamline: str, run: str = None) -> dict:
        """
        Get all proposal (beamtime request) details for 'beamline' and 'run'.

        Credentials must match to the specific beamline.

        Parameters
        ----------
        beamline : str
            beamline ID as stored in the APS scheduling system, e.g. 2-BM-A,B or 7-BM-B or 32-ID-B,C
        run : str
            Run name e.g. '2024-1'.  Default: name of the current run.

        Returns
        -------
        proposals : dict
            Dictionary of 'ProposalBase' objects, keyed by proposal number,
            scheduled on 'beamline' for 'run'.
        """

    @property
    @abc.abstractmethod
    def runs(self) -> list:
        """Details (from server) about all known runs."""
