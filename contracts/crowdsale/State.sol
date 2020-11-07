// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

contract State {

  //=======================
  // Variables & constants
  //=======================

  // possible states
  enum StateEnum { SALE, ACTIVE, REDEEMABLE, CANCELED }
  StateEnum private state;

  // start and end timestamps where investments are allowed 
  uint256 public startTime;
  uint256 public endTime;

  //=======================
  // Constructor
  //=======================

  constructor (uint256 _startTime, uint256 _endTime) public {
    state = StateEnum.SALE;
    startTime = _startTime;
    endTime = _endTime;
  }

  //=======================
  // Modifiers
  //=======================

  modifier isSaleState() {
    require(state == StateEnum.SALE);
    _;
  }

  modifier isActiveState() {
    require(state == StateEnum.ACTIVE);
    _;
  }

  modifier isRedeembleState() {
    require(state == StateEnum.REDEEMABLE);
    _;
  }

  modifier isCanceledState() {
    require(state == StateEnum.CANCELED);
    _;
  }

  //=======================
  // Functions
  //=======================

}
