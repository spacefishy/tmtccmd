import enum
import struct

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from tmtccmd.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from tmtccmd.cfdp.tlv import CfdpTlv
from tmtccmd.cfdp.conf import LenInBytes, check_packet_length
from tmtccmd.ccsds.log import LOGGER


class TransactionStatus(enum.IntEnum):
    """For more detailed information: CCSDS 727.0-B-5 p.81"""
    UNDEFINED = 0b00
    ACTIVE = 0b01
    TERMINATED = 0b10
    UNRECOGNIZED = 0b11


class AckPdu():
    def __init__(
        self,
        serialize: bool,
        directive_code_of_acked_pdu: DirectiveCodes,
        condition_code_of_acked_pdu: ConditionCode,
        transaction_status: TransactionStatus,
        direction: Direction,
        trans_mode: TransmissionModes,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        len_entity_id: LenInBytes = LenInBytes.NONE,
        len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            serialize=serialize,
            directive_code=DirectiveCodes.ACK_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.directive_code_of_acked_pdu = directive_code_of_acked_pdu
        self.directive_subtype_code = 0
        if self.directive_code_of_acked_pdu == DirectiveCodes.FINISHED_PDU:
            self.directive_subtype_code = 0b0001
        else:
            self.directive_subtype_code = 0b0000
        self.condition_code_of_acked_pdu = condition_code_of_acked_pdu
        self.transaction_status = transaction_status

    def pack(self):
        packet = self.pdu_file_directive.pack()
        packet.append((self.directive_code_of_acked_pdu << 4) | self.directive_subtype_code)
        packet.append((self.condition_code_of_acked_pdu << 4) | self.transaction_status)

    def unpack(self, raw_packet: bytearray):
        self.pdu_file_directive.unpack(raw_packet=raw_packet)
        current_idx = self.pdu_file_directive.get_len()
        self.directive_code_of_acked_pdu = raw_packet[current_idx] & 0xf0
        self.directive_subtype_code = raw_packet[current_idx] & 0x0f
        current_idx += 1
        self.condition_code_of_acked_pdu = raw_packet[current_idx] & 0xf0
        self.transaction_status = raw_packet[current_idx] & 0x03