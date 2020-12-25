# ---------------------------------------------------------------------------- #

from __future__ import annotations

import pytest

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #


def test_get_all(
    controller: tui.Controller,
    funding_loan: tui.Loan,
) -> None:

    ret = tuple(controller.loans.get_all())
    assert len(ret) == 1
    assert ret[0].identifier == funding_loan.identifier


def test_get_by_recipient(
    controller: tui.Controller,
    funding_loan: tui.Loan,
) -> None:

    # non-existent loan

    ret = tuple(
        controller.loans.get_by_recipient(tui.PrivateKey.random().address)
    )
    assert not ret

    # existing loan

    ret = tuple(
        controller.loans.get_by_recipient(funding_loan.recipient_address)
    )
    assert len(ret) == 1
    assert ret[0].identifier == funding_loan.identifier


def test_get_by_identifier(
    controller: tui.Controller,
    funding_loan: tui.Loan,
) -> None:

    # non-existent loan

    with pytest.raises(ValueError, match=""):
        controller.loans.get_by_identifier(tui.LoanIdentifier._random())

    # existing loan

    loan = controller.loans.get_by_identifier(funding_loan.identifier)

    assert loan.identifier == funding_loan.identifier


# ---------------------------------------------------------------------------- #
