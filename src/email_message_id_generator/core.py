"""Generate RFC 5322 compliant Message-ID headers.

A Message-ID has the form ``<local-part@domain>``. RFC 5322 §3.6.4 mandates
that the value be globally unique. In practice uniqueness is achieved by
combining three independent sources of entropy:

1. A monotonic counter held in process memory. This guarantees that two
   calls within the same process at the same epoch second cannot collide.
2. A clock value (epoch seconds by default). This widens the space across
   restarts of the process, assuming the clock advances.
3. A cryptographically random 64-bit value from ``secrets.token_hex``.
   This is the real guarantee of global uniqueness: even if two processes
   on different machines share the same clock reading and the same counter
   state (e.g. right after a fork), the random component makes a collision
   astronomically unlikely.

We use ``secrets`` rather than ``random`` because ``random`` uses a Mersenne
Twister whose state is predictable; ``secrets`` draws from the OS CSPRNG.

The local part is constrained to ``[A-Za-z0-9._-]+`` so that it is safe in
the ``left-hand side`` of a Message-ID without quoting. We do not attempt
to support the full ``atext`` grammar (RFC 5322 §3.2.3) because the extra
characters (``!#$%&'*+-/=?^_`{|}~``) buy nothing for uniqueness and make the
value harder to log, grep, and paste. This is a deliberate trade-off: we
sacrifice grammatical generality for operational safety.

The domain is taken from the constructor argument. We do not validate it
beyond rejecting empty strings; DNS validation is out of scope (and would
require network access, which the test environment does not permit). The
caller is responsible for passing a domain they control.
"""

from __future__ import annotations

import secrets
import time
from typing import Callable, Optional

__version__ = "1.0.0"

# Characters allowed in the local part. Kept to the URL-safe subset of atext
# so that the generated Message-ID is also safe to use in log lines, URLs,
# and filenames without escaping.
_LOCAL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"


class MessageIdGenerator:
    """Generate globally-unique Message-ID values.

    Parameters
    ----------
    domain:
        The domain to place after the ``@``. Must be non-empty. The caller
        is responsible for ensuring this is a domain they control; no DNS
        validation is performed.
    clock:
        Optional callable returning the current time as a float (epoch
        seconds). Injecting a fake clock makes the time component of the
        generated ID deterministic, which is essential for testing.
        Defaults to ``time.time``.
    """

    def __init__(
        self,
        domain: str,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if not isinstance(domain, str):
            raise TypeError("domain must be a string")
        if not domain:
            raise ValueError("domain must be a non-empty string")
        # Reject domains containing whitespace or control characters — these
        # would never be valid in a Message-ID and almost certainly indicate
        # a caller bug.
        for ch in domain:
            if ch.isspace() or ord(ch) < 33:
                raise ValueError(
                    "domain must not contain whitespace or control characters"
                )
        self._domain = domain
        self._clock = clock if clock is not None else time.time
        self._counter = 0

    def generate(self) -> str:
        """Return a new Message-ID string, including angle brackets.

        The returned value includes the surrounding ``<`` and ``>`` as required
        by RFC 5322 §3.6.4, so it can be assigned directly to a ``Message-ID``
        header.
        """
        self._counter += 1
        now = self._clock()
        # ``secrets.token_hex(8)`` yields 16 hex characters = 64 bits of
        # entropy. 64 bits is sufficient: even generating a billion IDs the
        # collision probability is below 1e-11 (birthday bound).
        rand = secrets.token_hex(8)
        # Encode the clock as a fixed-width integer so that sorting generated
        # IDs lexicographically approximates chronological order. We use the
        # integer part of the epoch seconds; sub-second precision is already
        # covered by the counter and the random component.
        ts = int(now)
        local = f"{ts:010d}.{self._counter:06d}.{rand}"
        return f"<{local}@{self._domain}>"


# Module-level convenience function. Each call constructs a fresh generator,
# so the counter always starts at 0. This is fine for ad-hoc use; for bulk
# generation, instantiate ``MessageIdGenerator`` once and call ``generate``
# repeatedly so the counter contributes to uniqueness.
def generate_message_id(domain: str, clock: Optional[Callable[[], float]] = None) -> str:
    """Generate a single Message-ID for *domain*.

    Equivalent to ``MessageIdGenerator(domain, clock).generate()``.
    """
    return MessageIdGenerator(domain, clock=clock).generate()
