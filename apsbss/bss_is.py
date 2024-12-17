"""
BSS_IS
======

Support the APSU-era scheduling system restful web service from the IS group.

.. autosummary::

    ~IS_BeamtimeRequest
    ~IS_ScheduleSystem

.. rubric:: Exceptions
.. autosummary::
    ~IS_Exception
    ~IS_MissingAuthentication
    ~IS_NotAllowedToRespond
    ~IS_RequestNotFound
    ~IS_Unauthorized

https://beam-api-dev.aps.anl.gov/beamline-scheduling/swagger-ui/index.html
"""

import datetime
import logging

from .core import ProposalBase
from .core import Run
from .core import ScheduleInterfaceBase
from .core import User
from .core import iso2dt
from .core import miner

logger = logging.getLogger(__name__)


class IS_Exception(RuntimeError):
    """Base for any exception from the scheduling server support."""


class IS_MissingAuthentication(IS_Exception):
    """Incorrect or missing authentication details."""


class IS_Unauthorized(IS_Exception):
    """Credentials valid but not authorized to access."""


class IS_NotAllowedToRespond(IS_Exception):
    """Scheduling server is not allowed to respond to that request."""


class IS_RequestNotFound(IS_Exception):
    """Beamtime request (proposal) was not found."""


class IS_BeamtimeRequest(ProposalBase):
    """Content of a single beamtime request (proposal)."""

    def __init__(self, raw, _run) -> None:
        """
        Create a new instance.

        Parameters
        ----------
        raw : dict
            Dictionary-like object with raw information from the server.
        _run : str
            Ignored.
        """
        self._cache = {}
        self._raw = raw  # dict-like object

    def _find_user(self, first, last):
        """Return the dictionary with the specified user."""
        full_name = f"{first} {last}"
        all_matches = [user for user in self._users if user.fullName == full_name]
        return all_matches

    @property
    def endDate(self) -> datetime.datetime:
        """Return the ending time of this proposal."""
        iso = miner(self._raw, "activity.endTime")
        if iso is None:
            iso = miner(self._raw, "run.endTime", "")
        return iso2dt(iso)

    @property
    def info(self) -> dict:
        """Details provided with this proposal."""

        info = {}
        info["Proposal GUP"] = self.proposal_id
        info["Proposal Title"] = self.title

        info["Start time"] = str(self.startDate)
        info["End time"] = str(self.endDate)

        pi = self._pi
        info["Users"] = [str(u) for u in self._users]
        info["PI Name"] = pi.fullName
        info["PI affiliation"] = pi.affiliation
        info["PI email"] = pi.email
        info["PI badge"] = pi.badge

        # Scheduling System rest interface provides this info
        # which is not available vi DM's API.
        info["Equipment"] = miner(self._raw, "beamtime.equipment", "")
        info["run"] = self.run
        if miner(self._raw, "proposalType", None) == "PUP":
            info["Proposal PUP"] = miner(self._raw, "proposal.pupId", "")

        return info

    @property
    def proposal_id(self) -> str:
        """The proposal identifier."""
        return miner(self._raw, "proposal.gupId", "no GUP")

    @property
    def run(self) -> str:
        """The run identifier."""
        return miner(self._raw, "run.runName")

    @property
    def startDate(self) -> datetime.datetime:
        """Return the starting time of this proposal."""
        iso = miner(self._raw, "activity.startTime")
        if iso is None:
            iso = miner(self._raw, "run.startTime", "")
        return iso2dt(iso)

    @property
    def title(self) -> str:
        """The proposal title."""
        return miner(self._raw, "proposalTitle", "no title")

    @property
    def _users(self) -> list:
        """Return a list of all users, as 'User' objects."""
        return [User(u) for u in miner(self._raw, "beamtime.proposal.experimenters", [])]


