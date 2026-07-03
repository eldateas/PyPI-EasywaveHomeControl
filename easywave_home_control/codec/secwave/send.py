"""Parse Secwave send ICP responses."""

from __future__ import annotations

from .models import SecSendCmdTelResponse
from .states import parse_reply_state


def parse_sec_send_response(
    primary_state: int,
    secondary_state: int,
    *,
    queried_reply: bool = True,
) -> SecSendCmdTelResponse:
    """Parse SEC_SEND_CMD_TEL / SEC_SEND_LRN_TEL ICP (Spec offset 3-6).

    State words are only valid when the IRP query field (offset 3) requested a reply.
    """
    if not queried_reply:
        return SecSendCmdTelResponse(reply=None)
    if primary_state == 0 and secondary_state == 0:
        return SecSendCmdTelResponse(reply=None)
    return SecSendCmdTelResponse(reply=parse_reply_state(primary_state, secondary_state))
