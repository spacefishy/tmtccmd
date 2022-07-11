from dataclasses import dataclass


class NoRemoteEntityCfgFound(Exception):
    pass


class SourceFileDoesNotExist(Exception):
    pass


class ChecksumNotImplemented(Exception):
    pass


class PacketSendNotConfirmed(Exception):
    pass


class BusyError(Exception):
    pass


@dataclass
class FileParams:
    offset = 0
    segment_len = 0
    crc32 = bytes()
    size = 0

    def reset(self):
        self.offset = 0
        self.segment_len = 0
        self.crc32 = bytes()
        self.size = 0
