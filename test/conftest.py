# ---------------------------------------------------------------------------- #

from __future__ import annotations

import datetime
import secrets
import typing

import eth_tester
import eth_tester.backends.pyevm.main
import pytest
import web3
import web3.types

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #

# increase block gas limit
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8_000_000

# ---------------------------------------------------------------------------- #


@pytest.fixture
def chain() -> eth_tester.EthereumTester:

    ethereum_tester = eth_tester.EthereumTester()
    ethereum_tester.disable_auto_mine_transactions()

    return ethereum_tester


@pytest.fixture
def w3(chain: eth_tester.EthereumTester) -> web3.Web3:

    w3 = web3.Web3(web3.EthereumTesterProvider(chain))
    w3.enable_strict_bytes_type_checking()

    return w3


@pytest.fixture
def users(chain: eth_tester.EthereumTester) -> typing.Sequence[tui.Address]:
    return tuple(map(tui.Address, chain.get_accounts()))


@pytest.fixture
def master(
    chain: eth_tester.EthereumTester,
    users: typing.Sequence[tui.Address],
    w3: web3.Web3,
) -> tui.PrivateKey:

    # generate private key for master account

    master_account = tui.PrivateKey.random()

    # eth-tester unfortunately signs read-only calls, so must add private key

    chain.add_account(bytes(master_account).hex())

    # transfer some ether to new account

    w3.eth.sendTransaction(
        {
            "from": users[0]._checksummed,
            "to": master_account.address._checksummed,
            "value": web3.Web3.toWei(100_000, "ether"),
        }
    )

    chain.mine_block()

    # return master account private key

    return master_account


@pytest.fixture
def controller(
    chain: eth_tester.EthereumTester,
    master: tui.PrivateKey,
    users: typing.Sequence[tui.Address],
    w3: web3.Web3,
) -> tui.Controller:

    # deploy controller

    tx_controller = tui.Controller.deploy(
        provider=w3.provider,
        master_account_private_key=master,
        dai_contract_address=tui.Address.MAINNET_DAI_CONTRACT,
        market_fee_atto_dai_per_nano_dai=42,
    )

    assert not tx_controller.is_done()
    chain.mine_block()
    assert tx_controller.is_done()

    controller = tx_controller.get()

    # test access to controller properties and methods

    _ = controller.chain_id
    _ = controller.contract_address
    _ = controller.market

    assert not tuple(controller.get_all_loans())
    assert not tuple(controller.get_loans_by_recipient(users[0]))

    assert (
        controller.get_loan_by_identifier(
            tui.LoanIdentifier(secrets.token_bytes(20))
        )
        is None
    )

    # with pytest.raises(ValueError, match=r"is not the owner of"):
    #     tui.Controller(
    #         provider=w3.provider,
    #         master_account_private_key=tui.PrivateKey.random(),
    #         contract_address=controller.contract_address,
    #     )

    assert controller.market.get_fee_atto_dai_per_nano_dai() == 42

    return controller


@pytest.fixture
def loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    users: typing.Sequence[tui.Address],
) -> tui.Loan:

    tx_create = controller.create_loan(
        recipient_address=users[0],
        time_to_expiration=datetime.timedelta(minutes=1),
        funding_fee_atto_dai_per_dai=5 * (10 ** 16),
        payment_fee_atto_dai_per_dai=10 * (10 ** 16),
        requested_value_atto_dai=20_000 * (10 ** 18),
    )

    assert not tx_create.is_done()

    chain.mine_block()
    assert tx_create.is_done()

    loan = tx_create.get()

    return loan


# ---------------------------------------------------------------------------- #
