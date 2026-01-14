import pytest

from saim.culture_link.private.cached_session import BrowserPWAdapter, PWContext
from saim.culture_link.private.container import CachedPageResp, SearchTask, TaskPackage
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.shared.data_con.designation import CCNoDes, CCNoId
from saim.shared.misc.ctx import get_worker_ctx

from cafi.container.links import CatalogueLink, LinkLevel


@pytest.fixture
def cool_down() -> CoolDownDomain:
    return CoolDownDomain(get_worker_ctx(), "test.test")


@pytest.fixture
def ccno_des() -> CCNoDes:
    ccno_id = CCNoId(full="1234", core="1234", pre="", suf="")
    return CCNoDes(acr="ABC", id=ccno_id, designation="ABC 1234")


@pytest.fixture
def search_task(ccno_des: CCNoDes) -> SearchTask:
    return SearchTask(brc_id=1, find_ccno=ccno_des, find_extra=[])


@pytest.fixture
def cached_resp_suc() -> CachedPageResp:
    return CachedPageResp(
        response="<div> ABC 1234 </div>".encode("utf-8"),
        status=200,
        timeout=False,
        prohibited=False,
    )


@pytest.fixture
def cached_resp_suc_emp() -> CachedPageResp:
    return CachedPageResp(
        response=" ".encode("utf-8"),
        status=200,
        timeout=False,
        prohibited=False,
    )


@pytest.fixture
def cached_resp_fail() -> CachedPageResp:
    return CachedPageResp(
        response="<div> ABC 1234 </div>".encode("utf-8"),
        status=400,
        timeout=False,
        prohibited=False,
    )


@pytest.fixture
def task_pack(search_task: SearchTask) -> TaskPackage:
    link = CatalogueLink(
        level=LinkLevel.cat,
        catalogue=["http://test.test/1"],
        homepage="http://test.test/",
    )
    return TaskPackage(
        task_id=1, search_task=search_task, template_links=link, fallback_link=""
    )


@pytest.fixture(scope="session")
def browser_adapter() -> BrowserPWAdapter:
    return BrowserPWAdapter(PWContext(2, True), "")
