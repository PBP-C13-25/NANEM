from unittest import mock

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase

from apps.core import ratelimit, throttle


class RateLimitEdgeCaseTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.request = RequestFactory().get("/")
        self.request.user = mock.Mock(is_authenticated=False)

    @mock.patch("apps.core.ratelimit.cache.incr", side_effect=ValueError)
    def test_hit_falls_back_to_set_when_key_expires_mid_increment(self, mock_incr):
        ratelimit.hit(self.request, "some_action", 60)
        key = ratelimit._key(self.request, "some_action")
        self.assertEqual(cache.get(key), 1)


class ThrottleEdgeCaseTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.request = RequestFactory().get("/")

    @mock.patch("apps.core.throttle.cache.incr", side_effect=ValueError)
    def test_register_failure_falls_back_when_key_expires_mid_increment(self, mock_incr):
        throttle.register_failure(self.request, "budi")
        key = throttle._key(self.request, "budi")
        self.assertEqual(cache.get(key), 1)