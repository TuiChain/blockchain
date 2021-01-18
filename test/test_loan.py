# ---------------------------------------------------------------------------- #

from __future__ import annotations

import typing as t

import eth_tester
import pytest

import tuichain_ethereum as tui
import util

# ---------------------------------------------------------------------------- #


def test_get_state(
    funding_loan: tui.Loan,
    active_loan: tui.Loan,
    finalized_loan: tui.Loan,
) -> None:
    def query(state: tui.LoanState) -> None:
        _ = state.phase
        _ = state.funded_value_atto_dai
        _ = state.paid_value_atto_dai
        _ = state.redemption_value_atto_dai_per_token

    query(funding_loan.get_state())
    query(active_loan.get_state())
    query(finalized_loan.get_state())


def test_get_token_balance_of(
    accounts: t.Sequence[tui.PrivateKey],
    active_loan: tui.Loan,
) -> None:

    balance = active_loan.get_token_balance_of(accounts[1].address)
    assert balance == 0

    balance = active_loan.get_token_balance_of(accounts[2].address)
    assert balance == (active_loan.requested_value_atto_dai // (10 ** 18))


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
