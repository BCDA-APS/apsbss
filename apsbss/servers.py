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

from .bss_dm import DM_ScheduleInterface
from .bss_is import IS_ScheduleSystem
from .core import DM_APS_DB_WEB_SERVICE_URL
from .core import iso2dt

logger = logging.getLogger(__name__)


class ServerException(RuntimeError): ...


class EsafNotFound(ServerException): ...


class ProposalNotFound(ServerException): ...


class RunNotFound(ServerException): ...


class Server:
    """
    Common connection to information servers.

    .. autosummary::
        ~beamlines
        ~current_esafs
        ~current_esafs_and_proposals
        ~current_proposals
        ~current_run
        ~esafs
        ~get_proposal
        ~proposals
        ~recent_runs
        ~_runs
        ~runs
    """

    def __init__(self, creds_file=None):
        self.esaf_api = dm.EsafApsDbApi(DM_APS_DB_WEB_SERVICE_URL)
        try:
            self.bss_api = IS_ScheduleSystem()
            self.bss_api.auth_from_file(creds_file)
        except Exception as reason:
            logger.info("Did not connect to IS server: %s", reason)
            self.bss_api = DM_ScheduleInterface()

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
            Number of APS runs (cycles) to include, optional (default: 3, a one year
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
        esafs = {e["esafId"]: e for e in esafs}
        proposals = {p.proposal_id: p for p in proposals}

        # match people by badge number
        esaf_badges = {k: sorted([u["badge"] for u in e["experimentUsers"]]) for k, e in esafs.items()}
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
        """Return the name of the current APS run (cycle)."""
        return self.bss_api.current_run["name"]

    def esafs(self, sector, run):
        """
        Return list of ESAFs for the given sector & run.

        PARAMETERS

        sector : str | int
            Name of sector.  If ``str``, must be in ``%02d`` format (``02``, not
            ``2``).
        run : str
            List of APS run (cycle).
        """
        if isinstance(sector, int):
            sector = f"{sector:02d}"
        if len(sector) == 1:
            sector = "0" + sector

        run_info = self._runs.get(run)
        if run_info is None:
            raise RunNotFound(f"Could not find {run=!r}")

        year = int(run.split("-")[0])

        results = []

        esafs = self.esaf_api.listEsafs(sector=sector, year=year)
        for esaf in esafs:
            esaf_starts = iso2dt(esaf["experimentStartDate"])
            if run_info["startTime"] <= esaf_starts <= run_info["endTime"]:
                results.append(esaf)

        return results

    def get_esaf(self, esaf_id):
        """
        Return ESAF as a dictionary.

        PARAMETERS

        esaf_id : int
            ESAF number
        """
        esaf_id = str(esaf_id)
        try:
            record = self.esaf_api.getEsaf(int(esaf_id))
        except dm.ObjectNotFound:
            raise EsafNotFound(f"{esaf_id=!r}")
        return dict(record.data)

    def get_proposal(self, proposal_id, beamline, run):
        """
        Return proposal as a dictionary.

        PARAMETERS

        proposalId : str
            Proposal identification number.
        run : str
            Canonical name of APS run (cycle).
        beamline : str
            Canonical name of beam line.
        """
        # The server will validate the request.
        proposal_id = str(proposal_id)
        proposal = self.proposals(beamline, run).get(proposal_id)
        if proposal is None:
            raise ProposalNotFound(f"{proposal_id=!r} {beamline=!r} {run=!r}")
        return proposal

    def proposals(self, beamline, run):
        """List of all proposals on 'beamline' in 'run'."""
        return self.bss_api.proposals(beamline, run)

    def recent_runs(self, nruns=6) -> list:
        """
        Return a list of the 'quantity' most recent 'nruns'.

        Sorted in reverse chronological order.

        PARAMETERS

        nruns : int
            Number of APS runs (cycles) to include, optional (default: 6, a two year
            period)
        """
        runs = self.runs
        return sorted(runs[: 1 + runs.index(self.current_run)], reverse=True)[:nruns]

    @property
    def _runs(self) -> dict:
        """Return dictionary of run details."""
        return {r["name"]: r for r in self.bss_api._runs}

    @property
    def runs(self) -> list:
        """Return list of known beam line names."""
        return self.bss_api.runs
