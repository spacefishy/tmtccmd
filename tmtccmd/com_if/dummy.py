"""Dummy Communication Interface. Currently serves to provide an example without external hardware
"""
from typing import Optional

from spacepackets.ecss.pus_1_verification import RequestId
from spacepackets.ecss.tc import PusTelecommand

from tmtccmd.com_if import ComInterface
from tmtccmd.tm import TelemetryListT
from tmtccmd.tm.pus_1_verification import Service1TmExtended
from tmtccmd.tm.pus_17_test import Subservices, Service17TmExtended
from tmtccmd.logging import get_console_logger


LOGGER = get_console_logger()


class DummyComIF(ComInterface):

    def __init__(self, com_if_id: str):
        super().__init__(com_if_id=com_if_id)
        self.dummy_handler = DummyHandler()
        self.last_service = 0
        self.last_subservice = 0
        self.tc_ssc = 0
        self.tc_packet_id = 0

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        pass

    def is_open(self) -> bool:
        return True

    def close(self, args: any = None) -> None:
        pass

    def data_available(self, timeout: float = 0, parameters: any = 0):
        if self.dummy_handler.reply_pending:
            return True
        return False

    def receive(self, parameters: any = 0) -> TelemetryListT:
        return self.dummy_handler.receive_reply_package()

    def send(self, data: bytearray):
        if data is not None:
            self.dummy_handler.pass_telecommand(data)


class DummyHandler:
    def __init__(self):
        self.last_tc: Optional[PusTelecommand] = None
        self.next_telemetry_package = []
        self.current_ssc = 0
        self.reply_pending = False

    def pass_telecommand(self, data: bytearray):
        self.last_tc = PusTelecommand.unpack(data)
        self.reply_pending = True
        self.generate_reply_package()

    def generate_reply_package(self):
        """
        Generate the replies. This function will perform the following steps:
         - Generate an object representation of the telemetry to be generated based on service and subservice
         - Generate the raw bytearray of the telemetry
         - Generate the object representation which would otherwise be generated from the raw bytearray received
           from an external source
        """
        if self.last_tc.service == 17:
            if self.last_tc.subservice == 1:
                tm_packer = Service1TmExtended(
                    subservice=1,
                    ssc=self.current_ssc,
                    tc_request_id=RequestId(
                        self.last_tc.packet_id, self.last_tc.packet_seq_ctrl
                    ),
                )

                self.current_ssc += 1
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                tm_packer = Service1TmExtended(
                    subservice=7,
                    ssc=self.current_ssc,
                    tc_request_id=RequestId(
                        self.last_tc.packet_id, self.last_tc.packet_seq_ctrl
                    ),
                )
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

                tm_packer = Service17TmExtended(subservice=Subservices.TM_REPLY)
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

    def receive_reply_package(self) -> TelemetryListT:
        if self.reply_pending:
            return_list = self.next_telemetry_package.copy()
            self.next_telemetry_package.clear()
            self.reply_pending = False
            return return_list
        else:
            return []
