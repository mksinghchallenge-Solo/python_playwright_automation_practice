"""Framework self-tests: logging + secret masking."""

import logging

import allure
import pytest

from utils.logging.logger import ROOT_LOGGER_NAME, get_log_context, get_logger, set_log_context
from utils.logging.masking import is_sensitive_key, mask_data, mask_headers, mask_text, mask_url

pytestmark = [pytest.mark.framework, pytest.mark.read_only]


@allure.feature("Framework")
@allure.story("Secret masking")
class TestMasking:
    @pytest.mark.parametrize(
        "text",
        [
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "password=SuperSecret123",
            'token: "abc.def.ghi"',
            'api_key="AKIA1234567890"',
            '{"password": "hunter2"}',
            '{"refresh_token": "r-1234567890"}',
            "cookie: session=abcdef123456",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcDEFghiJKLmnoPQRstuVWXyz",
        ],
    )
    def test_free_text_is_masked(self, text: str) -> None:
        masked = mask_text(text)
        assert "*****" in masked
        for secret in ("abcdefghijklmnopqrstuvwxyz", "SuperSecret123", "hunter2", "r-1234567890", "AKIA1234567890"):
            assert secret not in masked

    def test_nested_dict_masking(self) -> None:
        payload = {
            "email": "a@b.c",
            "password": "p@ss",
            "profile": {"access_token": "tok", "name": "Anna", "author": "keep-me"},
            "items": [{"client_secret": "s"}, {"ok": 1}],
        }
        masked = mask_data(payload)
        assert masked["password"] == "*****"
        assert masked["profile"]["access_token"] == "*****"
        assert masked["profile"]["name"] == "Anna"
        assert masked["profile"]["author"] == "keep-me"
        assert masked["items"][0]["client_secret"] == "*****"
        assert payload["password"] == "p@ss", "input must not be mutated"

    def test_headers_masking(self) -> None:
        headers = mask_headers({"Authorization": "Bearer x", "Cookie": "a=b", "Accept": "json", "X-API-Key": "k"})
        assert headers["Authorization"] == "*****"
        assert headers["Cookie"] == "*****"
        assert headers["X-API-Key"] == "*****"
        assert headers["Accept"] == "json"

    def test_url_query_masking(self) -> None:
        assert "secret" not in mask_url("https://x.io/a?token=secret&page=2")
        assert "page=2" in mask_url("https://x.io/a?token=secret&page=2")

    def test_sensitive_key_detection(self) -> None:
        assert is_sensitive_key("refreshToken")
        assert is_sensitive_key("X-Csrf-Token")
        assert not is_sensitive_key("author")
        assert not is_sensitive_key("token_type")

    def test_masking_can_be_disabled(self) -> None:
        assert mask_text("password=abc", enabled=False) == "password=abc"


@allure.feature("Framework")
@allure.story("Logging")
class TestLogging:
    def test_logger_hierarchy(self) -> None:
        log = get_logger("LoginPage")
        assert log.name == f"{ROOT_LOGGER_NAME}.LoginPage"

    def test_log_records_are_masked(self, caplog: pytest.LogCaptureFixture) -> None:
        log = get_logger("MaskCheck")
        log.propagate = True  # let caplog see the record
        try:
            with caplog.at_level(logging.INFO, logger=log.name):
                log.info("login with password=TopSecret99")
        finally:
            log.propagate = False
        # The root handlers mask the *rendered* record; verify via handler filters.
        root = logging.getLogger(ROOT_LOGGER_NAME)
        record = logging.LogRecord(log.name, logging.INFO, __file__, 1, "password=TopSecret99", (), None)
        for handler in root.handlers:
            for flt in handler.filters:
                flt.filter(record)
        assert "TopSecret99" not in record.getMessage()

    def test_log_context_is_injected(self) -> None:
        set_log_context(browser="firefox", device="Pixel 7")
        ctx = get_log_context()
        assert ctx["browser"] == "firefox"
        assert ctx["device"] == "Pixel 7"
