import pytest
import requests

from ansible_collections.serverscom.sc_api.plugins.module_utils import sc_api


class FakeResponse:
    def __init__(self, status_code, headers, json_data=None, links=None, url="http://api"):
        self.status_code = status_code
        self._json_data = json_data
        self.links = links or {}
        self.url = url
        self.content = b"error"
        self.headers = headers

    def json(self):
        return self._json_data


class SendSequencer:
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.calls = 0

    def __call__(self, _prep_request):
        self.calls += 1
        item = self.sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(sc_api.time, "time", clock.time)
    monkeypatch.setattr(sc_api.time, "sleep", clock.sleep)
    monkeypatch.setattr(sc_api.random, "uniform", lambda _a, _b: 1.0)
    return clock


@pytest.fixture
def api_helper():
    return sc_api.ApiHelper(token="token", endpoint="http://api")


def test_make_get_request_normal(api_helper, clock):
    sequencer = SendSequencer([FakeResponse(200, {}, json_data={"ok": True})])
    api_helper.session.send = sequencer

    result = api_helper.make_get_request("/path")

    assert result == {"ok": True}
    assert sequencer.calls == 1
    assert clock.now == 0.0


def test_make_get_request_retries_then_ok(api_helper, clock):
    sequencer = SendSequencer(
        [
            FakeResponse(426, {}),
            FakeResponse(426, {}),
            FakeResponse(200, {}, json_data={"ok": True}),
        ]
    )
    api_helper.session.send = sequencer
    retry_rules = {"codes": {426}, "delay": 1, "max_wait": 10}

    result = api_helper.make_get_request("/path", retry_rules=retry_rules)

    assert result == {"ok": True}
    assert sequencer.calls == 3
    assert clock.now == 2.0


def test_make_get_request_retry_timeout(api_helper, clock):
    def always_426(_prep_request):
        always_426.calls += 1
        return FakeResponse(426, {})

    always_426.calls = 0
    api_helper.session.send = always_426
    retry_rules = {"codes": {426}, "delay": 1, "max_wait": 2}

    with pytest.raises(sc_api.APIError):
        api_helper.make_get_request("/path", retry_rules=retry_rules)

    assert always_426.calls == 3
    assert clock.now == 2.0


def test_make_get_request_retries_connection_error(api_helper, clock):
    sequencer = SendSequencer(
        [
            requests.exceptions.ConnectionError("boom"),
            FakeResponse(200, {}, json_data={"ok": True}),
        ]
    )
    api_helper.session.send = sequencer
    retry_rules = {"codes": {426}, "delay": 1, "max_wait": 5}

    result = api_helper.make_get_request("/path", retry_rules=retry_rules)

    assert result == {"ok": True}
    assert sequencer.calls == 2
    assert clock.now == 1.0


def test_make_get_request_404_no_retry(api_helper, clock):
    sequencer = SendSequencer(
        [FakeResponse(404, {}), FakeResponse(200, {}, json_data={"ok": True})]
    )
    api_helper.session.send = sequencer
    retry_rules = {"codes": {426}, "delay": 1, "max_wait": 10}

    with pytest.raises(sc_api.APIError404):
        api_helper.make_get_request("/path", retry_rules=retry_rules)

    assert sequencer.calls == 1
    assert clock.now == 0.0


def test_make_multipage_request_retries_then_ok(api_helper, clock):
    page1 = FakeResponse(200, {}, json_data=[1], links={"next": {"url": "http://api/next"}})
    page2 = FakeResponse(200, {}, json_data=[2], links={"next": {"url": None}})
    sequencer = SendSequencer([FakeResponse(426, {}), page1, page2])
    api_helper.session.send = sequencer
    retry_rules = {"codes": {426}, "delay": 1, "max_wait": 10}

    result = list(api_helper.make_multipage_request("/path", retry_rules=retry_rules))

    assert result == [1, 2]
    assert sequencer.calls == 3
    assert clock.now == 1.0


def test_error_includes_correlation_id(api_helper, clock):
    headers = {"X-Correlation-ID": "abc-123"}
    sequencer = SendSequencer([FakeResponse(404, headers)])
    api_helper.session.send = sequencer

    with pytest.raises(sc_api.APIError404) as exc_info:
        api_helper.make_get_request("/path")

    assert exc_info.value.correlation_id == "abc-123"
    assert "abc-123" in exc_info.value.msg
    fail_dict = exc_info.value.fail()
    assert fail_dict["correlation_id"] == "abc-123"


def test_error_without_correlation_id(api_helper, clock):
    sequencer = SendSequencer([FakeResponse(404, {})])
    api_helper.session.send = sequencer

    with pytest.raises(sc_api.APIError404) as exc_info:
        api_helper.make_get_request("/path")

    assert exc_info.value.correlation_id is None
    assert "X-Correlation-ID" not in exc_info.value.msg
    fail_dict = exc_info.value.fail()
    assert "correlation_id" not in fail_dict


def test_decode_error_includes_correlation_id(api_helper, clock):
    headers = {"X-Correlation-ID": "decode-456"}

    class BadJsonResponse(FakeResponse):
        def json(self):
            raise ValueError("bad json")

    sequencer = SendSequencer([BadJsonResponse(200, headers)])
    api_helper.session.send = sequencer

    with pytest.raises(sc_api.DecodeError) as exc_info:
        api_helper.make_get_request("/path")

    assert exc_info.value.correlation_id == "decode-456"
    assert "decode-456" in exc_info.value.msg


def test_correlation_id_all_error_codes(api_helper, clock):
    headers = {"X-Correlation-ID": "test-corr"}
    error_map = {
        400: sc_api.APIError400,
        401: sc_api.APIError401,
        404: sc_api.APIError404,
        409: sc_api.APIError409,
        500: sc_api.APIError,
    }
    for code, exc_class in error_map.items():
        sequencer = SendSequencer([FakeResponse(code, headers)])
        api_helper.session.send = sequencer
        with pytest.raises(exc_class) as exc_info:
            api_helper.make_get_request("/path")
        assert exc_info.value.correlation_id == "test-corr", (
            f"Failed for status code {code}"
        )
