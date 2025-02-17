from pathlib import Path
import unittest
import pytest

from datetime import timedelta
from unittest.mock import Mock
from requests_cache import CachedSession

from saim.culture_link.private.cached_session import BrowserPWAdapter
from saim.culture_link.private.constants import VerificationStatus
from saim.culture_link.private.container import (
    CachedPageResp,
    LinkResult,
    LinkStatus,
    SearchTask,
    TaskPackage,
    VerifiedURL,
)
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.culture_link.private.robots_txt import RobotsTxt
from saim.culture_link.private.verify_ccno import (
    _find_elements_in_content,
    _is_ccno_in_text,
    _is_string_in_text,
    _prepare_result_raw,
    _wrap_status,
    verify_ccno_in_url,
)
from saim.shared.misc.ctx import get_worker_ctx
from saim.shared.data_con.designation import CCNoDes
from saim.shared.error.exceptions import KnownException
from saim.shared.parse.http_url import get_domain
from saim.shared.error.warnings import ValidationWarn

from cafi.container.links import LinkLevel


pytest_plugins = ("tests.fixture.links",)


def test_wrap_status() -> None:
    assert _wrap_status(200, False, True, False) == VerificationStatus.prohibited
    assert _wrap_status(200, True, False, False) == VerificationStatus.timeout
    assert _wrap_status(200, False, False, True) == VerificationStatus.mis_ele
    assert _wrap_status(200, False, False, False) == VerificationStatus.ok
    assert _wrap_status(404, False, False, False) == VerificationStatus.fail_404
    assert _wrap_status(403, False, False, False) == VerificationStatus.fail_403
    assert _wrap_status(400, False, False, False) == VerificationStatus.fail_status


def test_is_string_in_text() -> None:
    assert _is_string_in_text("ABC", ["abc"])
    assert _is_string_in_text("ABC", ["ab", "bc"])
    assert not _is_string_in_text("ABC", ["abd"])
    assert not _is_string_in_text("ABC", ["abcd"])
    assert not _is_string_in_text("", ["abc"])


def test_is_ccno_in_text(ccno_des: CCNoDes) -> None:
    assert _is_ccno_in_text("ABC 1234", ccno_des)
    assert _is_ccno_in_text("ABC-1234", ccno_des)
    assert not _is_ccno_in_text("ABC-12-34", ccno_des)
    assert not _is_ccno_in_text("", ccno_des)
    assert not _is_ccno_in_text("HELLO WORLD", ccno_des)


def test_find_elements_in_content(search_task: SearchTask) -> None:
    assert _find_elements_in_content("<div> ABC 1234 </div>".encode("utf-8"), search_task)
    assert not _find_elements_in_content(
        "<div> Hello World </div>".encode("utf-8"), search_task
    )


@pytest.mark.filterwarnings("ignore:.* somelink .*")
def test_prepare_result_raw_skip_suc(
    search_task: SearchTask, cached_resp_suc: CachedPageResp
) -> None:
    assert _prepare_result_raw(
        "somelink", cached_resp_suc, search_task, True
    ) == LinkResult(link="somelink", brc_id=1, found_ccno=search_task.find_ccno)


@pytest.mark.filterwarnings("ignore:.* somelink .*")
def test_prepare_result_raw_suc(
    search_task: SearchTask, cached_resp_suc: CachedPageResp
) -> None:
    assert _prepare_result_raw(
        "somelink", cached_resp_suc, search_task, False
    ) == LinkResult(link="somelink", brc_id=1, found_ccno=search_task.find_ccno)


@pytest.mark.filterwarnings("ignore:.* somelink .*")
def test_prepare_result_raw_fail(
    search_task: SearchTask, cached_resp_fail: CachedPageResp
) -> None:

    assert _prepare_result_raw("somelink", cached_resp_fail, search_task, False) is None


@pytest.mark.filterwarnings("ignore:.* somelink .*")
def test_prepare_result_raw_fail_emp(
    search_task: SearchTask, cached_resp_suc_emp: CachedPageResp
) -> None:

    assert (
        _prepare_result_raw("somelink", cached_resp_suc_emp, search_task, False) is None
    )


def test_get_domain() -> None:
    assert "test.test" == get_domain("http://test.test/1")


