// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/* -------------------------------------------------------------------------- */

contract DaiMock is ERC20
{
    constructor() ERC20("Dai Stablecoin", "DAI") public
    {
    }

    function mint(address account, uint256 amount) public
    {
        _mint({ account: account, amount: amount });
    }
}

/* -------------------------------------------------------------------------- */
