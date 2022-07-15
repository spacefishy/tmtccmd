import os
import tempfile
from pathlib import Path
from unittest import TestCase

from spacepackets.cfdp import ChecksumTypes, PduConfig, TransmissionModes
from spacepackets.cfdp.pdu import MetadataPdu, MetadataParams
from spacepackets.util import ByteFieldU16, ByteFieldU8
from tmtccmd.cfdp import LocalIndicationCfg, LocalEntityCfg
from tmtccmd.cfdp.defs import CfdpStates
from tmtccmd.cfdp.handler.dest import DestHandler, TransactionStep

from .cfdp_fault_handler_mock import FaultHandler
from .cfdp_user_mock import CfdpUser


class TestCfdpDestHandler(TestCase):
    def setUp(self) -> None:
        self.indication_cfg = LocalIndicationCfg(True, True, True, True, True, True)
        self.fault_handler = FaultHandler()
        self.entity_id = ByteFieldU16(2)
        self.local_cfg = LocalEntityCfg(
            self.entity_id, self.indication_cfg, self.fault_handler
        )
        self.src_pdu_conf = PduConfig(
            source_entity_id=ByteFieldU16(1),
            dest_entity_id=self.entity_id,
            transaction_seq_num=ByteFieldU8(1),
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
        )
        self.cfdp_user = CfdpUser()
        self.file_path = Path(f"{tempfile.gettempdir()}/hello_dest.txt")
        with open(self.file_path, "w"):
            pass
        self.dest_handler = DestHandler(self.local_cfg, self.cfdp_user)

    def test_empty_file_reception(self):
        metadata_params = MetadataParams(
            checksum_type=ChecksumTypes.NULL_CHECKSUM,
            closure_requested=False,
            source_file_name=f"{tempfile.gettempdir()}/hello.txt",
            dest_file_name=self.file_path.as_posix(),
            file_size=0,
        )

        file_transfer_init = MetadataPdu(
            params=metadata_params, pdu_conf=self.src_pdu_conf
        )
        self.assertEqual(self.dest_handler.states.state, CfdpStates.IDLE)
        self.assertEqual(self.dest_handler.states.transaction, TransactionStep.IDLE)
        self.dest_handler.pass_packet(file_transfer_init)
        fsm_res = self.dest_handler.state_machine()
        self.assertFalse(fsm_res.states.packet_ready)
        pass

    def tearDown(self) -> None:
        if self.file_path.exists():
            os.remove(self.file_path)