def _cr_args_test_verify_ccno_in_url(
    mock_serializer: Mock,
    mock_cache_session: Mock,
    mock_request: Mock,
    task_pack: TaskPackage,
    tmp_path: Path,
    browser_adapter: BrowserPWAdapter,
) -> tuple[
    TaskPackage,
    dict[str, tuple[CoolDownDomain, RobotsTxt]],
    int,
    Path,
    BrowserPWAdapter,
    None,
]:
    cool = CoolDownDomain(get_worker_ctx(), "test.test")
    robot = RobotsTxt("http://test.test/1", get_worker_ctx())
    workdir = tmp_path
    c_down = {"test.test": (cool, robot)}
    mock_serializer.return_value = {"stages": []}
    mock_cache_session.return_value = CachedSession(
        cache_name=str(workdir.joinpath(Path("smth.sqlite"))),
        backend="sqlite",
        expire_after=timedelta(days=2),
        cache_control=False,
        stale_if_error=False,
        allowable_codes=[200, 404, 403],
        allowable_methods=("GET",),
        serializer="yaml",
    )
    mock_request.return_value = CachedPageResp(
        response="<div> ABC 1234 </div>".encode("utf-8"),
        status=200,
        timeout=False,
        prohibited=False,
    )
    return (task_pack, c_down, 20, workdir, browser_adapter, None)


@pytest.mark.filterwarnings("ignore:.* http.*")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.make_get_request")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.create_get_cache")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.yaml_serializer")
def test_verify_ccno_in_url_ok(
    mock_serializer: Mock,
    mock_cache_session: Mock,
    mock_request: Mock,
    task_pack: TaskPackage,
    browser_adapter: BrowserPWAdapter,
    tmp_path: Path,
) -> None:
    args = _cr_args_test_verify_ccno_in_url(
        mock_serializer,
        mock_cache_session,
        mock_request,
        task_pack,
        tmp_path,
        browser_adapter,
    )
    vcn_ex = VerifiedURL(
        1,
        LinkResult("http://test.test/1", 1, task_pack.search_task.find_ccno),
        [
            LinkStatus(
                link="http://test.test/1",
                link_type=LinkLevel.cat.value,
                status=VerificationStatus.ok,
            )
        ],
    )
    vcn = verify_ccno_in_url(args)
    assert vcn_ex == vcn


@pytest.mark.filterwarnings("ignore:.* http.*")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.make_get_request")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.create_get_cache")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.yaml_serializer")
def test_verify_ccno_in_url_fail(
    mock_serializer: Mock,
    mock_cache_session: Mock,
    mock_request: Mock,
    task_pack: TaskPackage,
    browser_adapter: BrowserPWAdapter,
    tmp_path: Path,
) -> None:
    args = _cr_args_test_verify_ccno_in_url(
        mock_serializer,
        mock_cache_session,
        mock_request,
        task_pack,
        tmp_path,
        browser_adapter,
    )
    mock_request.return_value = CachedPageResp(
        response="<div> ABC 1234 </div>".encode("utf-8"),
        status=400,
        timeout=False,
        prohibited=False,
    )
    assert VerifiedURL(
        1,
        None,
        [
            LinkStatus(
                link="http://test.test/1",
                link_type=LinkLevel.cat.value,
                status=VerificationStatus.fail_status,
            ),
            LinkStatus(
                link="http://test.test/",
                link_type=LinkLevel.home.value,
                status=VerificationStatus.fail_status,
            ),
        ],
    ) == verify_ccno_in_url(args)


@pytest.mark.filterwarnings("ignore:.* http.*")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.make_get_request")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.create_get_cache")
@unittest.mock.patch("saim.culture_link.private.verify_ccno.yaml_serializer")
def test_verify_ccno_in_url_fatal(
    mock_serializer: Mock,
    mock_cache_session: Mock,
    mock_request: Mock,
    task_pack: TaskPackage,
    browser_adapter: BrowserPWAdapter,
    tmp_path: Path,
) -> None:
    args = _cr_args_test_verify_ccno_in_url(
        mock_serializer,
        mock_cache_session,
        mock_request,
        task_pack,
        tmp_path,
        browser_adapter,
    )
    mock_request.side_effect = KnownException("Horrible horrible error")
    with pytest.warns(ValidationWarn, match="Horrible horrible error"):
        assert VerifiedURL(
            1,
            None,
            [
                LinkStatus(
                    link="",
                    link_type="",
                    status=VerificationStatus.err,
                )
            ],
        ) == verify_ccno_in_url(args)
