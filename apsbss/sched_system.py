"""
Support the APSU-era scheduling system restful web service from the IS group.

.. autosummary::

    ~IS_BeamtimeRequest
    ~IS_SchedulingServer

.. rubric:: Exceptions
.. autosummary::
    ~MissingAuthentication
    ~NotAllowedToRespond
    ~RequestNotFound
    ~SchedulingServerException
    ~Unauthorized

https://beam-api-dev.aps.anl.gov/beamline-scheduling/swagger-ui/index.html

"""

import datetime
import logging

from .core import ProposalBase
from .core import ScheduleInterfaceBase
from .core import User

logger = logging.getLogger(__name__)


class SchedulingServerException(RuntimeError):
    """Base for any exception from the scheduling server support."""


class MissingAuthentication(SchedulingServerException):
    """Incorrect or missing authentication details."""


class Unauthorized(SchedulingServerException):
    """Credentials valid but not authorized to access."""


class NotAllowedToRespond(SchedulingServerException):
    """Scheduling server is not allowed to respond to that request."""


class RequestNotFound(SchedulingServerException):
    """Beamtime request (proposal) was not found."""


class IS_BeamtimeRequest(ProposalBase):
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

    def __init__(self, raw: dict) -> None:
        self.raw = raw

    def __repr__(self):
        """Short summary of this beamtime request."""
        n_truncate = 40
        title = self.title
        if len(title) > n_truncate:
            title = title[: n_truncate - 4] + " ..."
        # fmt: off
        return (
            "IS_BeamtimeRequest("
            f"id:{self.proposal_id!r}"
            f", current:{self.current}"
            f", title:{title!r}" ")"
            f", pi:{self.pi!r}"
            ")"
        )
        # fmt: on

    def _dig(self, path, default={}):
        """Dig through the raw dictionary along the dotted path."""
        obj = self.raw
        num = len(path.split("."))
        for i, part in enumerate(path.split("."), start=1):
            fallback = {} if i < num else default
            obj = obj.get(part, fallback)
        return obj

    def _find_user(self, first, last):
        """Return the dictionary with the specified user."""
        full_name = f"{first} {last}"
        all_matches = [user for user in self._users if user.fullName == full_name]
        return all_matches

    @property
    def current(self) -> bool:
        """Is this proposal active now?"""
        try:
            now = datetime.datetime.now().astimezone()
            return self.startTime <= now <= self.endTime
        except ValueError:
            # Cannot determine (at least one of) the dates.
            return False

    @property
    def emails(self) -> list:
        """List of emails on this proposal."""
        return [user.email for user in self._users]

    @property
    def endTime(self) -> datetime.datetime:
        """Return the ending time of this proposal."""
        # FIXME: Too general! Is there a better source for this info?
        # Perhaps from an "activity"?
        return datetime.datetime.fromisoformat(self._dig("run.endTime", ""))

    @property
    def info(self) -> dict:
        """Details provided with this proposal."""

        info = {}
        info["Proposal GUP"] = self.proposal_id
        info["Proposal Title"] = self.title

        info["Start time"] = str(self.startTime)
        info["End time"] = str(self.endTime)

        pi = self._pi
        info["Users"] = [str(u) for u in self._users]
        info["PI Name"] = pi.fullName
        info["PI affiliation"] = pi.affiliation
        info["PI email"] = pi.email
        info["PI badge"] = pi.badge

        # Scheduling System rest interface provides this info
        # which is not available vi DM's API.
        info["Equipment"] = self._dig("beamtime.equipment", "")
        info["run"] = self.run
        if self._dig("proposalType", None) == "PUP":
            info["Proposal PUP"] = self._dig("proposal.pupId", "")

        return info

    @property
    def _pi(self) -> User:
        """Return first listed principal investigator or user."""
        default = None
        for user in self._users:
            if default is None:
                default = user  # Otherwise, pick the first one.
            if user.is_pi:
                return user
        return default

    @property
    def pi(self):
        """Return the full name and email of the principal investigator."""
        return str(self._pi)

    @property
    def proposal_id(self) -> str:
        """The proposal identifier."""
        return self._dig("proposal.gupId", "no GUP")

    @property
    def run(self) -> str:
        """The run identifier."""
        return self._dig("run.runName")

    @property
    def startTime(self) -> datetime.datetime:
        """Return the starting time of this proposal."""
        # FIXME: Too general! Is there a better source for this info?
        # Perhaps from an "activity"?
        return datetime.datetime.fromisoformat(self._dig("run.startTime", ""))

    @property
    def title(self) -> str:
        """The proposal title."""
        return self._dig("proposalTitle", "no title")

    @property
    def _users(self) -> object:
        """Return a list of all users, as 'User' objects."""
        return [User(u) for u in self._dig("beamtime.proposal.experimenters", [])]

    @property
    def users(self) -> list:
        """List of users (first & last names) on this proposal."""
        return [user.fullName for user in self._users]


