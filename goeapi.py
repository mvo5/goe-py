#!/usr/bin/python3

import json
import requests
import socket
import sys
import time


from typing import Any, Dict


class GoeError(Exception):
    pass


class GoeStatusError(Exception):
    pass


class GoeValueError(ValueError):
    pass


class GoeSetError(Exception):
    pass


class GoeAPI:
    """go-e v2 API"""

    # how long API replies are cached (60s)
    API_CACHE_MAX_AGE = 60.0

    def __init__(self, addr: str):
        # basic validation
        try:
            socket.getaddrinfo(addr, 80)
        except socket.gaierror as e:
            raise GoeError("cannot use address {}".format(e))
        self._get_url = "http://{}/api/status".format(addr)
        self._set_url = "http://{}/api/set".format(addr)
        # the status cache
        self._cache: Dict[str, Any] = {}
        self._cache_time = sys.float_info.min

    def _set(self, key: str, value: Any):
        # XXX: or invalidate the entire cache?
        self._cache.pop(key, None)
        kv = {key: json.dumps(value)}
        req = requests.get(self._set_url, params=kv)
        if req.status_code != 200 and req.status_code != 201:
            raise GoeSetError("cannot set {}".format(kv))
        ret_val = req.json().get(key)
        if not ret_val:
            raise GoeSetError("unexpected reply from set: '{}'".format(req.text))

    def _get(self, key: str, dfl=None) -> Any:
        cache_age = time.monotonic() - self._cache_time
        if len(self._cache) == 0 or cache_age > self.API_CACHE_MAX_AGE:
            rsp = requests.get(self._get_url)
            self._cache = rsp.json()
            self._cache_time = time.monotonic()
        elif key not in self._cache:
            params = {"filter": key}
            rsp = requests.get(self._get_url, params=params)
            self._cache[key] = rsp.json().get(key, dfl)
        return self._cache.get(key, dfl)

    @property
    def serial(self) -> str:
        """Return the serial of the Go-e"""
        return self._get("sse", "unknown")

    @property
    def phases(self) -> int:
        """Return the number of configured phases (1 or 3)"""
        ph = self._get("psm")
        # 1 = 1 Phase, 2 = 3 Phase
        if ph == 1:
            return 1
        elif ph == 2:
            return 3
        raise GoeStatusError("got unexpected number of phases 'psm' key {}".format(ph))

    @phases.setter
    def phases(self, n: int):
        if n == 1:
            pass
        elif n == 3:
            n = 2
        else:
            raise GoeStatusError("phases only supports 1 or 3 not {}".format(n))
        self._set("psm", n)

    @property
    def allow_charge(self) -> bool:
        """Return can the car charge"""
        return self._get("alw")

    @allow_charge.setter
    def allow_charge(self, allow: bool):
        if allow not in [True, False]:
            raise GoeValueError(
                "allow_charge can only take a boolean parameter, "
                "not {}".format(allow)
            )
        self._set("alw", allow)

    @property
    def name(self) -> str:
        return self._get("fna", "unset")

    @name.setter
    def name(self, new_name: str):
        self._set("fna", new_name)

    @property
    def ampere(self) -> int:
        return self._get("amp")

    @ampere.setter
    def ampere(self, val: int):
        supported = [6, 10, 12, 14, 16]
        if val not in supported:
            raise GoeSetError(
                "unsupported value {} for ampere value, try {}".format(val, supported)
            )
        self._set("amp", val)

    @property
    def force_pause(self) -> bool:
        # frc: 0=neutral; 1=off; 2=on
        return self._get("frc")

    @force_pause.setter
    def force_pause(self, off: bool):
        # frc: 0=neutral; 1=off; 2=on
        if off:
            self._set("frc", 1)
        else:
            self._set("frc", 0)

    @property
    def power(self) -> float:
        # XXX: make this nicer?
        # power cannot be cached
        self._cache.pop("nrg")
        energy_array = self._get("nrg")
        return float(energy_array[11])

    @property
    def car_connected(self) -> bool:
        self._cache.pop("car")
        car_status = self._get("car")
        # status_unknown = 0
        status_idle = 1
        status_charging = 2
        # status_wait_car = 3
        status_complete = 4
        # status_error = 5
        return car_status in {status_idle, status_charging, status_complete}
