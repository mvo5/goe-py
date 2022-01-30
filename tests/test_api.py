#!/usr/bin/python3

import json
import os
import os.path
import time
import unittest

import responses

import goeapi


MOCK_JSON_RESPONSE = open(
    os.path.join(os.path.dirname(__file__), "api_data.json")
).read()


class ApiHappyTests(unittest.TestCase):
    def setUp(self):
        responses.add(
            responses.GET,
            "http://example.com/api/status",
            json=json.loads(MOCK_JSON_RESPONSE),
            status=200,
        )
        self.api = goeapi.GoeAPI("example.com")

    @responses.activate
    def test_read(self):
        self.assertEqual(self.api.serial, "012345")
        self.assertEqual(self.api.phases, 1)
        self.assertEqual(self.api.allow_charge, True)
        self.assertEqual(self.api.name, "go-e-123")
        self.assertEqual(self.api.ampere, 6)
        self.assertEqual(self.api.power, 0)
        self.assertEqual(self.api.force_pause, False)

    @responses.activate
    def test_write_amp(self):
        responses.add(
            responses.GET,
            "http://example.com/api/set?amp=10",
            json=json.loads('{"amp":true}'),
            status=200,
        )
        self.api.ampere = 10
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url, "http://example.com/api/set?amp=10"
        )

    @responses.activate
    def test_write_force_pause_true(self):
        responses.add(
            responses.GET,
            "http://example.com/api/set?frc=1",
            json=json.loads('{"frc":true}'),
            status=200,
        )
        self.api.force_pause = True
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url, "http://example.com/api/set?frc=1"
        )

    @responses.activate
    def test_write_force_pause_false(self):
        responses.add(
            responses.GET,
            "http://example.com/api/set?frc=0",
            json=json.loads('{"frc":true}'),
            status=200,
        )
        self.api.force_pause = False
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url, "http://example.com/api/set?frc=0"
        )

    @responses.activate
    def test_api_cache_timeout(self):
        self.api.API_CACHE_MAX_AGE = 0.1
        # get serial
        self.assertEqual(self.api.serial, "012345")
        self.assertEqual(len(responses.calls), 1)
        # get it again: this time it comes from the cache
        self.assertEqual(self.api.serial, "012345")
        self.assertEqual(len(responses.calls), 1)
        # wait for longer than the api.API_CACHE_MAX_AGE
        time.sleep(0.3)
        self.assertEqual(self.api.serial, "012345")
        # and it is fetched again
        self.assertEqual(len(responses.calls), 2)
