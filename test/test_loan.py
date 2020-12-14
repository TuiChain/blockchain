# ---------------------------------------------------------------------------- #

from __future__ import annotations

import eth_tester
import pytest

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #


def advance_time(chain: eth_tester.EthereumTester, seconds: int) -> None:
    chain.time_travel(chain.get_block_by_number()["timestamp"] + seconds)
    chain.mine_block()


def test_get_state(loan: tui.Loan) -> None:
    loan.get_state()


def test_try_expire(
    chain: eth_tester.EthereumTester,
    loan: tui.Loan,
) -> None:

    # try expiring before deadline

    tx = loan.try_expire()
    assert tx.is_done()
    assert not tx.get()

    # try expiring after deadline

    advance_time(chain, 65)

    tx = loan.try_expire()
    assert not tx.is_done()

    chain.mine_block()
    assert tx.is_done()
    assert tx.get()


def test_cancel(
    chain: eth_tester.EthereumTester,
    loan: tui.Loan,
) -> None:

    tx = loan.cancel()
    assert not tx.is_done()

    chain.mine_block()
    assert tx.is_done()
    tx.get()


def test_finalize(loan: tui.Loan) -> None:

    tx = loan.finalize()
    assert tx.is_done()

    with pytest.raises(tui.InvalidLoanPhaseError) as e:
        tx.get()

    assert e.value.observed == tui.LoanPhase.FUNDING


# ---------------------------------------------------------------------------- #
