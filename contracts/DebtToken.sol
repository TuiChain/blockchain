// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract DebtToken is ERC20, AccessControl {

  constructor(string memory name, string memory symbol, uint256 supply) ERC20(name, symbol) public {
    // set the deployer of the contract as the admin
    _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    // create the initial supply in the deployer address
    _mint(msg.sender, supply);
  }

  // CAUTION THIS REPRESENTS SOME RISK
  // NEED A CLOSER LOOK
  function manualTransfer(address sender, address recipient, uint256 amount) public {
    _transfer(sender, recipient, amount);
  }

}
