# ---------------------------------------------------------------------------- #

from __future__ import annotations

import typing as t

import eth_tester
import eth_tester.backends.pyevm.main
import web3
import web3.contract
import web3.types

import tuichain_ethereum as tui

# ---------------------------------------------------------------------------- #


def advance_time(chain: eth_tester.EthereumTester, seconds: int) -> None:
    chain.time_travel(chain.get_block_by_number()["timestamp"] + seconds)
    chain.mine_block()


def execute_user_transactions(
    w3: web3.Web3,
    from_address: tui.Address,
    transactions: t.Iterable[tui.UserTransaction],
) -> None:

    assert isinstance(w3.provider, web3.EthereumTesterProvider)

    tester = w3.provider.ethereum_tester
    assert isinstance(tester, eth_tester.EthereumTester)

    for tx in transactions:

        # create transaction

        params = web3.contract.fill_transaction_defaults(
            w3,
            web3.types.TxParams(
                {
                    "data": web3.types.HexStr(tx.data),
                    "from": from_address._checksummed,
                    "gas": web3.types.Wei(
                        eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT
                    ),
                    "gasPrice": web3.types.Wei(0),
                    "to": web3.Web3.toChecksumAddress(tx.to),
                }
            ),
        )

        # test the transaction locally to get better error messages

        w3.eth.call(params)

        # execute transaction

        tx_hash = w3.eth.sendTransaction(params)

        tester.mine_block()
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

        assert tx_receipt["status"] == 1


# ---------------------------------------------------------------------------- #
