"""
Interface to the servers.

.. autosummary::
    ~Server

.. rubric:: Exceptions
.. autosummary::
    ~EsafNotFound
    ~ProposalNotFound
    ~RunNotFound
    ~ServerException
"""

import logging

import dm
import pyRestTable

from .bss_dm import DM_ScheduleInterface
from .bss_is import IS_ScheduleSystem
from .core import DM_APS_DB_WEB_SERVICE_URL
from .core import Esaf
from .core import iso2dt
from .core import trim
from .text_search import SearchEngine

logger = logging.getLogger(__name__)


class ServerException(RuntimeError):
    """Base exception for this module."""


class EsafNotFound(ServerException):
    """ESAF ID not found by server."""


class ProposalNotFound(ServerException):
    """Proposal ID not found by server."""


class RunNotFound(ServerException):
    """Run name not found by server."""


class Server:
    """
    Common connection to information servers.

    .. autosummary::
        ~_runs
        ~beamlines
        ~current_esafs
        ~current_esafs_and_proposals
        ~current_proposals
        ~current_run
        ~esaf
        ~esaf_table
        ~esafs
        ~find_run
        ~parse_runs_arg
        ~proposal
        ~proposal_table
        ~proposals
        ~recent_runs
        ~runs
        ~search
    """

    def __init__(self, creds_file=None):
        self.esaf_api = dm.EsafApsDbApi(DM_APS_DB_WEB_SERVICE_URL)
        try:
            self.bss_api = IS_ScheduleSystem()
            self.bss_api.auth_from_file(creds_file)
        except Exception as reason:
            logger.info("Did not connect to IS server: %s", reason)
            self.bss_api = DM_ScheduleInterface()

        self.search_engine = SearchEngine()

    def esaf_table(self, esafs: list) -> pyRestTable.Table:
        """
        Print the list of ESAFS as a table.

        PARAMETERS

        esafs : [Esaf]
            List of Esaf objects.
        """

        def sorter(item):
            return item.startDate

        table = pyRestTable.Table()
        table.labels = "id status run start end user(s) title".split()

        for item in sorted(esafs, key=sorter, reverse=True):
            users = trim(
                ",".join(item.lastNames),
                length=20,
            )
            table.addRow(
                (
                    item.esaf_id,
                    item.status,
                    item.run,
                    item.startDate.strftime("%Y-%m-%d"),
                    item.endDate.strftime("%Y-%m-%d"),
                    users,
                    trim(item.title, 40),
                )
            )

        return table

    def parse_runs_arg(self, runs) -> list:
        """
        Parse a 'runs' argument into a list of run names.

        Parameters

        runs : str | [str] | None
            Name(s) of APS runs.

            * If 'None', then use the current run.
            * If a list, then all strings in the list must be
              valid names of APS runs.
            * If a string, refer to the following table:

              ============  =============================
              value         meaning
              ============  =============================
              ""            Use the current run.
              "all"         Use all runs.
              "current"     Use the current run.
              "future"      Use the next run.
              "next"        Use the next run.
              "now"         Use the current run.
              "past"        Use the previous run.
              "previous"    Use the previous run.
              "prior"       Use the previous run.
              "recent"      Use the past six (6) runs.
              ``None``      Use the current run.
              ============  =============================
        """
        if runs in ("current", "now", "", None):
            runs = self.current_run
        elif runs in ("past", "previous", "prior"):
            rr = sorted(self.runs, reverse=True)
            runs = rr[1 + rr.index(self.current_run)]
        elif runs in ("future", "next"):
            rr = sorted(self.runs, reverse=True)
            p = rr.index(self.current_run)
            if p == 0:
                raise KeyError(f"No runs in the future for run={self.current_run}.")
            runs = rr[p - 1]
        elif runs == "recent":
            runs = self.recent_runs()
        elif runs == "all":
            runs = self.runs

        if not isinstance(runs, (list, set, tuple, str)):
            raise TypeError(f"Must be str or iterable, received: {runs=!r}")

        if not isinstance(runs, (list, set, tuple)):
            runs = [runs]

        return set(runs)  # ensure 'runs' is unique

    def proposal_table(self, proposals: dict) -> pyRestTable.Table:
        """
        Print the list of proposals as a table.

        PARAMETERS

        proposals : [ProposalBase]
            Dictionary of ProposalBase objects.
        """

        def sorter(prop):
            return prop.startDate

        table = pyRestTable.Table()
        table.labels = "id run start end user(s) title".split()
        for item in sorted(proposals.values(), key=sorter, reverse=True):
            users = trim(
                ",".join(item.lastNames),
                20,
            )
            table.addRow(
                (
                    item.proposal_id,
                    item.run,
                    item.startDate.strftime("%Y-%m-%d"),
                    item.endDate.strftime("%Y-%m-%d"),
                    users,
                    trim(item.title),
                )
            )

        return table

    @property
    def beamlines(self) -> list:
        """Return list of known beam line names."""
        return self.bss_api.beamlines

    def current_esafs(self, sector):
        """
        Return list of ESAFs for 'sector' for the current run.

        PARAMETERS

        sector : str | int
            Name of sector.  If ``str``, must be in ``%02d`` format (``02``, not
            ``2``).
        """
        return self.esafs(sector, self.current_run)

    def current_esafs_and_proposals(self, beamline, nruns=3) -> dict:
        """
        Proposals & ESAFs and proposals with same people for 'nruns' recent runs.

        PARAMETERS

        beamline : str
            Canonical name of beam line.
        nruns : int
            Number of APS runs to include, optional (default: 3, a one year
            period)

        RETURNS

        Dictionary of proposal and ESAF identification numbers.  Proposals IDs
        are the dictionary keys, list of ESAFs with same people as proposal are
        the dictionary values.
        """
        sector = beamline.split("-")[0]
        esafs = []
        proposals = []
        for run in self.recent_runs(nruns):
            esafs += self.esafs(sector, run)
            ppp = self.proposals(beamline, run)
            if len(ppp) > 0:
                proposals += list(ppp.values())
        esafs = {e.esaf_id: e for e in esafs}
        proposals = {p.proposal_id: p for p in proposals}

        # match people by badge number
        esaf_badges = {k: sorted([u.badge for u in e._users]) for k, e in esafs.items()}
        proposal_badges = {k: sorted([u.badge for u in p._users]) for k, p in proposals.items()}
        matches = {}
        for proposal_id, pbadge in proposal_badges.items():
            # fmt: off
            common = [
                esaf_id
                for esaf_id, ebadge in esaf_badges.items()
                if ebadge == pbadge
            ]
            # fmt: on
            if len(common) > 0:
                matches[proposal_id] = sorted(common)
        return matches

    def current_proposals(self, beamline):
        """
        Return list of proposals for 'beamline' for the current run.

        PARAMETERS

        beamline : str
            Canonical name of beam line.
        """
        return self.proposals(beamline, self.current_run)

    @property
    def current_run(self) -> str:
        """Return the name of the current APS run."""
        return str(self.bss_api.current_run)

    def esaf(self, esaf_id):
        """
        Return ESAF as a dictionary.

        PARAMETERS

        esaf_id : int
            ESAF number
        """
        try:
            record = self.esaf_api.getEsaf(esaf_id)  # refactor a la ProposalBase?
        except dm.ObjectNotFound as exc:
            raise EsafNotFound(f"{esaf_id=!r}") from exc
        return dict(record.data)

    def esafs(self, sector, run=None):
        """
        Return list of ESAFs for the given sector & run.

        PARAMETERS

        sector : str | int
            Name of sector.  If ``str``, must be in ``%02d`` format (``02``, not
            ``2``).
        run : str
            List of APS run.  Default to current run.
        """
        if isinstance(sector, int):
            sector = f"{sector:02d}"
        if len(sector) == 1:
            sector = "0" + sector

        run = run or self.current_run
        if not isinstance(run, str):
            raise TypeError(f"Not a string: {run=!r}")
        run_info = self._runs.get(run)
        if run_info is None:
            raise RunNotFound(f"Could not find {run=!r}")

        year = int(run.split("-")[0])

        results = []
        for raw in self.esaf_api.listEsafs(sector=sector, year=year):
            esaf = Esaf(raw, run)
            if run_info.startDate <= esaf.startDate <= run_info.endDate:
                results.append(esaf)

        if len(results) > 0:
            self.search_engine.index_esafs(results)
        return results

    def find_run(self, target_date):
        """Find the run that contains the target date."""
        if isinstance(target_date, str):
            target_date = iso2dt(target_date)

        run = None
        for r in self._runs.values():
            if r.startDate <= target_date <= r.endDate:
                run = str(r)
                break

        if run is None:
            raise ValueError(f"Run not found for date: {target_date}")

        return run

    def proposal(self, proposal_id, beamline, run=None):
        """
        Return proposal as a dictionary.

        PARAMETERS

        proposalId : int
            Proposal identification number.
        beamline : str
            Canonical name of beam line.
        run : str
            Canonical name of APS run.  Default: the current run.
        """
        run = run or self.current_run
        if not isinstance(run, str):
            raise TypeError(f"Not a string: {run=!r}")

        # The server will validate the request.
        proposal = self.proposals(beamline, run).get(proposal_id)
        if proposal is None:
            raise ProposalNotFound(f"{proposal_id=!r} {beamline=!r} {run=!r}")
        return proposal

    def proposals(self, beamline, run=None):
        """
        List of all proposals on 'beamline' in 'run'.

        PARAMETERS

        beamline : str
            Canonical name of beam line.
        run : str
            Canonical name of APS run.  Default: the current run.
        """
        run = run or self.current_run
        if not isinstance(run, str):
            raise TypeError(f"Not a string: {run=!r}")

        props = self.bss_api.proposals(beamline, run)
        if len(props) > 0:
            self.search_engine.index_proposals(props.values())
        return props

    def recent_runs(self, nruns=6) -> list:
        """
        Return a list of the 'quantity' most recent 'nruns'.

        Sorted in reverse chronological order.

        PARAMETERS

        nruns : int
            Number of APS run to include, optional (default: 6, a two year period)
        """
        runs = self.runs
        return sorted(runs[: 1 + runs.index(self.current_run)], reverse=True)[:nruns]

    @property
    def _runs(self) -> dict:
        """Return dictionary of run details."""
        return {str(r): r for r in self.bss_api._runs}

    @property
    def runs(self) -> list:
        """Return list of known beam line names."""
        return self.bss_api.runs

    def search(self, query):
        """
        Return a list of ESAFs & proposals that match the query.

        The ESAFs and Proposals have already been indexed for search in
        the :meth:`esafs` and :meth:`proposals` methods, respectively.

        Parameters

        query : str
            Search expression.

        Here are the keys available for queries:

        .. rubric:: Query Keys

        ==========  ======  ========  =========================
        key         stored  type      meaning
        ==========  ======  ========  =========================
        type        True    str       Either "ESAF" or "proposal"
        id          True    int       ID number of ESAF or Proposal
        pi          True    str       Full name & email of principal investigator
        run         True    str       APS run name
        title       True    str       Title of ESAF or Proposal
        full        False   str       (default key) Full text of ESAF or Proposal
        startDate   False   DATETIME  Starting date and time
        endDate     False   DATETIME  Ending date and time
        users       False   text      List of all users (including email) on ESAF or Proposal
        ==========  ======  ========  =========================

        .. rubric:: Example query strings

        Whoosh query strings [#]_ will search the **full** text of each ESAF and
        Proposal by default.  Queries may specify a key (such as 'pi').

        ==========================  ==============================
        query                       intent
        ==========================  ==============================
        "condensate"                Any ESAF or Proposal with "condensate" anywhere in the full text.
        "'WA-XPCS'"                 Any ESAF or Proposal with "WA-XPCS" anywhere.
        "cerium OR users:Smith"     Any ESAF or Proposal with "cerium" anywhere or "Smith" as a user.
        "title:School pi:Choi"      Any ESAF or Proposal with "school" in the title *and* "Choi" as a PI.
        "type:proposal AND *oxid*"  Any Proposal with a word containing "oxid" anywhere.
        ==========================  ==============================

        Each item in the list of results is a dictionary.  The keys are items in
        the Whoosh schema marked as 'stored=True'.  This dict is a subset of a
        ESAF or Proposal.

        .. tip:: The 'id' and 'type' keys in the search results,
           together with the 'beamline' and 'run', can be used to
           obtain the full ESAF or Proposal record.

        .. [#] The Whoosh query language provides for many types of searches.
            See https://whoosh.readthedocs.io/en/latest/querylang.html for more
            details.
        """
        return self.search_engine.search(query)
