// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

library ValidationLibrary {

  // @return true if the transaction can buy tokens
  function validPurchase(uint256 _value, address purchaser) internal pure returns (bool) {
    return _value != 0 && 
           validAddress(purchaser);
  }

  // @return true if the transaction can create contract
  function validContractCreation(uint256 _startTime, uint256 _endTime, uint256 _rate, IERC20 _token) 
    internal view returns (bool) {
    return (_startTime >= now) && 
           (_startTime <= _endTime) && 
           (_rate > 0) &&
           validAddress(address(_token));
  }

  // @return true if the address is 
  function validAddress(address _address) internal pure returns (bool) {
    return _address != address(0);
  }

  // @return true if give time has passed
  function hasEnded(uint256 _endTime) internal view returns (bool) {
    return now > _endTime;
  }

}
