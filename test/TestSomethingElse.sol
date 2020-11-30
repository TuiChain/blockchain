// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "truffle/Assert.sol";

import "../contracts/mocks/DaiMock.sol";
import "../contracts/TuiChainToken.sol";

/* -------------------------------------------------------------------------- */

contract TestSomethingElse
{
    DaiMock dai;

    function beforeAll() public
    {
        dai = new DaiMock();
    }

    function testOneThing() public
    {
        Assert.equal(dai.balanceOf(msg.sender), 0, "huh?");
    }
}

/* -------------------------------------------------------------------------- */
