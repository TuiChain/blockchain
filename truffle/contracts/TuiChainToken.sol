// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainLoan.sol";

import "@openzeppelin/contracts/token/ERC20/ERC20Burnable.sol";

/* -------------------------------------------------------------------------- */

contract TuiChainToken is ERC20Burnable
{
    TuiChainLoan private immutable loan;

    /* ---------------------------------------------------------------------- */

    /**
     * The entire supply is assigned to _loan.
     */
    constructor(TuiChainLoan _loan, uint256 _totalSupply) ERC20("", "") public
    {
        require(_loan != TuiChainLoan(0));

        loan = _loan;

        // TODO: document
        _setupDecimals({ decimals_: 0 });

        // assign entire supply to loan contract
        _mint({ account: address(_loan), amount: _totalSupply });
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Return the loan contract to which this token contract pertains.
     */
    function getLoan() external view returns (TuiChainLoan _loan)
    {
        return loan;
    }
}

/* -------------------------------------------------------------------------- */
