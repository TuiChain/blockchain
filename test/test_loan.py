# ---------------------------------------------------------------------------- #

from __future__ import annotations

import eth_tester
import pytest

import tuichain_ethereum._test as tui
import util

# ---------------------------------------------------------------------------- #


def test_try_expire(
    chain: eth_tester.EthereumTester,
    funding_loan: tui.Loan,
) -> None:

    # try expiring before deadline

    tx = funding_loan.try_expire()
    assert tx.is_done()
    assert not tx.get()

    # try expiring after deadline

    util.advance_time(chain, 65)

    tx = funding_loan.try_expire()
    assert not tx.is_done()

    chain.mine_block()
    assert tx.is_done()
    assert tx.get()


def test_cancel(
    chain: eth_tester.EthereumTester,
    funding_loan: tui.Loan,
) -> None:

    tx = funding_loan.cancel()
    assert not tx.is_done()

    chain.mine_block()
    assert tx.is_done()
    tx.get()


def test_finalize(funding_loan: tui.Loan) -> None:

    tx = funding_loan.finalize()
    assert tx.is_done()

    with pytest.raises(
        ValueError, match="Loan is in phase FUNDING, expected ACTIVE"
    ):
        tx.get()


# ---------------------------------------------------------------------------- #
