import sys
from typing import Union, Tuple

from tmtccmd.core.definitions import CoreGlobalIds, CoreComInterfaces
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.com_if.serial_com_if import SerialConfigIds, SerialCommunicationType
from tmtccmd.com_if.serial_utilities import determine_com_port, determine_baud_rate
from tmtccmd.com_if.ethernet_com_if import EthernetConfigIds
from tmtccmd.com_if.ethernet_utilities import ethernet_address_t
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter


LOGGER = get_logger()


def create_communication_interface_default(
        com_if: int, tmtc_printer: TmTcPrinter
) -> Union[CommunicationInterface, None]:
    from tmtccmd.com_if.serial_com_if import SerialComIF
    from tmtccmd.com_if.dummy_com_if import DummyComIF
    from tmtccmd.com_if.ethernet_com_if import EthernetComIF
    from tmtccmd.com_if.qemu_com_if import QEMUComIF
    """
    Return the desired communication interface object
    :param tmtc_printer: TmTcPrinter object.
    :return: CommunicationInterface object
    """
    try:
        if com_if == CoreComInterfaces.EthernetUDP:
            ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
            send_addr = ethernet_cfg_dict[EthernetConfigIds.SEND_ADDRESS]
            rcv_addr = ethernet_cfg_dict[EthernetConfigIds.RECV_ADDRESS]
            communication_interface = EthernetComIF(
                tmtc_printer=tmtc_printer, tm_timeout=get_global(CoreGlobalIds.TM_TIMEOUT),
                tc_timeout_factor=get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR),
                send_address=send_addr, receive_address=rcv_addr)
        elif com_if == CoreComInterfaces.Serial:
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_baudrate = serial_cfg[SerialConfigIds.SERIAL_BAUD_RATE]
            serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
            # Determine COM port, either extract from JSON file or ask from user.
            com_port = determine_com_port()
            communication_interface = SerialComIF(
                tmtc_printer=tmtc_printer, com_port=com_port, baud_rate=serial_baudrate,
                serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING)
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(dle_max_queue_len, dle_max_frame_size,
                                                     serial_timeout)
        elif com_if == CoreComInterfaces.QEMU:
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
            communication_interface = QEMUComIF(
                tmtc_printer=tmtc_printer, serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING)
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout)
        else:
            communication_interface = DummyComIF(tmtc_printer=tmtc_printer)
        if not communication_interface.valid:
            LOGGER.warning("Invalid communication interface!")
            sys.exit()
        communication_interface.initialize()
        return communication_interface
    except (IOError, OSError) as e:
        LOGGER.error("Error setting up communication interface")
        print(e)
        sys.exit(1)


def default_tcpip_cfg_setup():
    from tmtccmd.com_if.ethernet_utilities import determine_ip_addresses
    update_global(CoreGlobalIds.USE_ETHERNET, True)
    # This will either load the addresses from a JSON file or prompt them from the user.
    send_addr, rcv_addr = determine_ip_addresses()
    setup_tcpip_cfg(send_address=send_addr, receive_address=rcv_addr)


def setup_tcpip_cfg(send_address: ethernet_address_t, receive_address: ethernet_address_t):
    ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_cfg_dict.update({EthernetConfigIds.SEND_ADDRESS: send_address})
    ethernet_cfg_dict.update({EthernetConfigIds.RECV_ADDRESS: receive_address})
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_cfg_dict)


def default_serial_cfg_setup(com_if: CoreComInterfaces):
    baud_rate = determine_baud_rate()
    if com_if == CoreComInterfaces.Serial:
        serial_port = determine_com_port()
    else:
        serial_port = ""
    set_up_serial_cfg(com_if=com_if, baud_rate=baud_rate, com_port=serial_port)


def set_up_serial_cfg(
        com_if: CoreComInterfaces, baud_rate: int, com_port: str = "",  tm_timeout: float = 0.01,
        ser_com_type: SerialCommunicationType = SerialCommunicationType.DLE_ENCODING,
        ser_frame_size: int = 256, dle_queue_len: int = 25, dle_frame_size: int = 1024
):
    """
    Default configuration to set up serial communication. The serial port and the baud rate
    will be determined from a JSON configuration file and prompted from the user
    :param com_if:
    :param com_port:
    :param baud_rate:
    :param tm_timeout:
    :param ser_com_type:
    :param ser_frame_size:
    :param dle_queue_len:
    :param dle_frame_size:
    :return:
    """
    update_global(CoreGlobalIds.USE_SERIAL, True)
    if com_if == CoreComInterfaces.Serial and com_port == "":
        LOGGER.warning("Invalid com port specified!")
        com_port = determine_com_port()
    serial_cfg_dict = get_global(CoreGlobalIds.SERIAL_CONFIG)
    serial_cfg_dict.update({SerialConfigIds.SERIAL_PORT: com_port})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_BAUD_RATE: baud_rate})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_TIMEOUT: tm_timeout})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_COMM_TYPE: ser_com_type})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_FRAME_SIZE: ser_frame_size})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_QUEUE_LEN: dle_queue_len})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE: dle_frame_size})
    update_global(CoreGlobalIds.SERIAL_CONFIG, serial_cfg_dict)
