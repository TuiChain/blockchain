// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

import "truffle/Assert.sol";
import "truffle/DeployedAddresses.sol";
import "../contracts/DebtToken.sol";

contract TestDebtToken {

  function testTotalSupply() public {

    DebtToken token = DebtToken(DeployedAddresses.DebtToken());

    uint expected = 1000;

    Assert.equal(token.totalSupply(), expected, "It should exist 1000 DebtToken initially");

  }
  
  function testBalanceOfOwner() public {

    DebtToken token = DebtToken(DeployedAddresses.DebtToken());

    uint expected = 1000;

    Assert.equal(token.balanceOf(tx.origin), expected, "The contract Owner should have 1000 DebtToken initially");

  }



}
