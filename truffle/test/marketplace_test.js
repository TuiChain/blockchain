/* -------------------------------------------------------------------------- */

const { expectRevert } = require("@openzeppelin/test-helpers");
const { toBigInt, oneDai, oneNanoDai } = require("./helpers");

const DaiMock = artifacts.require("DaiMock");
const TuiChainController = artifacts.require("TuiChainController");
const TuiChainLoan = artifacts.require("TuiChainLoan");
const TuiChainMarket = artifacts.require("TuiChainMarket");
const TuiChainToken = artifacts.require("TuiChainToken");

/* -------------------------------------------------------------------------- */

contract("TuiChainMarket", function(accounts) {
  const marketFeeAttoDaiPerNanoDai = oneNanoDai / BigInt(10); // 10% fee
  const requestedValueAttoDai = BigInt(1000) * oneDai;

  let daiMock = null; // deployed DaiMock instance
  let controller = null; // deployed TuiChainController instance
  let market = null; // deployed TuiChainMarket instance
  let loan = null; // deployed TuiChainLoan instance
  let token = null; // deployed TuiChainToken instance

  let createLoanArgs = null; // default arguments to createLoan()

  /* ------------------------------------------------------------------------ */

  before(async function() {
    // deploy mock Dai contract and credit every account with 1200 Dai

    daiMock = await DaiMock.new();

    for (const acc of accounts) await daiMock.mint(acc, BigInt(1200) * oneDai);

    // deploy controller contract
    controller = await TuiChainController.new(
      daiMock.address, // _dai
      accounts[0], // _marketFeeRecipient
      marketFeeAttoDaiPerNanoDai // _marketFeeAttoDaiPerNanoDai
    );

    market = await TuiChainMarket.at(await controller.market());

    // deploy loan contract

    const receipt = await controller.createLoan(
      accounts[0], // _feeRecipient
      accounts[1], // _loanRecipient
      BigInt(60), // _secondsToExpiration
      oneDai / BigInt(10), // _fundingFeeAttoDaiPerDai, 10% fee
      oneDai / BigInt(10), // _paymentFeeAttoDaiPerDai, 10% fee
      requestedValueAttoDai // _requestedValueAttoDai
    );

    loan = await TuiChainLoan.at(receipt.logs[0].address);
    token = await TuiChainToken.at(await loan.token());

    // allows tokens to be transfered to our contracts

    await daiMock.increaseAllowance(loan.address, BigInt(1200) * oneDai, {
      from: accounts[2]
    });

    await daiMock.increaseAllowance(market.address, BigInt(1200) * oneDai, {
      from: accounts[3]
    });

    await token.increaseAllowance(market.address, BigInt(1000), {
      from: accounts[2]
    });

    // account 3 funds the loan

    await loan.provideFunds(requestedValueAttoDai, { from: accounts[2] });
  });

  /* ------------------------------------------------------------------------ */

  it("Fail to create sell position without sufficient balance", async function() {
    await expectRevert(
      market.createSellPosition(
        token.address,
        BigInt(1050),
        BigInt(55) * oneDai,
        { from: accounts[2] }
      ),
      "ERC20: transfer amount exceeds balance"
    );
  });

  it("Fail to create sell position with amount zero", async function() {
    await expectRevert(
      market.createSellPosition(token.address, BigInt(0), BigInt(55) * oneDai, {
        from: accounts[2]
      }),
      "_amountTokens is zero"
    );
  });

  it("Fail to create sell position for disallowed token", async function() {
    await expectRevert(
      market.createSellPosition(
        daiMock.address,
        BigInt(1050),
        BigInt(55) * oneDai,
        { from: accounts[2] }
      ),
      "_token not allowed by the market"
    );
  });

  it("Create sell position", async function() {
    const initialTokensBalance = toBigInt(await token.balanceOf(accounts[2]));
    const tokensToSell = BigInt(50);

    await market.createSellPosition(
      token.address,
      tokensToSell,
      BigInt(55) * oneDai,
      { from: accounts[2] }
    );

    assert.equal(
      await token.balanceOf(accounts[2]),
      initialTokensBalance - tokensToSell
    );
  });

  it("Fail to update price of nonexistent sell position", async function() {
    await expectRevert(
      market.updateSellPositionPrice(token.address, BigInt(60) * oneDai, {
        from: accounts[1]
      }),
      "sell position does not exist"
    );
  });

  it("Update sell position price", async function() {
    await market.updateSellPositionPrice(token.address, BigInt(60) * oneDai, {
      from: accounts[2]
    });
  });

  it("Fail to create duplicate sell position", async function() {
    await expectRevert(
      market.createSellPosition(
        token.address,
        BigInt(50),
        BigInt(55) * oneDai,
        { from: accounts[2] }
      ),
      "sell position already exists"
    );
  });

  it("Fail to increase the amount of a nonexistent sell position", async function() {
    await expectRevert(
      market.increaseSellPositionAmount(token.address, BigInt(1), {
        from: accounts[1]
      }),
      "sell position does not exist"
    );
  });

  it("Increase the amount of a sell position", async function() {
    const initialTokensBalance = toBigInt(await token.balanceOf(accounts[2]));
    const tokensToIncrease = BigInt(5);

    await market.increaseSellPositionAmount(token.address, tokensToIncrease, {
      from: accounts[2]
    });

    assert.equal(
      await token.balanceOf(accounts[2]),
      initialTokensBalance - tokensToIncrease
    );
  });

  it("Fail to decrease the amount of a nonexistent sell position", async function() {
    await expectRevert(
      market.decreaseSellPositionAmount(token.address, BigInt(1), {
        from: accounts[1]
      }),
      "sell position does not exist"
    );
  });

  it("Fail to decrease the amount of a sell position to a negative value", async function() {
    await expectRevert(
      market.decreaseSellPositionAmount(token.address, BigInt(100), {
        from: accounts[2]
      }),
      "_decreaseAmount exceeds amount for sale"
    );
  });

  it("Decrease the amount of a sell position", async function() {
    const initialTokensBalance = BigInt(await token.balanceOf(accounts[2]));
    const tokensToDecrease = BigInt(5);

    await market.decreaseSellPositionAmount(token.address, tokensToDecrease, {
      from: accounts[2]
    });

    assert.equal(
      await token.balanceOf(accounts[2]),
      initialTokensBalance + tokensToDecrease
    );
  });

  it("Fail to purchase from nonexistent sell position", async function() {
    await expectRevert(
      market.purchase(
        token.address,
        accounts[1],
        BigInt(5),
        BigInt(60) * oneDai,
        marketFeeAttoDaiPerNanoDai,
        { from: accounts[3] }
      ),
      "sell position does not exist"
    );
  });

  it("Fail to purchase from sell position with mismatching price", async function() {
    await expectRevert(
      market.purchase(
        token.address,
        accounts[2],
        BigInt(5),
        BigInt(50) * oneDai,
        marketFeeAttoDaiPerNanoDai,
        { from: accounts[3] }
      ),
      "_priceAttoDaiPerToken does not match the current price"
    );
  });

  it("Fail to purchase an amount greater than offered by a sell position", async function() {
    await expectRevert(
      market.purchase(
        token.address,
        accounts[2],
        BigInt(100),
        BigInt(60) * oneDai,
        marketFeeAttoDaiPerNanoDai,
        { from: accounts[3] }
      ),
      "_amountTokens exceeds amount for sale"
    );
  });

  const tokensToPurchase = BigInt(5);

  it("Purchase from a sell position", async function() {
    const initialSellerAttoDai = toBigInt(await daiMock.balanceOf(accounts[2]));
    const initialBuyerAttoDai = toBigInt(await daiMock.balanceOf(accounts[3]));

    const priceAttoDaiPerToken = BigInt(60) * oneDai;

    await market.purchase(
      token.address,
      accounts[2],
      tokensToPurchase,
      priceAttoDaiPerToken,
      marketFeeAttoDaiPerNanoDai,
      { from: accounts[3] }
    );

    assert.equal(
      await daiMock.balanceOf(accounts[2]),
      initialSellerAttoDai + priceAttoDaiPerToken * tokensToPurchase
    );

    assert.equal(
      await daiMock.balanceOf(accounts[3]),
      initialBuyerAttoDai -
        priceAttoDaiPerToken * tokensToPurchase -
        marketFeeAttoDaiPerNanoDai *
          (priceAttoDaiPerToken / oneNanoDai) *
          tokensToPurchase
    );

    assert.equal(await token.balanceOf(accounts[3]), tokensToPurchase);
  });

  it("Fail to remove nonexistent sell position", async function() {
    await expectRevert(
      market.removeSellPosition(token.address, { from: accounts[1] }),
      "sell position does not exist"
    );
  });

  it("Remove sell position", async function() {
    await market.removeSellPosition(token.address, { from: accounts[2] });

    assert.equal(
      await token.balanceOf(accounts[2]),
      requestedValueAttoDai / oneDai - tokensToPurchase
    );
  });
});

/* -------------------------------------------------------------------------- */
