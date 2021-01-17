# ---------------------------------------------------------------------------- #

from __future__ import annotations

import typing as t

import pytest
import web3
import web3.exceptions

import tuichain_ethereum as tui
import util

# ---------------------------------------------------------------------------- #


def _invalid_dai_transfers(
    build: t.Callable[[int], t.Sequence[tui.UserTransaction]],
) -> None:

    error_message = "`value_atto_dai` must be a positive multiple of 1 Dai"

    with pytest.raises(ValueError, match=error_message):
        build(-1 * (10 ** 18))

    with pytest.raises(ValueError, match=error_message):
        build(0)

    with pytest.raises(ValueError, match=error_message):
        build((10 ** 18) - 1)

    with pytest.raises(ValueError, match=error_message):
        build((10 ** 18) + 1)


def test_provide_funds(
    accounts: t.Sequence[tui.PrivateKey], funding_loan: tui.Loan, w3: web3.Web3
) -> None:
    def provide_funds(value_dai: int) -> None:
        util.execute_user_transactions(
            w3=w3,
            from_address=accounts[2].address,
            transactions=funding_loan.user_transaction_builder.provide_funds(
                value_atto_dai=value_dai * (10 ** 18)
            ),
        )

    # fail to provide invalid amounts

    _invalid_dai_transfers(
        lambda v: funding_loan.user_transaction_builder.provide_funds(
            value_atto_dai=v
        ),
    )

    # provide 9999 Dai

    provide_funds(9_999)

    assert funding_loan.get_state().funded_value_atto_dai == 9_999 * (10 ** 18)

    # provide 1 Dai

    provide_funds(1)

    assert funding_loan.get_state().funded_value_atto_dai == 10_000 * (10 ** 18)


def test_withdraw_funds(
    accounts: t.Sequence[tui.PrivateKey], funding_loan: tui.Loan, w3: web3.Web3
) -> None:
    def withdraw_funds(value_dai: int) -> None:
        util.execute_user_transactions(
            w3=w3,
            from_address=accounts[2].address,
            transactions=funding_loan.user_transaction_builder.withdraw_funds(
                value_atto_dai=value_dai * (10 ** 18)
            ),
        )

    # provide 10 thousand Dai

    util.execute_user_transactions(
        w3=w3,
        from_address=accounts[2].address,
        transactions=funding_loan.user_transaction_builder.provide_funds(
            value_atto_dai=10_000 * (10 ** 18)
        ),
    )

    # fail to withdraw invalid amounts

    _invalid_dai_transfers(
        lambda v: funding_loan.user_transaction_builder.withdraw_funds(
            value_atto_dai=v
        ),
    )

    # withdraw 4999 Dai

    withdraw_funds(4_999)

    assert funding_loan.get_state().funded_value_atto_dai == 5_001 * (10 ** 18)

    # fail to withdraw 6 000 Dai

    with pytest.raises(Exception):
        withdraw_funds(6_000)

    assert funding_loan.get_state().funded_value_atto_dai == 5_001 * (10 ** 18)

    # withdraw the remaining 5 001 Dai

    withdraw_funds(5_001)

    assert funding_loan.get_state().funded_value_atto_dai == 0


def test_make_payment(
    accounts: t.Sequence[tui.PrivateKey], active_loan: tui.Loan, w3: web3.Web3
) -> None:
    def make_payment(value_dai: int) -> None:
        util.execute_user_transactions(
            w3=w3,
            from_address=accounts[2].address,
            transactions=active_loan.user_transaction_builder.make_payment(
                value_atto_dai=value_dai * (10 ** 18)
            ),
        )

    # fail to pay invalid amounts

    _invalid_dai_transfers(
        lambda v: active_loan.user_transaction_builder.make_payment(
            value_atto_dai=v
        ),
    )

    # pay 9999 Dai

    make_payment(9_999)

    assert active_loan.get_state().paid_value_atto_dai == 9_999 * (10 ** 18)

    # pay 1 Dai

    make_payment(1)

    assert active_loan.get_state().paid_value_atto_dai == 10_000 * (10 ** 18)


def test_redeem_tokens(
    accounts: t.Sequence[tui.PrivateKey],
    finalized_loan: tui.Loan,
    w3: web3.Web3,
) -> None:
    def redeem_tokens(amount_tokens: int) -> None:
        util.execute_user_transactions(
            w3=w3,
            from_address=accounts[2].address,
            transactions=finalized_loan.user_transaction_builder.redeem_tokens(
                amount_tokens=amount_tokens
            ),
        )

    # fail to redeem invalid amounts

    error_message = "`amount_tokens` must be positive"

    with pytest.raises(ValueError, match=error_message):
        finalized_loan.user_transaction_builder.redeem_tokens(-1)

    with pytest.raises(ValueError, match=error_message):
        finalized_loan.user_transaction_builder.redeem_tokens(0)

    # redeem 14999 tokens

    redeem_tokens(14_999)

    # fail to withdraw 6 000 tokens

    with pytest.raises(Exception, match="burn amount exceeds balance"):
        redeem_tokens(6_000)

    # redeem the remaining 5 001 tokens

    redeem_tokens(5_001)


# ---------------------------------------------------------------------------- #
