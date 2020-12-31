/* -------------------------------------------------------------------------- */

const { expectRevert } = require("@openzeppelin/test-helpers");
const { toBigInt, oneDai, oneNanoDai, LoanPhase } = require("./helpers");

const DaiMock = artifacts.require("DaiMock");
const TuiChainController = artifacts.require("TuiChainController");
const TuiChainLoan = artifacts.require("TuiChainLoan");
const TuiChainToken = artifacts.require("TuiChainToken");

/* -------------------------------------------------------------------------- */

contract("TuiChainLoan", function(accounts) {
  const fundingFeeAttoDaiPerDai = oneDai / BigInt(10); // 10% fee
  const paymentFeeAttoDaiPerDai = oneDai / BigInt(10); // 10% fee
  const requestedValueAttoDai = BigInt(500) * oneDai;

  let daiMock = null; // deployed DaiMock instance
  let controller = null; // deployed TuiChainController instance
  let loan = null; // deployed TuiChainLoan instance

  /* ------------------------------------------------------------------------ */

  before(async () => {
    // deploy mock Dai contract and credit every account with 1000 Dai

    daiMock = await DaiMock.new();

    for (const acc of accounts) await daiMock.mint(acc, BigInt(1000) * oneDai);

    // deploy controller contract

    controller = await TuiChainController.new(
      daiMock.address, // _dai
      accounts[0], // _marketFeeRecipient
      oneNanoDai / BigInt(10) // _marketFeeAttoDaiPerNanoDai, 10% fee
    );

    // create loan

    const receipt = await controller.createLoan(
      accounts[0], // _feeRecipient
      accounts[1], // _loanRecipient
      BigInt(60), // _secondsToExpiration
      fundingFeeAttoDaiPerDai, // _fundingFeeAttoDaiPerDai
      paymentFeeAttoDaiPerDai, // _paymentFeeAttoDaiPerDai
      requestedValueAttoDai // _requestedValueAttoDai
    );

    loan = await TuiChainLoan.at(receipt.logs[0].address);
    token = await TuiChainToken.at(await loan.token());
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to provide excess funds to loan", async function() {
    await expectRevert(
      loan.provideFunds(BigInt(1000) * oneDai, { from: accounts[2] }),
      "_valueAttoDai exceeds remaining requested funding"
    );
  });

  const fundsToProvide = BigInt(100) * oneDai;

  it("Provide funds to loan", async function() {
    const initialBalanceAttoDai = toBigInt(
      await daiMock.balanceOf(accounts[2])
    );

    await daiMock.approve(
      loan.address,
      fundsToProvide + fundingFeeAttoDaiPerDai * (fundsToProvide / oneDai),
      { from: accounts[2] }
    );

    await loan.provideFunds(fundsToProvide, { from: accounts[2] });

    assert.equal(await loan.fundedValueAttoDai(), fundsToProvide);

    assert.equal(
      await daiMock.balanceOf(accounts[2]),
      initialBalanceAttoDai -
        fundsToProvide -
        fundingFeeAttoDaiPerDai * (fundsToProvide / oneDai)
    );
  });

  it("Fail to withdraw more funds than provided to loan", async function() {
    await expectRevert(
      loan.withdrawFunds(fundsToProvide + oneDai, { from: accounts[2] }),
      "SafeMath: subtraction overflow"
    );

    await expectRevert(
      loan.withdrawFunds(oneDai, { from: accounts[5] }),
      "ERC20: transfer amount exceeds balance"
    );
  });

  it("Withdraw provided funds from loan", async function() {
    const initialBalanceAttoDai = toBigInt(
      await daiMock.balanceOf(accounts[2])
    );

    await token.approve(loan.address, fundsToProvide / oneDai, {
      from: accounts[2]
    });

    await loan.withdrawFunds(fundsToProvide, { from: accounts[2] });

    assert.equal(await loan.fundedValueAttoDai(), 0);

    assert.equal(
      await daiMock.balanceOf(accounts[2]),
      initialBalanceAttoDai +
        fundsToProvide +
        fundingFeeAttoDaiPerDai * (fundsToProvide / oneDai)
    );
  });

  it("Fail to make payment when loan phase is not Active", async function() {
    await expectRevert(loan.makePayment(BigInt(100) * oneDai), "wrong phase");
  });

  it("Fully fund loan", async function() {
    const initialInvestorBalanceAttoDai = toBigInt(
      await daiMock.balanceOf(accounts[2])
    );

    const initialStudentBalanceAttoDai = toBigInt(
      await daiMock.balanceOf(accounts[1])
    );

    await daiMock.approve(
      loan.address,
      requestedValueAttoDai +
        fundingFeeAttoDaiPerDai * (requestedValueAttoDai / oneDai),
      { from: accounts[2] }
    );

    await loan.provideFunds(requestedValueAttoDai, { from: accounts[2] });

    assert.equal(await loan.fundedValueAttoDai(), requestedValueAttoDai);
    assert.equal(await loan.phase(), LoanPhase.Active);

    assert.equal(
      await daiMock.balanceOf(accounts[2]),
      initialInvestorBalanceAttoDai -
        requestedValueAttoDai -
        fundingFeeAttoDaiPerDai * (requestedValueAttoDai / oneDai)
    );

    assert.equal(
      await daiMock.balanceOf(accounts[1]),
      initialStudentBalanceAttoDai + requestedValueAttoDai
    );
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to provide funds when loan phase is not Funding", async function() {
    await expectRevert(
      loan.provideFunds(requestedValueAttoDai - fundsToProvide, {
        from: accounts[2]
      }),
      "wrong phase"
    );
  });

  it("Fail to withdraw provided funds when loan phase is not Funding", async function() {
    await expectRevert(
      loan.withdrawFunds(fundsToProvide, { from: accounts[2] }),
      "wrong phase"
    );
  });

  it("Make loan payment", async function() {
    const initialBalanceAttoDai = toBigInt(
      await daiMock.balanceOf(accounts[1])
    );

    const paymentAttoDai = BigInt(1000) * oneDai;

    await daiMock.approve(
      loan.address,
      paymentAttoDai + paymentFeeAttoDaiPerDai * (paymentAttoDai / oneDai),
      { from: accounts[1] }
    );

    await loan.makePayment(paymentAttoDai, { from: accounts[1] });

    assert.equal(paymentAttoDai, await loan.paidValueAttoDai());

    assert.equal(
      await daiMock.balanceOf(accounts[1]),
      initialBalanceAttoDai -
        paymentAttoDai -
        paymentFeeAttoDaiPerDai * (paymentAttoDai / oneDai)
    );
  });

  it("Fail to redeem tokens when loan phase is not Finalized", async function() {
    await token.approve(loan.address, BigInt(1), { from: accounts[2] });

    await expectRevert(
      loan.redeemTokens(BigInt(1), { from: accounts[2] }),
      "wrong phase"
    );
  });

  it("Finalize loan", async function() {
    await controller.finalizeLoan(loan.address);

    assert.equal(await loan.phase(), LoanPhase.Finalized);
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to redeem more tokens than owned", async function() {
    await token.approve(loan.address, BigInt(2000), { from: accounts[2] });
    await token.approve(loan.address, BigInt(1), { from: accounts[5] });

    await expectRevert(
      loan.redeemTokens(BigInt(2000), { from: accounts[2] }),
      "ERC20: burn amount exceeds balance"
    );

    await expectRevert(
      loan.redeemTokens(BigInt(1), { from: accounts[5] }),
      "ERC20: burn amount exceeds balance"
    );
  });

  it("Redeem tokens", async function() {
    const initialBalanceAttoDai = toBigInt(
      await daiMock.balanceOf(accounts[2])
    );

    const tokensToRedeem = BigInt(10);

    await token.approve(loan.address, tokensToRedeem, { from: accounts[2] });
    await loan.redeemTokens(tokensToRedeem, { from: accounts[2] });

    assert.equal(
      await daiMock.balanceOf(accounts[2]),
      initialBalanceAttoDai +
        toBigInt(await loan.redemptionValueAttoDaiPerToken()) * tokensToRedeem
    );
  });
});

/* -------------------------------------------------------------------------- */
