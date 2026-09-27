import re
import unittest

from email_message_id_generator import MessageIdGenerator, generate_message_id


# A fake clock that returns a fixed value. Using this keeps tests fully
# deterministic -- no dependence on wall-clock time.
class _FakeClock:
    def __init__(self, value=1700000000.0):
        self._value = value

    def __call__(self):
        return self._value


# Pattern matching the output of generate(). The random part is hex, so we
# cannot assert its exact value, but we can assert its shape.
_ID_PATTERN = re.compile(
    r"^<(?P<local>[0-9]{10}\.[0-9]{6}\.[0-9a-f]{16})@(?P<domain>[^>]+)>$"
)


class TestMessageIdGenerator(unittest.TestCase):
    def test_returns_string_with_angle_brackets(self):
        gen = MessageIdGenerator("mail.example.org", clock=_FakeClock())
        mid = gen.generate()
        self.assertIsInstance(mid, str)
        self.assertTrue(mid.startswith("<"))
        self.assertTrue(mid.endswith(">"))

    def test_matches_expected_shape(self):
        gen = MessageIdGenerator("mail.example.org", clock=_FakeClock())
        mid = gen.generate()
        m = _ID_PATTERN.match(mid)
        self.assertIsNotNone(m, f"ID {mid!r} did not match expected shape")
        self.assertEqual(m.group("domain"), "mail.example.org")

    def test_domain_appears_after_at_sign(self):
        gen = MessageIdGenerator("my-domain.com", clock=_FakeClock())
        mid = gen.generate()
        self.assertIn("@my-domain.com>", mid)

    def test_counter_makes_consecutive_calls_unique(self):
        # With a fixed clock and fixed random (we cannot fix the random, but
        # the counter alone must guarantee uniqueness within the process).
        # We call generate many times and assert no duplicates. The random
        # component makes collisions essentially impossible, so if we see
        # any duplicate it would indicate the counter is broken.
        gen = MessageIdGenerator("d.test", clock=_FakeClock())
        ids = {gen.generate() for _ in range(1000)}
        self.assertEqual(len(ids), 1000)

    def test_counter_increments_within_local_part(self):
        gen = MessageIdGenerator("d.test", clock=_FakeClock())
        first = gen.generate()
        second = gen.generate()
        # Extract the counter field (the 6-digit zero-padded segment).
        c1 = _ID_PATTERN.match(first).group("local").split(".")[1]
        c2 = _ID_PATTERN.match(second).group("local").split(".")[1]
        self.assertEqual(int(c2), int(c1) + 1)

    def test_timestamp_embedded_from_clock(self):
        clock = _FakeClock(1234567890.0)
        gen = MessageIdGenerator("d.test", clock=clock)
        mid = gen.generate()
        ts = _ID_PATTERN.match(mid).group("local").split(".")[0]
        self.assertEqual(ts, "1234567890")

    def test_timestamp_uses_integer_part_of_clock(self):
        clock = _FakeClock(1234567890.99)
        gen = MessageIdGenerator("d.test", clock=clock)
        mid = gen.generate()
        ts = _ID_PATTERN.match(mid).group("local").split(".")[0]
        self.assertEqual(ts, "1234567890")

    def test_empty_domain_rejected(self):
        with self.assertRaises(ValueError):
            MessageIdGenerator("")

    def test_whitespace_in_domain_rejected(self):
        with self.assertRaises(ValueError):
            MessageIdGenerator("bad domain.com")

    def test_control_char_in_domain_rejected(self):
        with self.assertRaises(ValueError):
            MessageIdGenerator("bad\tdomain.com")

    def test_non_string_domain_rejected(self):
        with self.assertRaises(TypeError):
            MessageIdGenerator(12345)

    def test_default_clock_used_when_none(self):
        # We cannot assert the exact timestamp, but we can assert the ID is
        # well-formed and that the timestamp is a plausible epoch value
        # (greater than the year 2020).
        gen = MessageIdGenerator("d.test")
        mid = gen.generate()
        m = _ID_PATTERN.match(mid)
        self.assertIsNotNone(m)
        ts = int(m.group("local").split(".")[0])
        self.assertGreater(ts, 1577836800)  # 2020-01-01

    def test_generate_message_id_function(self):
        mid = generate_message_id("d.test", clock=_FakeClock())
        m = _ID_PATTERN.match(mid)
        self.assertIsNotNone(m)
        self.assertEqual(m.group("domain"), "d.test")

    def test_local_part_contains_only_safe_characters(self):
        gen = MessageIdGenerator("d.test", clock=_FakeClock())
        mid = gen.generate()
        local = _ID_PATTERN.match(mid).group("local")
        self.assertTrue(
            re.fullmatch(r"[A-Za-z0-9._-]+", local),
            f"local part {local!r} contains unsafe characters",
        )

    def test_two_generators_produce_different_ids(self):
        # Different generator instances have independent counters, but the
        # random component must still prevent collisions.
        g1 = MessageIdGenerator("d.test", clock=_FakeClock())
        g2 = MessageIdGenerator("d.test", clock=_FakeClock())
        ids1 = {g1.generate() for _ in range(500)}
        ids2 = {g2.generate() for _ in range(500)}
        overlap = ids1 & ids2
        self.assertEqual(overlap, set())


if __name__ == "__main__":
    unittest.main()
