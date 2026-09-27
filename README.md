# email-message-id-generator

Generates RFC 5322 compliant `Message-ID` header values that are globally unique.

```python
from email_message_id_generator import MessageIdGenerator, generate_message_id

# One-off use
mid = generate_message_id("mail.example.org")
# -> "<1700000000.000001.a1b2c3d4e5f6a7b8@mail.example.org>"

# Bulk use: instantiate once, call generate() repeatedly. The internal
# counter guarantees no two calls within the process collide.
gen = MessageIdGenerator("mail.example.org")
for _ in range(10):
    print(gen.generate())
```

## Why

Generating a `Message-ID` sounds trivial until you need it to be globally
unique across processes, machines, and restarts. Common approaches —
UUIDs, hashing the current time — work but produce values that are hard to
read in logs and impossible to correlate chronologically.

This library combines a monotonic in-process counter, the epoch timestamp,
and 64 bits of OS CSPRNG entropy. The counter prevents collisions within a
process at the same clock reading. The timestamp gives approximate
chronological sortability. The random component is the real uniqueness
guarantee across processes and machines.

The trade-off: the local part is restricted to `[A-Za-z0-9._-]` rather than
the full RFC 5322 `atext` set. This sacrifices grammatical generality for
values that are safe in logs, URLs, and filenames without escaping.

## Edge cases

- The domain is **not** DNS-validated. Pass a domain you control. Validation
  would require network access, which the test environment does not permit.
- The clock can be injected via the `clock` parameter (a callable returning
  epoch seconds as a float). This exists for deterministic testing; in
  production you can omit it and `time.time` is used.
- Sub-second clock precision is discarded. The integer epoch seconds are
  used; uniqueness within the same second is handled by the counter and the
  random component.

## Exports

- `MessageIdGenerator(domain, clock=None)` — class. `.generate()` returns a
  `str` including angle brackets.
- `generate_message_id(domain, clock=None)` — convenience function.
  Equivalent to `MessageIdGenerator(domain, clock).generate()`.
- `__version__` — package version string.
