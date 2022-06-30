import enum
from dataclasses import dataclass, field
from typing import Dict, Optional, List

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import RequestId, Service1Tm, Subservices


class StatusField(enum.IntEnum):
    UNSET = -1
    FAILURE = 0
    SUCCESS = 1


@dataclass
class VerificationStatus:
    all_verifs_recvd: bool = False
    accepted: StatusField = StatusField.UNSET
    started: StatusField = StatusField.UNSET
    step: StatusField = StatusField.UNSET
    step_list: List[int] = field(default_factory=lambda: [])
    completed: StatusField = StatusField.UNSET


VerifDictT = Dict[RequestId, VerificationStatus]


@dataclass
class TmCheckResult:
    """Result type for a TM check.

    Special note on the completed flag: This flag indicates that
    any of the steps have failed or there was a completion success. This does not mean that
    all related verification packets have been received for the respective telecommand. If all
    packets were received, the :py:attr:`VerificationStatus.all_verifs_recvd` field will bet
    set to True
    """

    req_id_in_dict: bool
    status: Optional[VerificationStatus]
    completed: bool


class PusVerificator:
    def __init__(self):
        self._verif_dict: VerifDictT = dict()
        pass

    def add_tc(self, tc: PusTelecommand) -> bool:
        req_id = RequestId.from_sp_header(tc.sp_header)
        if req_id in self._verif_dict:
            return False
        self._verif_dict.update({req_id: VerificationStatus()})
        return True

    def add_tm(self, pus_1_tm: Service1Tm) -> TmCheckResult:
        req_id = pus_1_tm.tc_req_id
        res = TmCheckResult(False, None, False)
        if req_id not in self._verif_dict:
            return res
        res.req_id_in_dict = True
        verif_status = self._verif_dict.get(req_id)
        if pus_1_tm.subservice <= 0 or pus_1_tm.subservice > 8:
            raise ValueError(
                f"PUS 1 TM with invalid subservice {pus_1_tm.subservice} was passed"
            )
        res.status = verif_status

        return self._check_subservice(pus_1_tm, res, verif_status)

    def _check_subservice(
        self,
        pus_1_tm: Service1Tm,
        res: TmCheckResult,
        verif_status: VerificationStatus,
    ) -> TmCheckResult:
        subservice = pus_1_tm.subservice
        if subservice % 2 == 0:
            # For failures, verification handling is completed
            res.completed = True
        if subservice == Subservices.TM_ACCEPTANCE_SUCCESS:
            verif_status.accepted = StatusField.SUCCESS
        elif subservice == Subservices.TM_ACCEPTANCE_FAILURE:
            verif_status.all_verifs_recvd = True
            verif_status.accepted = StatusField.FAILURE
            res.completed = True
        elif subservice == Subservices.TM_START_SUCCESS:
            verif_status.started = StatusField.SUCCESS
        elif subservice == Subservices.TM_START_FAILURE:
            res.completed = True
            if verif_status.accepted != StatusField.UNSET:
                verif_status.all_verifs_recvd = True
            verif_status.started = StatusField.FAILURE
        elif subservice == Subservices.TM_STEP_SUCCESS:
            # Do not overwrite a failed step status
            if verif_status.step == StatusField.UNSET:
                verif_status.step = StatusField.SUCCESS
            verif_status.step_list.append(pus_1_tm.step_id.val)
        elif subservice == Subservices.TM_STEP_FAILURE:
            self._check_all_replies_recvd_after_step(verif_status)
            verif_status.step = StatusField.FAILURE
            verif_status.step_list.append(pus_1_tm.step_id.val)
            res.completed = True
        elif subservice == Subservices.TM_COMPLETION_SUCCESS:
            self._check_all_replies_recvd_after_step(verif_status)
            verif_status.completed = StatusField.SUCCESS
            res.completed = True
        elif subservice == Subservices.TM_COMPLETION_FAILURE:
            self._check_all_replies_recvd_after_step(verif_status)
            verif_status.completed = StatusField.FAILURE
            res.completed = True
        return res

    @property
    def verif_dict(self):
        return self._verif_dict

    @staticmethod
    def _check_all_replies_recvd_after_step(verif_stat: VerificationStatus):
        if (
            verif_stat.accepted != StatusField.UNSET
            and verif_stat.started != StatusField.UNSET
        ):
            verif_stat.all_verifs_recvd = True

    def remove_completed_entries(self):
        self._verif_dict = {
            key: val
            for key, val in self._verif_dict.items()
            if not val.all_verifs_recvd
        }

    def remove_entry(self, req_id: RequestId) -> bool:
        if req_id in self._verif_dict:
            del self._verif_dict[req_id]
            return True
        return False
