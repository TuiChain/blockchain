# ---------------------------------------------------------------------------- #

from __future__ import annotations

import typing as t

import eth_tester
import pytest
import web3
import web3.exceptions

import tuichain_ethereum._test as tui

# ---------------------------------------------------------------------------- #


def test_deploy(
    accounts: t.Sequence[tui.PrivateKey],
    chain: eth_tester.EthereumTester,
    dai: tui.DaiMockContract,
    w3: web3.Web3,
) -> None:
    def deploy(market_fee_atto_dai_per_nano_dai: int) -> None:

        transaction = tui.Controller.deploy(
            provider=w3.provider,
            master_account_private_key=accounts[0],
            dai_contract_address=dai.address,
            market_fee_atto_dai_per_nano_dai=market_fee_atto_dai_per_nano_dai,
        )

        assert not transaction.is_done()

        chain.mine_block()
        assert transaction.is_done()

        transaction.get()

    # fail to deploy controller with invalid market fee

    with pytest.raises(
        ValueError, match="`fee_atto_dai_per_nano_dai` must not be negative"
    ):
        deploy(market_fee_atto_dai_per_nano_dai=-1)

    # deploy controller

    deploy(market_fee_atto_dai_per_nano_dai=0)
    deploy(market_fee_atto_dai_per_nano_dai=10 ** 7)


def test_init(
    accounts: t.Sequence[tui.PrivateKey],
    controller: tui.Controller,
    w3: web3.Web3,
) -> None:

    # connect to existing controller contract as the owner

    tui.Controller(
        provider=w3.provider,
        master_account_private_key=accounts[0],
        contract_address=controller.contract_address,
    )

    # fail to connect to a existing controller contract without being the owner

    with pytest.raises(ValueError, match="is not the owner of"):

        tui.Controller(
            provider=w3.provider,
            master_account_private_key=accounts[1],
            contract_address=controller.contract_address,
        )

    # fail to connect to a non-existing controller contract

    with pytest.raises(web3.exceptions.BadFunctionCallOutput):

        tui.Controller(
            provider=w3.provider,
            master_account_private_key=accounts[0],
            contract_address=tui.Address._random(),
        )


def test_chain_id(controller: tui.Controller, w3: web3.Web3) -> None:
    assert controller.chain_id == w3.eth.chainId


def test_contract_address(controller: tui.Controller) -> None:
    _ = controller.contract_address


def test_loans(controller: tui.Controller) -> None:
    _ = controller.loans


def test_market(controller: tui.Controller) -> None:
    _ = controller.market


# ---------------------------------------------------------------------------- #
