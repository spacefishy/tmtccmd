from abc import abstractmethod
from typing import Optional
from unittest.mock import MagicMock
import argparse

from tmtccmd.com_if import ComInterface
from tmtccmd.config import CoreModeList
from tmtccmd.config.tmtc import TmTcDefWrapper
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.config import TmTcCfgHookBase
from tmtccmd.logging import get_console_logger
from tmtccmd.utility.obj_id import ObjectIdDictT

LOGGER = get_console_logger()


def create_hook_mock() -> TmTcCfgHookBase:
    """Create simple minimal hook mock using the MagicMock facilities by unittest
    :return:
    """
    tmtc_hook_base = TmTcCfgHookBase()
    tmtc_hook_base.add_globals_pre_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.add_globals_post_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.custom_args_parsing = MagicMock(
        return_value=argparse.Namespace(service=17, mode=CoreModeList.IDLE)
    )
    return tmtc_hook_base


def create_hook_mock_with_srv_handlers() -> TmTcCfgHookBase:
    tmtc_hook_base = create_hook_mock()
    tmtc_hook_base.handle_service_8_telemetry = MagicMock(return_value=(["Test"], [0]))
    # Valid returnvalue for now
    srv_3_return_tuple = (["Test"], [0], bytearray(0b10000000), 1)
    tmtc_hook_base.handle_service_3_housekeeping = MagicMock(
        return_value=srv_3_return_tuple
    )
    return tmtc_hook_base


class TestHookObj(TmTcCfgHookBase):
    service_8_handler_called = False
    service_5_handler_called = False
    service_3_handler_called = False

    def __init__(self):
        super().__init__()
        self.get_obj_id_called = False
        self.add_globals_pre_args_parsing_called = False
        self.add_globals_post_args_parsing_called = False
        self.assign_communication_interface_called = False

    @abstractmethod
    def get_object_ids(self) -> ObjectIdDictT:
        """The user can specify an object ID dictionary here mapping object ID bytearrays to a
        list. This list could contain containing the string representation or additional
        information about that object ID.
        """
        return super().get_object_ids()

    @abstractmethod
    def assign_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
        """Assign the communication interface used by the TMTC commander to send and receive
        TMTC with.

        :param com_if_key:      String key of the communication interface to be created.
        """
        from tmtccmd.config.com_if import create_communication_interface_default

        return create_communication_interface_default(
            com_if_key=com_if_key, json_cfg_path=self.json_cfg_path
        )

    @abstractmethod
    def get_tmtc_definitions(self) -> TmTcDefWrapper:
        """This is a dicitonary mapping services represented by strings to an operation code
        dictionary.

        :return:
        """
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    @abstractmethod
    def perform_mode_operation(self, tmtc_backend: CcsdsTmtcBackend, mode: int):
        """Perform custom mode operations
        :param tmtc_backend:
        :param mode:
        :return:
        """
        pass
