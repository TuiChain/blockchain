// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

contract State {

  //=======================
  // Variables & constants
  //=======================

  // possible states
  enum StateEnum { SALE, ACTIVE, REDEEMABLE, CANCELED }
  StateEnum private state;

  //=======================
  // Constructor
  //=======================

  constructor () internal {
    state = StateEnum.SALE;
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

  modifier isRedeemableState() {
    require(state == StateEnum.REDEEMABLE);
    _;
  }

  modifier isCanceledState() {
    require(state == StateEnum.CANCELED);
    _;
  }

  modifier isSaleOrCanceledState() {
    require(state == StateEnum.CANCELED || state == StateEnum.SALE);
    _;
  }

  //=======================
  // Functions
  //=======================

  function setState(StateEnum _state) internal {
    state = _state;
  }

}
