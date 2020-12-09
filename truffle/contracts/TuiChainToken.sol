// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainLoan.sol";

import "@openzeppelin/contracts/token/ERC20/ERC20Burnable.sol";

/* -------------------------------------------------------------------------- */

/**
 * An ERC-20 contract implementing loan tokens.
 *
 * Note that decimals() returns 0 for these tokens.
 */
contract TuiChainToken is ERC20Burnable
{
    /** The loan contract to which this token contract pertains. */
    TuiChainLoan public immutable loan;

    /* ---------------------------------------------------------------------- */

    /**
     * Construct a TuiChainToken.
     *
     * The token's entire supply is assigned to the given loan contract.
     *
     * @param _loan The loan contract to which the token pertains
     * @param _totalSupply The token's total supply
     */
    constructor(TuiChainLoan _loan, uint256 _totalSupply) ERC20("", "") public
    {
        require(_loan != TuiChainLoan(0), "_loan is the zero address");

        loan = _loan;

        _setupDecimals({ decimals_: 0 });
        _mint({ account: address(_loan), amount: _totalSupply });
    }
}

/* -------------------------------------------------------------------------- */