class IS_ScheduleSystem(ScheduleInterfaceBase):
    """
    Interact with the APS-U era beamline schedule system.

    .. autosummary::

        ~activeBeamlines
        ~activities
        ~auth_from_creds
        ~auth_from_file
        ~beamlines
        ~current_proposal
        ~current_run
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
        super().__init__()
        self.creds = None
        self.response = None  # Most-recent response object from web server.

    @property
    def activeBeamlines(self):
        """Details about all active beamlines in database."""
        return self.webget("beamline/findAllActiveBeamlines")

    def activities(self, beamline, run=None) -> dict:
        """An "activity" describes scheduled beamtime."""
        if run is None:
            run = str(self.current_run)

        key = f"activities-{beamline!r}-{run!r}"
        if key not in self._cache:
            self._cache[key] = {
                miner(activity, "beamtime.proposal.gupId"): dict(activity)
                for activity in self.webget(
                    f"activity/findByRunNameAndBeamlineId/{run}/{beamline}",
                )
            }

        return self._cache[key]

    @property
    def authorizedBeamlines(self):
        """Beamlines where these credentials are authorized."""
        return self.webget("userBeamlineAuthorizedEdit/getAuthorizedBeamlines")

    def auth_from_creds(self, username, password):
        """Use credentials upplied as arguments."""
        import requests.auth  # noqa

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

    def current_proposal(self, beamline: str):
        """Return the current (active) proposal or 'None'."""
        for proposal in self.proposals(beamline).values():
            if proposal.current:
                return proposal
        return None

    # @property
    # def current_run(self):
    #     """All details about the current run."""
    #     entries = self.webget("run/getCurrentRun")
    #     return entries[0]

    def get_request(self, beamline, proposal_id, run=None):
        """Return the request (proposal) by beamline, id, and run."""
        if run is None:
            run = str(self.current_run)

        proposal = self.proposals(beamline).get(proposal_id)
        if proposal is None:
            raise IS_RequestNotFound(f"{beamline=!r}, {proposal_id!r}, {run=!r}")
        return proposal

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
        IS_Exception :
            Credentials are not authorized access to view beamtime requests (or
            proposals) from 'beamline'.
        """
        if run is None:
            run = str(self.current_run)

        key = f"proposals-{beamline!r}-{run!r}"
        if key not in self._cache:
            # Server will validate if data from 'beamline' & 'run' can be provided.
            api = "beamtimeRequests/findBeamtimeRequestsByRunAndBeamline"
            api += f"/{run}/{beamline}"
            entries = self.webget(api)

            prop_dict = {}
            for entry in entries:
                proposal = IS_BeamtimeRequest(entry, run)
                gupId = proposal.proposal_id
                activity = self.activities(beamline, run).get(gupId)
                if activity is not None:
                    entry["activity"] = activity
                    proposal = IS_BeamtimeRequest(entry, run)
                prop_dict[gupId] = proposal

            self._cache[key] = prop_dict

        return self._cache[key]

    @property
    def _runs(self) -> list:
        """Details about all known runs in database."""
        if "listRuns" not in self._cache:
            self._cache["listRuns"] = [Run(run) for run in self.webget("run/getAllRuns")]
        return self._cache["listRuns"]

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
            raise IS_MissingAuthentication("Authentication is not set.")
        uri = f"{self.base}/{api}"
        logger.debug("URI: %r", uri)

        # main event: Send the server the URI, get the response
        self.response = requests.get(uri, auth=self.creds)
        if self.response is None:
            raise IS_Exception(f"None response from server.  {uri=!r}")
        logger.debug("response OK? %s", self.response.ok)

        if not self.response.ok:
            raiser = {
                "Unauthorized": IS_Unauthorized,
                "Forbidden": IS_NotAllowedToRespond,
            }.get(self.response.reason, IS_Exception)
            raise raiser(
                f"reason: {self.response.reason!r}"
                f", text: {self.response.text!r}"
                f", URL: {self.response.url!r}"
            )

        return self.response.json()
