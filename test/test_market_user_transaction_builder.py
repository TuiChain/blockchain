# ---------------------------------------------------------------------------- #

from __future__ import annotations

import pytest

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #


def test_create_sell_position(
    active_loan: tui.Loan, controller: tui.Controller
) -> None:
    def build(amount_tokens: int, price_atto_dai_per_token: int) -> None:
        controller.market.user_transaction_builder.create_sell_position(
            loan=active_loan,
            amount_tokens=amount_tokens,
            price_atto_dai_per_token=price_atto_dai_per_token,
        )

    # fail to build transactions to create position with invalid token amounts

    msg = "`amount_tokens` must be positive"

    with pytest.raises(ValueError, match=msg):
        build(amount_tokens=-1, price_atto_dai_per_token=10 ** 18)

    with pytest.raises(ValueError, match=msg):
        build(amount_tokens=0, price_atto_dai_per_token=10 ** 18)

    # fail to build transactions to create position with invalid price

    msg = "`price_atto_dai_per_token` must be a positive multiple of 1 nano-Dai"

    with pytest.raises(ValueError, match=msg):
        build(amount_tokens=1, price_atto_dai_per_token=-1 * (10 ** 18))

    with pytest.raises(ValueError, match=msg):
        build(amount_tokens=1, price_atto_dai_per_token=0)

    with pytest.raises(ValueError, match=msg):
        build(amount_tokens=1, price_atto_dai_per_token=(10 ** 18) - 1)

    with pytest.raises(ValueError, match=msg):
        build(amount_tokens=1, price_atto_dai_per_token=(10 ** 18) + 1)

    # build transactions to create position

    build(amount_tokens=1, price_atto_dai_per_token=10 ** 18)


def test_remove_sell_position(
    active_loan: tui.Loan, controller: tui.Controller
) -> None:

    # build transactions to create position

    controller.market.user_transaction_builder.remove_sell_position(
        loan=active_loan
    )


def test_increase_sell_position_amount(
    active_loan: tui.Loan, controller: tui.Controller
) -> None:

    builder = controller.market.user_transaction_builder

    def build(increase_amount: int) -> None:
        builder.increase_sell_position_amount(
            loan=active_loan, increase_amount=increase_amount
        )

    # fail to build transactions with invalid increase amount

    msg = "`increase_amount` must be positive"

    with pytest.raises(ValueError, match=msg):
        build(increase_amount=-1)

    with pytest.raises(ValueError, match=msg):
        build(increase_amount=0)

    # build transactions to increase amount

    build(increase_amount=1)


def test_decrease_sell_position_amount(
    active_loan: tui.Loan, controller: tui.Controller
) -> None:

    builder = controller.market.user_transaction_builder

    def build(decrease_amount: int) -> None:
        builder.decrease_sell_position_amount(
            loan=active_loan, decrease_amount=decrease_amount
        )

    # fail to build transactions with invalid decrease amount

    msg = "`decrease_amount` must be positive"

    with pytest.raises(ValueError, match=msg):
        build(decrease_amount=-1)

    with pytest.raises(ValueError, match=msg):
        build(decrease_amount=0)

    # build transactions to decrease amount

    build(decrease_amount=1)


def test_update_sell_position_price(
    active_loan: tui.Loan, controller: tui.Controller
) -> None:
    def build(new_price_atto_dai_per_token: int) -> None:
        controller.market.user_transaction_builder.update_sell_position_price(
            loan=active_loan,
            new_price_atto_dai_per_token=new_price_atto_dai_per_token,
        )

    # fail to build transactions with invalid new price

    error_message = (
        "`new_price_atto_dai_per_token` must be a positive multiple of 1"
        " nano-Dai"
    )

    with pytest.raises(ValueError, match=error_message):
        build(new_price_atto_dai_per_token=-1 * (10 ** 18))

    with pytest.raises(ValueError, match=error_message):
        build(new_price_atto_dai_per_token=0)

    with pytest.raises(ValueError, match=error_message):
        build(new_price_atto_dai_per_token=(10 ** 18) - 1)

    with pytest.raises(ValueError, match=error_message):
        build(new_price_atto_dai_per_token=(10 ** 18) + 1)

    # build transactions to update price

    build(new_price_atto_dai_per_token=10 ** 18)


def test_purchase(active_loan: tui.Loan, controller: tui.Controller) -> None:
    def build(
        seller_address: tui.Address,
        amount_tokens: int,
        price_atto_dai_per_token: int,
        fee_atto_dai_per_nano_dai: int,
    ) -> None:

        controller.market.user_transaction_builder.purchase(
            loan=active_loan,
            seller_address=seller_address,
            amount_tokens=amount_tokens,
            price_atto_dai_per_token=price_atto_dai_per_token,
            fee_atto_dai_per_nano_dai=fee_atto_dai_per_nano_dai,
        )

    # fail to build transactions to purchase with invalid token amount

    msg = "`amount_tokens` must be positive"

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=-1,
            price_atto_dai_per_token=10 ** 18,
            fee_atto_dai_per_nano_dai=10 ** 7,
        )

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=0,
            price_atto_dai_per_token=10 ** 18,
            fee_atto_dai_per_nano_dai=10 ** 7,
        )

    # fail to build transactions to purchase with invalid price

    msg = "`price_atto_dai_per_token` must be a positive multiple of 1 nano-Dai"

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=1,
            price_atto_dai_per_token=-1 * (10 ** 9),
            fee_atto_dai_per_nano_dai=10 ** 7,
        )

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=1,
            price_atto_dai_per_token=0,
            fee_atto_dai_per_nano_dai=10 ** 7,
        )

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=1,
            price_atto_dai_per_token=(10 ** 9) - 1,
            fee_atto_dai_per_nano_dai=10 ** 7,
        )

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=1,
            price_atto_dai_per_token=(10 ** 9) + 1,
            fee_atto_dai_per_nano_dai=10 ** 7,
        )

    # fail to build transactions to purchase with invalid fee

    msg = "`fee_atto_dai_per_nano_dai` must not be negative"

    with pytest.raises(ValueError, match=msg):
        build(
            seller_address=tui.Address._random(),
            amount_tokens=1,
            price_atto_dai_per_token=10 ** 18,
            fee_atto_dai_per_nano_dai=-1,
        )

    # build transactions to purchase

    build(
        seller_address=tui.Address._random(),
        amount_tokens=1,
        price_atto_dai_per_token=10 ** 18,
        fee_atto_dai_per_nano_dai=10 ** 7,
    )

    build(
        seller_address=tui.Address._random(),
        amount_tokens=1,
        price_atto_dai_per_token=10 ** 9,
        fee_atto_dai_per_nano_dai=0,
    )


# ---------------------------------------------------------------------------- #
