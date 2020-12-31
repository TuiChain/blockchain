/* -------------------------------------------------------------------------- */

const {
  constants,
  expectEvent,
  expectRevert
} = require("@openzeppelin/test-helpers");

const { oneDai, oneNanoDai, LoanPhase } = require("./helpers");

const DaiMock = artifacts.require("DaiMock");
const TuiChainController = artifacts.require("TuiChainController");
const TuiChainLoan = artifacts.require("TuiChainLoan");
const TuiChainMarket = artifacts.require("TuiChainMarket");

/* -------------------------------------------------------------------------- */

contract("TuiChainController", function(accounts) {
  let daiMock = null; // deployed DaiMock instance
  let controller = null; // deployed TuiChainController instance
  let market = null; // deployed TuiChainMarket instance
  let loan = null; // deployed TuiChainLoan instance

  let createLoanArgs = null; // default arguments to createLoan()

  /* ------------------------------------------------------------------------ */

  before(async function() {
    // deploy mock Dai contract and credit every account with 1000 Dai

    daiMock = await DaiMock.new();

    for (const acc of accounts) await daiMock.mint(acc, BigInt(1000) * oneDai);

    // deploy controller and market contracts

    controller = await TuiChainController.new(
      daiMock.address, // _dai
      accounts[0], // _marketFeeRecipient
      oneNanoDai / BigInt(10) // _marketFeeAttoDaiPerNanoDai, 10% fee
    );

    market = await TuiChainMarket.at(await controller.market());
  });

  beforeEach(async function() {
    createLoanArgs = {
      _feeRecipient: accounts[0],
      _loanRecipient: accounts[1],
      _secondsToExpiration: BigInt(60), // 1 minute
      _fundingFeeAttoDaiPerDai: oneDai / BigInt(10), // 10% fee
      _paymentFeeAttoDaiPerDai: oneDai / BigInt(10), // 10% fee
      _requestedValueAttoDai: BigInt(1000) * oneDai
    };
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to update market fee if not the owner", async function() {
    await expectRevert(
      controller.setMarketFee(oneNanoDai / BigInt(50), {
        from: accounts[1]
      }),
      "Ownable: caller is not the owner"
    );
  });

  it("Update market fee", async function() {
    const newFee = oneNanoDai / BigInt(50);

    await controller.setMarketFee(newFee);
    assert.equal(await market.feeAttoDaiPerNanoDai(), newFee);
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to create loan with the zero address as fee recipient", async function() {
    createLoanArgs._feeRecipient = constants.ZERO_ADDRESS;

    await expectRevert(
      controller.createLoan(...Object.values(createLoanArgs)),
      "_feeRecipient is the zero address"
    );
  });

  it("Fail to create loan with the zero address as loan recipient", async function() {
    createLoanArgs._loanRecipient = constants.ZERO_ADDRESS;

    await expectRevert(
      controller.createLoan(...Object.values(createLoanArgs)),
      "_loanRecipient is the zero address"
    );
  });

  it("Fail to create loan with zero seconds to expiration", async function() {
    createLoanArgs._secondsToExpiration = BigInt(0);

    await expectRevert(
      controller.createLoan(...Object.values(createLoanArgs)),
      "_secondsToExpiration is zero"
    );
  });

  it("Fail to create loan requesting less than 1 Dai", async function() {
    createLoanArgs._requestedValueAttoDai = oneDai / BigInt(10);

    await expectRevert(
      controller.createLoan(...Object.values(createLoanArgs)),
      "not a positive multiple of 1 Dai"
    );
  });

  it("Fail to create loan requesting a value not multiple of 1 Dai", async function() {
    createLoanArgs._requestedValueAttoDai = oneDai + oneDai / BigInt(2);

    await expectRevert(
      controller.createLoan(...Object.values(createLoanArgs)),
      "not a positive multiple of 1 Dai"
    );
  });

  it("Fail to create loan if not the owner", async function() {
    await expectRevert(
      controller.createLoan(...Object.values(createLoanArgs), {
        from: accounts[1]
      }),
      "Ownable: caller is not the owner"
    );
  });

  it("Create loan", async function() {
    const receipt = await controller.createLoan(
      ...Object.values(createLoanArgs)
    );

    loan = await TuiChainLoan.at(receipt.logs[0].address);

    assert.notEqual(await loan.token(), constants.ZERO_ADDRESS);
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to finalize loan if not the owner", async function() {
    assert.isFalse(await loan.checkExpiration.call());

    await expectRevert(
      controller.finalizeLoan(loan.address, { from: accounts[1] }),
      "Ownable: caller is not the owner"
    );
  });

  it("Fail to finalize loan in phase Funding", async function() {
    assert.isFalse(await loan.checkExpiration.call());

    await expectRevert(controller.finalizeLoan(loan.address), "wrong phase");
  });

  it("Finalize loan", async function() {
    // 10 accounts providing 100 Dai each

    let receipt = null;

    for (const acc of accounts) {
      await daiMock.increaseAllowance(loan.address, BigInt(200) * oneDai, {
        from: acc
      });

      receipt = await loan.provideFunds(BigInt(100) * oneDai, { from: acc });
    }

    // ensure that loan transitioned to phase Active

    expectEvent(receipt, "PhaseUpdated", { newPhase: LoanPhase.Active });

    // finalize loan

    receipt = await controller.finalizeLoan(loan.address);

    await expectEvent.inTransaction(receipt.tx, loan, "PhaseUpdated", {
      newPhase: LoanPhase.Finalized
    });
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to cancel loan if not the owner", async function() {
    const receipt = await controller.createLoan(
      ...Object.values(createLoanArgs)
    );

    loan = await TuiChainLoan.at(receipt.logs[0].address);

    assert.isFalse(await loan.checkExpiration.call());

    await expectRevert(
      controller.cancelLoan(loan.address, { from: accounts[1] }),
      "Ownable: caller is not the owner"
    );
  });

  it("Cancel loan", async function() {
    receipt = await controller.cancelLoan(loan.address);

    await expectEvent.inTransaction(receipt.tx, loan, "PhaseUpdated", {
      newPhase: LoanPhase.Canceled
    });
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to manually notify loan activation", async function() {
    await expectRevert(
      controller.notifyLoanActivation(),
      "message sender is not a loan created by this controller"
    );
  });
});

/* -------------------------------------------------------------------------- */
