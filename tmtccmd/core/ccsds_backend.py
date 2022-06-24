import atexit
import sys
from typing import Optional

from tmtccmd.config.definitions import CoreServiceList, CoreModeList
from tmtccmd.core.backend import BackendBase, BackendState, Request, BackendController
from tmtccmd.core.modes import TcMode, TmMode
from tmtccmd.tc.definitions import ProcedureInfo
from tmtccmd.tc.handler import TcHandlerBase, FeedWrapper
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.logging import get_console_logger
from tmtccmd.tc.ccsds_seq_sender import (
    SequentialCcsdsSender,
    SenderMode,
)
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface

LOGGER = get_console_logger()


class CcsdsTmtcBackend(BackendBase):
    """This is the primary class which handles TMTC reception and sending"""

    def __init__(
        self,
        tc_mode: TcMode,
        tm_mode: TmMode,
        com_if: CommunicationInterface,
        tm_listener: CcsdsTmListener,
        tc_handler: TcHandlerBase,
    ):
        from tmtccmd.utility.exit_handler import keyboard_interrupt_handler

        self._state = BackendState()
        self._state.mode_wrapper.tc_mode = tc_mode
        self._state.mode_wrapper.tm_mode = tm_mode

        self.__com_if_active = False
        self.__tc_handler = tc_handler

        self.__com_if = com_if
        self.__tm_listener = tm_listener
        self._current_proc_info = ProcedureInfo(CoreServiceList.SERVICE_17.value, "0")
        self.exit_on_com_if_init_failure = True
        self._queue_wrapper = QueueWrapper(None)
        self._seq_handler = SequentialCcsdsSender(
            com_if=self.__com_if,
            tc_handler=tc_handler,
            queue_wrapper=self._queue_wrapper,
        )
        atexit.register(
            keyboard_interrupt_handler, tmtc_backend=self, com_interface=self.__com_if
        )

    @property
    def com_if_id(self):
        return self.__com_if.get_id()

    @property
    def com_if(self) -> CommunicationInterface:
        return self.__com_if

    @property
    def tc_mode(self):
        return self._state.mode_wrapper.tc_mode

    @property
    def tm_mode(self):
        return self._state.mode_wrapper.tm_mode

    @tc_mode.setter
    def tc_mode(self, tc_mode: TcMode):
        self._state.mode_wrapper._tc_mode = tc_mode

    @tm_mode.setter
    def tm_mode(self, tm_mode: TmMode):
        self._state.mode_wrapper._tm_mode = tm_mode

    @property
    def tm_listener(self):
        return self.__tm_listener

    def try_set_com_if(self, com_if: CommunicationInterface):
        if not self.com_if_active():
            self.__com_if = com_if
            self.__tm_listener.com_if(self.__com_if)
        else:
            LOGGER.warning(
                "Communication Interface is active and must be closed first before "
                "reassigning a new one"
            )

    def com_if_active(self):
        return self.__com_if_active

    @property
    def current_proc_info(self) -> ProcedureInfo:
        return self._current_proc_info

    @current_proc_info.setter
    def current_proc_info(self, proc_info: ProcedureInfo):
        self._current_proc_info = proc_info

    @staticmethod
    def start_handler(executed_handler, ctrl: BackendController):
        if not isinstance(executed_handler, CcsdsTmtcBackend):
            LOGGER.error("Unexpected argument, should be TmTcHandler!")
            sys.exit(1)
        executed_handler.start_listener(ctrl)

    def __listener_io_error_handler(self, ctx: str):
        LOGGER.error(f"Communication Interface could not be {ctx}")
        LOGGER.info("TM listener will not be started")
        if self.exit_on_com_if_init_failure:
            LOGGER.error("Closing TMTC commander..")
            self.__com_if.close()
            sys.exit(1)

    def start_listener(self, ctrl: BackendController):
        try:
            self.__com_if.open()
        except IOError:
            self.__listener_io_error_handler("opened")
        self.__com_if_active = True

    def close_listener(self):
        """Closes the TM listener and the communication interface. This is started in a separarate
        thread because the communication interface might still be busy. The completion can be
        checked with :meth:`tmtccmd.core.backend.is_com_if_active`. Alternatively, waiting on
        completion is possible by specifying the join argument and a timeout in
        floating point second.
        :return:
        """
        try:
            self.__com_if.close()
        except IOError:
            self.__listener_io_error_handler("close")
        self.__com_if_active = False

    def periodic_op(self, ctrl: BackendController) -> BackendState:
        """Periodic operation
        :raises KeyboardInterrupt: Yields info output and then propagates the exception
        :raises IOError: Yields informative output and propagates exception
        :"""
        try:
            return self.default_operation()
        except KeyboardInterrupt as e:
            LOGGER.info("Keyboard Interrupt.")
            raise e
        except IOError as e:
            LOGGER.exception("IO Error occured")
            raise e

    def default_operation(self) -> BackendState:
        """Command handling."""
        self.tm_operation()
        self.tc_operation()
        self.mode_to_req()
        return self._state

    def mode_to_req(self):
        if self.tc_mode == TcMode.IDLE and self.tm_mode == TmMode.IDLE:
            self._state.__req = Request.DELAY_IDLE
        elif self.tm_mode == TmMode.LISTENER and self.tc_mode == CoreModeList.IDLE:
            self._state.__req = Request.DELAY_LISTENER
        elif self._seq_handler.mode == SenderMode.DONE:
            if self._state.tc_mode == TcMode.ONE_QUEUE:
                self._state.mode_wrapper.tc_mode = TcMode.IDLE
                self._state._request = Request.TERMINATION_NO_ERROR
            elif self._state.tc_mode == TcMode.MULTI_QUEUE:
                self._state.mode_wrapper.tc_mode = TcMode.IDLE
                self._state._request = Request.CALL_NEXT
        else:
            if self._state.sender_res.longest_rem_delay > 0:
                self._state._recommended_delay = (
                    self._state.sender_res.longest_rem_delay
                )
                self._state._request = Request.DELAY_CUSTOM
            else:
                self._state._request = Request.CALL_NEXT

    def close_com_if(self):
        self.__com_if.close()

    def poll_tm(self):
        """Poll TM, irrespective of current TM mode"""
        self.__tm_listener.operation()

    def tm_operation(self):
        if self._state.tm_mode == TmMode.LISTENER:
            self.__tm_listener.operation()

    def tc_operation(self):
        self.__check_and_execute_seq_send()

    def __check_and_execute_seq_send(self):
        if not self._seq_handler.mode == SenderMode.DONE:
            service_queue = self.__prepare_tc_queue()
            if service_queue is None:
                return
            LOGGER.info("Loading TC queue")
            self._seq_handler.queue_wrapper = service_queue
            self._seq_handler.resume()
        self._state._sender_res = self._seq_handler.operation()

    def __prepare_tc_queue(self) -> Optional[QueueWrapper]:
        feed_wrapper = FeedWrapper()
        self.__tc_handler.feed_cb(self.current_proc_info, feed_wrapper)
        if not self.__com_if.valid or not feed_wrapper.dispatch_next_queue:
            return None
        return feed_wrapper.current_queue