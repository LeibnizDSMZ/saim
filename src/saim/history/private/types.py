from saim.shared.data_con.history import DepositCon, HistoryDeposition, HistoryDepositor


type HISTORY = list[HistoryDeposition | None]
type INDEX = dict[tuple[str, str, str], list[HistoryDepositor]]
type DESIGNATION = tuple[str, str, str, str]
type STRAIN_CC = dict[int, list[DESIGNATION]]
type STRAIN_DP = dict[int, DepositCon]
