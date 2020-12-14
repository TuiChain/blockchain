// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/* -------------------------------------------------------------------------- */

contract DaiMock is ERC20 {
    constructor() public ERC20("Dai Stablecoin", "DAI") {}

    function mint(address _account, uint256 _amount) external {
        _mint({account: _account, amount: _amount});
    }
}

/* -------------------------------------------------------------------------- */
