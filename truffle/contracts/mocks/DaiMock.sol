// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/* -------------------------------------------------------------------------- */

contract DaiMock is ERC20 {
    constructor() public ERC20("Dai Stablecoin", "DAI") {}

    function mint(address account, uint256 amount) external {
        _mint({account: account, amount: amount});
    }
}

/* -------------------------------------------------------------------------- */
