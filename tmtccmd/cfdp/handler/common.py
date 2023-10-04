import enum
from spacepackets.cfdp import GenericPduPacket, PduType, DirectiveType
from spacepackets.cfdp.pdu import PduHolder


class PacketDestination(enum.Enum):
    SOURCE_HANDLER = 0
    DEST_HANDLER = 1


def get_packet_destination(packet: GenericPduPacket) -> PacketDestination:
    """This function routes the packets based on PDU type and directive type if applicable.

    The routing is based on section 4.5 of the CFDP standard which specifies the PDU forwarding
    procedure."""
    if packet.pdu_type == PduType.FILE_DATA:
        return PacketDestination.DEST_HANDLER
    if packet.directive_type in [  # type: ignore
        DirectiveType.METADATA_PDU,
        DirectiveType.EOF_PDU,
        DirectiveType.PROMPT_PDU,
    ]:
        # Section b) of 4.5.3: These PDUs should always be targeted towards the file
        # receiver a.k.a. the destination handler
        return PacketDestination.DEST_HANDLER
    elif packet.directive_type in [  # type: ignore
        DirectiveType.FINISHED_PDU,
        DirectiveType.NAK_PDU,
        DirectiveType.KEEP_ALIVE_PDU,
    ]:
        # Section c) of 4.5.3: These PDUs should always be targeted towards the file sender
        # a.k.a. the source handler
        return PacketDestination.SOURCE_HANDLER
    elif packet.directive_type == DirectiveType.ACK_PDU:  # type: ignore
        # Section a): Recipient depends on the type of PDU that is being acknowledged.
        # We can simply extract the PDU type from the raw stream. If it is an EOF PDU,
        # this packet is passed to the source handler. For a finished PDU, it is
        # passed to the destination handler
        pdu_holder = PduHolder(packet)
        ack_pdu = pdu_holder.to_ack_pdu()
        if ack_pdu.directive_code_of_acked_pdu == DirectiveType.EOF_PDU:
            return PacketDestination.SOURCE_HANDLER
        elif ack_pdu.directive_code_of_acked_pdu == DirectiveType.FINISHED_PDU:
            return PacketDestination.DEST_HANDLER
    raise ValueError(f"unexpected directive type {packet.directive_type}")  # type: ignore
