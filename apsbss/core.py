"""
Core components
===============

.. autosummary::

    ~iso2dt
    ~miner
    ~printColumns
    ~ProposalBase
    ~ScheduleInterfaceBase
    ~trim
    ~User
"""

import abc
import datetime

DM_APS_DB_WEB_SERVICE_URL = "https://xraydtn01.xray.aps.anl.gov:11236"


def iso2dt(isodate) -> datetime.datetime:
    """
    Convert a text ISO8601 date into a ``datetime`` object.

    PARAMETERS

    isodate : str
        Date and time in modified ISO8601 format. (e.g.: ``2020-07-01
        12:34:56.789012``) Fractional seconds are optional.
    """
    return datetime.datetime.fromisoformat(isodate).astimezone()


def miner(root, path: str, default=None):
    """
    Return a value from a nested dictionary-like structure.

    root : dict-like
        The nested dictionary-like structure.
    path: str
        Text description of the keys to be navigated.  Keys are separated by dots.
    default : object
        Return this value if 'path' is not found.
        Default is 'None.
    """
    obj = root
    num = len(path.split("."))
    for i, part in enumerate(path.split("."), start=1):
        fallback = {} if i < num else default
        obj = obj.get(part, fallback)
    return obj


def printColumns(items, numColumns=5, width=10):
    """
    Print a list of ``items`` in column order.

    PARAMETERS

    items : [str]
        List of items to report
    numColumns : int
        number of columns, optional (default: 5)
    width : int
        width of each column, optional (default: 10)
    """
    n = len(items)
    rows = n // numColumns
    if n % numColumns > 0:
        rows += 1
    for base in range(0, rows):
        # fmt: off
        row = [
            items[base + k * rows]
            for k in range(numColumns)
            if base + k * rows < n
        ]
        # fmt: on
        print("".join([f"{s:{width}s}" for s in row]))


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


class User:
    """
    A single user on a proposal (beamtime request).

    .. rubric:: Property Methods
    .. autosummary::
        ~affiliation
        ~badge
        ~email
        ~firstName
        ~fullName
        ~lastName
        ~is_pi
    """

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

    Override any of the methods to access the raw data from the server.

    .. autosummary::
        ~to_dict

    .. rubric:: Property Methods
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

    def __init__(self, raw, run) -> None:
        """
        Create a new instance.

        Parameters
        ----------
        raw : dict
            Dictionary-like object with raw information from the server.
        run : str
            Canonical name of the run with this proposal.
        """
        self._cache = {}
        self._raw = raw  # dict-like object
        self.run = run

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
        found = None
        if "PI" not in self._cache:
            default = None
            for user in self._users:
                if default is None:
                    default = user  # Otherwise, pick the first one.
                if user.is_pi:
                    found = user
                    break
            self._cache["PI"] = found or default
        return self._cache["PI"]

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
    """
    Base class for interface to any scheduling system.

    Override any of the methods to access the raw data from the server.

    .. autosummary::
        ~getProposal

    .. rubric:: Property Methods
    .. autosummary::
        ~beamlines
        ~current_run
        ~proposals
        ~_runs
        ~runs
    """

    def __init__(self) -> None:
        self._cache = {}

    @property
    @abc.abstractmethod
    def beamlines(self) -> list:
        """List of all known beamlines, by name."""

    @property
    def current_run(self) -> dict:
        """All details about the current run."""
        now = datetime.datetime.now().astimezone()
        for run in self._runs:
            start = run["startTime"]
            end = run["endTime"]
            if start <= now <= end:
                return run
        return {}

    def getProposal(self, proposal_id, beamline, run):
        """Get 'proposal_id' for 'beamline' during 'run'.  None if not found."""
        return self.proposals(beamline, run).get(proposal_id)

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
    def _runs(self) -> list:
        """
        Details (from server) about all known runs.

        The returned value of is a list of dictionaries where each dict contains
        the details of a single run.

        =========   =================   ===============================
        key         type                description
        =========   =================   ===============================
        name        str                 name of the run
        startTime   datetime.datetime   when run starts (with timezone)
        endTime     datetime.datetime   when run ends (with timezone)
        =========   =================   ===============================
        """

    @property
    def runs(self) -> list:
        """List of names of all known runs."""
        if "runs" not in self._cache:
            self._cache["runs"] = [run["name"] for run in self._runs]
        return self._cache["runs"]
