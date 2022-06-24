"""Contains the TmListener which can be used to listen to Telemetry in the background"""
from typing import Dict, List, Tuple

from spacepackets.ccsds.spacepacket import get_apid_from_raw_space_packet
from tmtccmd.ccsds.handler import CcsdsTmHandler

from tmtccmd.tm.definitions import TelemetryQueueT
from tmtccmd.logging import get_console_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface

LOGGER = get_console_logger()

INVALID_APID = -2
UNKNOWN_TARGET_ID = -1
QueueDictT = Dict[int, Tuple[TelemetryQueueT, int]]
QueueListT = List[Tuple[int, TelemetryQueueT]]


class CcsdsTmListener:
    """Performs all TM listening operations.
    This listener to have a permanent means to receive data. A background thread is used
    to poll data with the provided communication interface. Dedicated sender and receiver object
    or any other software component can get the received packets from the internal deque container.
    """

    def __init__(
        self,
        com_if: CommunicationInterface,
        tm_handler: CcsdsTmHandler,
    ):
        """Initiate a TM listener.
        :param com_if: Type of communication interface,
            e.g. a serial or ethernet interface
        :param tm_handler: If valid CCSDS packets are found, they are dispatched to
            the passed handler
        """
        self.__com_if = com_if
        self.__tm_handler = tm_handler

    @property
    def com_if(self):
        return self.__com_if

    @com_if.setter
    def com_if(self, com_if: CommunicationInterface):
        self.__com_if = com_if

    def operation(self) -> int:
        packet_list = self.__com_if.receive()
        for tm_packet in packet_list:
            self.__handle_ccsds_space_packet(tm_packet)
        return len(packet_list)

    def __handle_ccsds_space_packet(self, tm_packet: bytes):
        if len(tm_packet) < 6:
            LOGGER.warning("TM packet to small to be a CCSDS space packet")
        else:
            apid = get_apid_from_raw_space_packet(tm_packet)
            self.__tm_handler.handle_packet(apid, tm_packet)
            return True
        return False