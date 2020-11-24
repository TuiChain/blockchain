// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "@openzeppelin/contracts/token/ERC20/ERC20Burnable.sol";

contract TuiChainLoanToken is ERC20Burnable
{
    constructor(uint256 totalSupply) ERC20("", "") public
    {
        // TODO: document
        _setupDecimals(0);

        // assign entire supply to deployer
        _mint(msg.sender, totalSupply);
    }
}

/* -------------------------------------------------------------------------- */
