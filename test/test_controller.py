# ---------------------------------------------------------------------------- #

from __future__ import annotations

import secrets

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #


def test_get_all_loans(
    controller: tui.Controller,
    loan: tui.Loan,
) -> None:

    ret = tuple(controller.get_all_loans())
    assert len(ret) == 1
    assert ret[0].identifier == loan.identifier


def test_get_loans_by_recipient(
    controller: tui.Controller,
    loan: tui.Loan,
) -> None:

    # non-existent loan

    ret = tuple(
        controller.get_loans_by_recipient(tui.PrivateKey.random().address)
    )
    assert not ret

    # existing loan

    ret = tuple(controller.get_loans_by_recipient(loan.recipient_address))
    assert len(ret) == 1
    assert ret[0].identifier == loan.identifier


def test_get_loan_by_identifier(
    controller: tui.Controller,
    loan: tui.Loan,
) -> None:

    # non-existent loan

    ret = controller.get_loan_by_identifier(
        tui.LoanIdentifier(secrets.token_bytes(20))
    )

    assert ret is None

    # existing loan

    ret = controller.get_loan_by_identifier(loan.identifier)
    assert ret is not None
    assert ret.identifier == loan.identifier


# ---------------------------------------------------------------------------- #