class IS_SchedulingServer(ScheduleInterfaceBase):
    """
    Interact with the APS-U era beamline scheduling restful web server.

    .. autosummary::

        ~activeBeamlines
        ~auth_from_creds
        ~auth_from_file
        ~beamlines
        ~current_proposal
        ~current_run
        ~get_activities
        ~get_request
        ~proposals
        ~runs
        ~runsByDateTime
        ~runsByRunYear
        ~webget
    """

    dev_base = "https://beam-api-dev.aps.anl.gov/beamline-scheduling/sched-api"
    prod_base = "https://beam-api.aps.anl.gov/beamline-scheduling/sched-api"

    def __init__(self, dev=False) -> None:
        self.base = self.dev_base if dev else self.prod_base
        self.creds = None
        self.response = None  # Most-recent response object from web server.
        self._beamline = None  # Most-recent beamline
        self._run = None  # Most-recent run
        self._proposals = {}  # Proposals for beamline+run

    @property
    def activeBeamlines(self):
        """Details about all active beamlines in database."""
        return self.webget("beamline/findAllActiveBeamlines")

    @property
    def runs(self):
        """Details about all known runs in database."""
        return self.webget("run/getAllRuns")

    @property
    def authorizedBeamlines(self):
        """Beamlines where these credentials are authorized."""
        # TODO: just the beamline names?
        return self.webget("userBeamlineAuthorizedEdit/getAuthorizedBeamlines")

    def auth_from_creds(self, username, password):
        """Use credentials upplied as arguments."""
        import requests.auth

        logger.debug("Loading credentials.")
        self.creds = requests.auth.HTTPBasicAuth(username, password)

    def auth_from_file(self, creds_file):
        """Use credentials from a text file."""
        logger.debug("Loading credentials from file: %s", str(creds_file))
        creds = open(creds_file).read().strip().split()
        self.auth_from_creds(*creds)

    @property
    def beamlines(self):
        """List of all active beamlines, by name."""
        return sorted([entry["beamlineId"] for entry in self.activeBeamlines])

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
            Dictionary of 'BeamtimeRequest' objects, keyed by proposal ID,
            scheduled on 'beamline' for 'run'.

        Raises
        -------
        SchedulingServerException :
            Credentials are not authorized access to view beamtime requests (or
            proposals) from 'beamline'.
        """
        # TODO: cache proposals, such as ApsDmScheduleInterface
        # key = f"proposals-{beamline!r}-{run!r}"

        if run is None:
            run = self.current_run["runName"]

        # Server will validate if data from 'beamline' & 'run' can be provided.
        if beamline != self._beamline or run != self._run:
            # Only if not already in memeory.
            api = "beamtimeRequests/findBeamtimeRequestsByRunAndBeamline"
            api += f"/{run}/{beamline}"
            entries = self.webget(api)

            self._beamline = beamline
            self._run = run
            self._proposals = {}
            for entry in entries:
                proposal = IS_BeamtimeRequest(entry)
                self._proposals[proposal.proposal_id] = proposal

        return self._proposals

    def current_proposal(self, beamline: str):
        """Return the current (active) proposal or 'None'."""
        for proposal in self.proposals(beamline).values():
            if proposal.current:
                return proposal
        return None

    @property
    def current_run(self):
        """All details about the current run."""
        entries = self.webget("run/getCurrentRun")
        return entries[0]

    def get_activities(self, beamline, run=None):
        """How is this different from getRequestByRunAndBeamline()?"""
        if run is None:
            run = self.current_run["runName"]
        logger.warning("get_activities(%r, %r)", beamline, run)
        return self.webget(
            "activity/findByRunNameAndBeamlineId" f"/{run}/{beamline}",
        )

    def get_request(self, beamline, proposal_id, run=None):
        """Return the request (proposal) by beamline, id, and run."""
        if run is None:
            run = self.current_run["runName"]

        proposal = self.proposals(beamline).get(proposal_id)
        if proposal is None:
            raise RequestNotFound(f"{beamline=!r}, {proposal_id!r}, {run=!r}")
        return proposal

    def runsByDateTime(self, dateTime=None):
        """
        All details about runs in 'dateTime' (default to now).

        'dateTime' could be any of these types:

        =========== ================================================
        type        meaning
        =========== ================================================
        None        Default to the current time (in the local timezone).
        str         ISO8601-formatted date and time representation: "2024-12-01T08:21:00-06:00".
        datetime    A 'datetime.datetime' object.
        =========== ================================================
        """
        if dateTime is None:  # default to now
            dateTime = datetime.datetime.now().astimezone()
        if isinstance(dateTime, datetime.datetime):  # format as ISO8601
            dateTime = dateTime.isoformat(sep="T", timespec="seconds")
        return self.webget(f"run/getRunByDateTime/{dateTime}")

    def runsByRunYear(self, year=None):
        """All details about runs in 'year' (default to this year)."""
        if year is None:  # default to current year
            year = datetime.datetime.now().year
        return self.webget(f"run/getRunByRunYear/{year}")

    def webget(self, api):
        """
        Send 'api' request to server and GET its response.

        This is the low-level method to interact with the server, which requires
        authenticated access only.  A custom ``AuthenticationError`` is raised
        if credentials have not been provided.  Other custom exceptions could be
        raised, based on interpretation of the server's response.
        """
        import requests  # The name 'requests' might be used elsewhere.

        if self.creds is None:
            raise MissingAuthentication("Authentication is not set.")
        uri = f"{self.base}/{api}"
        logger.debug("URI: %r", uri)

        # main event: Send the server the URI, get the response
        self.response = requests.get(uri, auth=self.creds)
        if self.response is None:
            raise SchedulingServerException(f"None response from server.  {uri=!r}")
        logger.debug("response OK? %s", self.response.ok)

        if not self.response.ok:
            raiser = {
                "Unauthorized": Unauthorized,
                "Forbidden": NotAllowedToRespond,
            }.get(self.response.reason, SchedulingServerException)
            raise raiser(
                f"reason: {self.response.reason!r}"
                f", text: {self.response.text!r}"
                f", URL: {self.response.url!r}"
            )

        return self.response.json()
