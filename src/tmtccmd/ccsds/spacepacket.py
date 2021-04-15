import enum
from typing import Tuple


SPACE_PACKET_HEADER_SIZE = 6


class PacketTypes(enum.IntEnum):
    PACKET_TYPE_TM = 0
    PACKET_TYPE_TC = 1


class SpacePacketCommonFields:
    def __init__(
            self, packet_type: PacketTypes, apid: int, source_sequence_count: int, data_length: int,
            version: int = 0b000, secondary_header_flag: int = 0b1, sequence_flags: int = 0b11
    ):
        self.packet_type = packet_type
        self.apid = apid
        self.ssc = source_sequence_count
        self.secondary_header_flag = secondary_header_flag
        self.sequence_flags = sequence_flags
        self.psc = get_sp_packet_sequence_control(
            sequence_flags=self.sequence_flags, source_sequence_count=self.ssc
        )
        self.version = version
        self.data_length = data_length
        self.packet_id = get_sp_packet_id_num(
            packet_type=self.packet_type, secondary_header_flag=self.secondary_header_flag,
            apid=self.apid
        )


# pylint: disable=too-many-instance-attributes
class SpacePacketHeaderDeserializer(SpacePacketCommonFields):
    """
    This class unnpacks the common spacepacket header, also see PUS structure below or
    PUS documentation.
    """
    def __init__(self, pus_packet_raw: bytes):
        """
        Deserializes space packet fields from raw bytearray
        :param pus_packet_raw:
        """
        if len(pus_packet_raw) < SPACE_PACKET_HEADER_SIZE:
            print("SpacePacketHeaderDeserializer: Packet size smaller than PUS header size!")
            super().__init__(
                packet_type=PacketTypes.PACKET_TYPE_TM, secondary_header_flag=0, sequence_flags=0,
                source_sequence_count=0, data_length=0, version=0, apid=0
            )
            return
        packet_type_raw = pus_packet_raw[0] & 0x10
        if packet_type_raw == 0:
            packet_type = PacketTypes.PACKET_TYPE_TM
        else:
            packet_type = PacketTypes.PACKET_TYPE_TC
        super().__init__(
            version=pus_packet_raw[0] >> 5,
            packet_type=packet_type,
            secondary_header_flag=(pus_packet_raw[0] & 0x8) >> 3,
            apid=((pus_packet_raw[0] & 0x7) << 8) | pus_packet_raw[1],
            sequence_flags=(pus_packet_raw[2] & 0xC0) >> 6,
            source_sequence_count=((pus_packet_raw[2] & 0x3F) << 8) | pus_packet_raw[3],
            data_length=pus_packet_raw[4] << 8 | pus_packet_raw[5]
        )

    def append_space_packet_header_content(self, content_list: list):
        content_list.append(str(hex(self.apid)))
        content_list.append(str(self.ssc))

    @staticmethod
    def append_space_packet_header_column_headers(header_list: list):
        header_list.append("APID")
        header_list.append("SSC")


class SpacePacketHeaderSerializer(SpacePacketCommonFields):
    def __init__(
            self, apid: int, packet_type: PacketTypes, data_length: int, source_sequence_count: int,
            secondary_header_flag: int = 0b1, version: int = 0b000, sequence_flags: int = 0b11
    ):
        """
        Serialize raw space packet header
        :param packet_type:             0 for telemetry, 1 for telecommands
        :param data_length:             Length of packet data field
        :param source_sequence_count:
        :param secondary_header_flag:
        :param version:                 Shall be b000 for CCSDS Version 1 packets
        :param sequence_flags:          0b11 for stand-alone packets
        :param apid:
        """
        self.packet_id_bytes = [0x00, 0x00]
        self.packet_id_bytes[0], self.packet_id_bytes[1] = get_sp_packet_id_bytes(
            version=version, packet_type=packet_type, secondary_header_flag=secondary_header_flag, apid=apid
        )
        super().__init__(
            packet_type=packet_type,
            source_sequence_count=source_sequence_count,
            data_length=data_length,
            secondary_header_flag=secondary_header_flag,
            sequence_flags=sequence_flags,
            version=version,
            apid=apid
        )
        self.header = get_sp_space_packet_header(
            packet_id_byte_one=self.packet_id_bytes[0], packet_id_byte_two=self.packet_id_bytes[1],
            data_length=data_length, packet_sequence_control=self.psc
        )

    def pack(self) -> bytearray:
        return self.header


def get_sp_packet_id_bytes(
        version: int, packet_type: PacketTypes, secondary_header_flag: int, apid: int
) -> Tuple[int, int]:
    """
    This function also includes the first three bits reserved for the version
    :param version:
    :param packet_type:
    :param secondary_header_flag:
    :param apid:
    :return:
    """
    byte_one = \
        ((version << 5) & 0xE0) | ((packet_type & 0x01) << 4) | \
        ((secondary_header_flag & 0x01) << 3) | ((apid & 0x700) >> 8)
    byte_two = apid & 0xFF
    return byte_one, byte_two


def get_sp_packet_id_num(packet_type: PacketTypes, secondary_header_flag: int, apid: int) -> int:
    return packet_type << 12 | secondary_header_flag << 11 | apid


def get_sp_packet_sequence_control(sequence_flags: int, source_sequence_count: int) -> int:
    if sequence_flags > 3:
        print("get_sp_packet_sequence_control: Sequence flag value larger than 0b11! "
              "Setting to 0b11..")
        sequence_flags = 3
    if source_sequence_count > 0x3fff:
        print("get_sp_packet_sequence_control: Source sequence count largen than 0x3fff. "
              "Larger bits are cut off!")
    return (source_sequence_count & 0x3FFF) | (sequence_flags << 14)


def get_sp_space_packet_header(
        packet_id_byte_one: int, packet_id_byte_two: int, packet_sequence_control: int,
        data_length: int
) -> bytearray:
    header = bytearray()
    header.append(packet_id_byte_one)
    header.append(packet_id_byte_two)
    header.append((packet_sequence_control & 0xFF00) >> 8)
    header.append(packet_sequence_control & 0xFF)
    header.append((data_length & 0xFF00) >> 8)
    header.append(data_length & 0xFF)
    return header
