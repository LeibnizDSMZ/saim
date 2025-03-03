from collections import defaultdict
from typing import Iterable
from saim.designation.known_acr_db import identify_acr_or_code
from saim.history.manager import HistoryManager
from saim.history.private.types import HISTORY, INDEX, STRAIN_CC, STRAIN_DP
from saim.shared.data_con.history import DepositCon, HistoryDepositor


def _create_hist_depositor(history: HISTORY, pos_next: int, /) -> HistoryDepositor:
    dep = HistoryDepositor()
    if pos_next >= len(history):
        return dep
    for his in history[pos_next:]:
        if dep.add_depositor(his):
            break
    return dep


def _create_history_index(histories: list[HISTORY], strain_cc: STRAIN_CC, /) -> INDEX:
    index = defaultdict(list)
    for his_dep in histories:
        for his_ind, his in enumerate(his_dep):
            if his is None:
                continue
            if (
                his.designation is None
                and len(
                    ccno := set(
                        des for brc_id in his.cc_ids for des in strain_cc.get(brc_id, [])
                    )
                )
                == 1
            ):
                full, acr, core, suf = ccno.pop()
                his.designation = (acr, core, suf)
                his.full_designation = full
            if his.designation is not None:
                index[his.designation].append(
                    _create_hist_depositor(his_dep, his_ind + 1)
                )
    return index


def _create_unique_strain_cc(
    strain_dp: Iterable[DepositCon], manager: HistoryManager, /
) -> STRAIN_CC:
    memory: set[tuple[str, str, str]] = set()
    container: STRAIN_CC = defaultdict(list)

    def __verify_memory_and_add(cc_id: int, designation: str, /) -> None:
        acr, core, suf = manager.get_syn_eq_struct(designation)
        if acr != "" and core != "" and (mem := (acr, core, suf)) not in memory:
            cor_cc_id = (
                {cc_id}
                if cc_id > 0
                else identify_acr_or_code(acr, manager.culture_collection_con)
            )
            for cid in cor_cc_id:
                container[cid].append((designation, acr, core, suf))
            memory.add(mem)

    for dep in strain_dp:
        __verify_memory_and_add(dep.cc_id, dep.designation)
        for rel_des in dep.rel_des:
            __verify_memory_and_add(-1, rel_des)
    return container


def _prepare_index(strain_dp: STRAIN_DP, manager: HistoryManager, /) -> INDEX:
    histories = [
        manager.parse_history(
            his,
            dep.cc_id,
            (dep.designation, *manager.get_syn_eq_struct(dep.designation)),
            _create_unique_strain_cc([dep], manager),
        )
        for dep in strain_dp.values()
        for his in dep.history
        if his != ""
    ]
    return _create_history_index(
        histories, _create_unique_strain_cc((dep for dep in strain_dp.values()), manager)
    )


def _prepare_index_strain(
    strain_dp: STRAIN_DP, manager: HistoryManager, /
) -> dict[tuple[str, str, str], int]:
    del_ids: set[tuple[str, str, str]] = set()
    index: dict[tuple[str, str, str], int] = {}
    for si_dp, dep in strain_dp.items():
        if dep.designation == "":
            continue
        if (acr_suf_pre := manager.get_syn_eq_struct(dep.designation))[
            0
        ] != "" and acr_suf_pre[1] != "":
            if acr_suf_pre in index:
                del_ids.add(acr_suf_pre)
            index[acr_suf_pre] = si_dp
    for to_del in del_ids:
        del index[to_del]
    return index


def _get_history_or_none(
    his_con: list[HistoryDepositor], pos: int, /
) -> HistoryDepositor | None:
    if pos >= len(his_con):
        return None
    return his_con[pos]


def assign_depositor_designation(
    strain_dp: STRAIN_DP, manager: HistoryManager, /
) -> Iterable[tuple[int, int]]:
    index = _prepare_index(strain_dp, manager)
    index_si_dp = _prepare_index_strain(strain_dp, manager)
    for si_dp, dep in strain_dp.items():
        if dep.deposited_as > 0:
            continue
        dep_si_dp = set()
        his_con = index.get(manager.get_syn_eq_struct(dep.designation), [])
        for his_ind, his_anc in enumerate(his_con):
            if (
                his_anc.deposition_designation != ""
                and (
                    new_si_dp := index_si_dp.get(
                        manager.get_syn_eq_struct(his_anc.deposition_designation), None
                    )
                )
                is not None
            ):
                dep_si_dp.add(new_si_dp)
            if not his_anc.is_compatible_deposition(
                _get_history_or_none(his_con, his_ind)
            ):
                dep_si_dp = set()
                break
        if len(dep_si_dp) == 1:
            yield si_dp, dep_si_dp.pop()
