"""
Support the APSU-era scheduling system restful web service.

.. autosummary::

    ~BeamtimeRequest
    ~SchedulingServer

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


class BeamtimeRequest:
    """
    A single beamtime request (proposal).

    .. autosummary::

        ~current
        ~emails
        ~experiment_info
        ~pi
        ~proposal_id
        ~title
        ~users

    Compare with Francesco's draft code:
    https://github.com/decarlof/sandbox/blob/d1cbe8a1d0a07f9b730c9f71a21c38bf21ffc57a/rest-api/connect_schedule_01.py#L49C5-L49C16
    """

    def __init__(self, raw: dict) -> None:
        self.raw = raw

    @property
    def current(self) -> bool:
        """Is this proposal active now?"""
        try:
            now = datetime.datetime.now().astimezone()
            start = datetime.datetime.fromisoformat(self._dig("run.startTime", ""))
            end = datetime.datetime.fromisoformat(self._dig("run.endTime", ""))
            return start <= now <= end
        except ValueError:
            # Cannot determine (at least one of) the dates.
            return False

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
        matches = [
            user
            for user in self._dig("beamtime.proposal.experimenters", [])
            if user["firstName"] == first and user["lastName"] == last
        ]
        return matches

    @property
    def emails(self) -> list:
        """List of emails on this proposal."""
        return [
            user["email"]
            for user in self._dig("proposal.experimenters", [])
        ]

    @property
    def experiment_info(self) -> dict:
        """Experiment details provided with this proposal."""
        pi = self._find_user(self._dig("piFirstName", ""), self._dig("piLastName", ""))[0]

        info = {}
        info["run"] = self._dig("run.runName")
        info["PI Name"] = f'{pi["firstName"]} {pi["lastName"]}'
        info["PI affiliation"] = pi["institution"]
        info["PI email"] = pi["email"]
        info["PI badge"] = pi["badge"]
        info["Proposal GUP"] = self.proposal_id
        info["Proposal Title"] = self.title
        if self._dig("proposalType", None) == "PUP":
            info["Proposal PUP"] = self._dig("proposal.pupId", "")

        info["Equipment"] = self._dig("beamtime.equipment", "")
        
        # is there a better choice for these times?
        info["Start time"] = self._dig("run.startTime", "")
        info["End time"] = self._dig("run.endTime", "")
        info["User email addresses"] = self.emails

        return info

    @property
    def pi(self) -> str:
        """Principal Investigator (last name) on this proposal."""
        return self.raw.get("piLastName", {})

    @property
    def proposal_id(self) -> str:
        """The proposal identifier."""
        return self._dig("proposal.gupId", "no GUP")

    @property
    def title(self) -> str:
        """The proposal title."""
        return self._dig("proposalTitle", "no title")

    @property
    def users(self) -> list:
        """List of users (first & last names) on this proposal."""
        return [
            f'{user["firstName"]} {user["lastName"]}'
            for user in self._dig("proposal.experimenters", [])
        ]

    def __repr__(self):
        """Short summary of this beamtime request."""
        n_truncate = 40
        title = self.title
        if len(title) > n_truncate:
            title = title[:n_truncate-4] + " ..."
        return (
            "BeamtimeRequest("
              f"id:{self.proposal_id!r}"
              f", pi:{self.pi!r}"
              f", title:{title!r}"
            ")"
        )


class SchedulingServer:
    """
    Interact with the APS-U era beamline scheduling restful web server.

    .. autosummary::

        ~activeBeamlines
        ~allRuns
        ~auth_from_creds
        ~auth_from_file
        ~beamlines
        ~beamtime_requests
        ~current_proposal
        ~current_run
        ~get_activities
        ~get_request
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
    def allRuns(self):
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

    def beamtime_requests(self, beamline: str, run: str = None) -> dict:
        """
        Get all beamtime request details for 'beamline' and 'run'.

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
        if run is None:
            run = self.current_run["runName"]

        if beamline != self._beamline or run != self._run:
            # Only if not already in memeory.
            api = "beamtimeRequests/findBeamtimeRequestsByRunAndBeamline"
            api += f"/{run}/{beamline}"
            entries = self.webget(api)

            self._beamline = beamline
            self._run = run
            self._proposals = {}
            for entry in entries:
                proposal = BeamtimeRequest(entry)
                self._proposals[proposal.proposal_id] = proposal

        return self._proposals

    def current_proposal(self, beamline: str):
        """Return the current (active) proposal or 'None'."""
        for proposal in self.beamtime_requests(beamline).values():
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

        proposal = self.beamtime_requests(beamline).get(proposal_id)
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
