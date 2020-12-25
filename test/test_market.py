# ---------------------------------------------------------------------------- #

from __future__ import annotations

import eth_tester
import pytest

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #


def test_get_fee_atto_dai_per_nano_dai(controller: tui.Controller) -> None:
    assert controller.market.get_fee_atto_dai_per_nano_dai() == 10 ** 7


def test_set_fee(
    chain: eth_tester.EthereumTester, controller: tui.Controller
) -> None:
    def set_fee(fee_atto_dai_per_nano_dai: int) -> None:

        transaction = controller.market.set_fee(
            fee_atto_dai_per_nano_dai=fee_atto_dai_per_nano_dai
        )

        assert not transaction.is_done()

        chain.mine_block()

        assert transaction.is_done()
        transaction.get()

        assert (
            controller.market.get_fee_atto_dai_per_nano_dai()
            == fee_atto_dai_per_nano_dai
        )

    # fail to set invalid fee

    with pytest.raises(
        ValueError, match="`fee_atto_dai_per_nano_dai` must not be negative"
    ):
        controller.market.set_fee(fee_atto_dai_per_nano_dai=-1)

    # set fee

    set_fee(0)
    set_fee(10 ** 7)


def test_user_transaction_builder(controller: tui.Controller) -> None:
    _ = controller.market.user_transaction_builder


def test_get_all_sell_positions(controller: tui.Controller) -> None:
    assert not tuple(controller.market.get_all_sell_positions())


def test_get_sell_positions_by_loan(
    controller: tui.Controller, active_loan: tui.Loan
) -> None:

    assert not tuple(
        controller.market.get_sell_positions_by_loan(loan=active_loan)
    )


def test_get_sell_positions_by_seller(controller: tui.Controller) -> None:

    assert not tuple(
        controller.market.get_sell_positions_by_seller(
            seller_address=tui.Address._random()
        )
    )


def test_get_sell_position_by_loan_and_seller(
    controller: tui.Controller, active_loan: tui.Loan
) -> None:

    assert (
        controller.market.get_sell_position_by_loan_and_seller(
            loan=active_loan, seller_address=tui.Address._random()
        )
        is None
    )


# ---------------------------------------------------------------------------- #
