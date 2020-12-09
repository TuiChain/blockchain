/* -------------------------------------------------------------------------- */

const TuiChainController = artifacts.require("TuiChainController");
const TuiChainMarket = artifacts.require("TuiChainMarket");
const TuiChainLoan = artifacts.require("TuiChainLoan");
const TuiChainToken = artifacts.require("TuiChainToken");

const DaiMock = artifacts.require("DaiMock");

const {
    constants, // Common constants, like the zero address and largest integers
    expectRevert // Assertions for transactions that should fail
} = require("@openzeppelin/test-helpers");

// Mocks an ENUM identical to the one in the TuiChainLoan
const Phase = Object.freeze({
    Funding: 0,
    Expired: 1,
    Canceled: 2,
    Active: 3,
    Finalized: 4
});

/* -------------------------------------------------------------------------- */

// Sequence of tests for the Marketplace Contract
// This tests represent possible interactions from the backend with marketplace contract
contract("Marketplace", function(accounts) {
    // market fee, is equivalent to 10% of a DAI
    const marketFeeAttoDaiPerNanoDai = BigInt(10) ** BigInt(8);

    /* -------------------------------------------------------------------------- */

    // variable which represents the deployed DAI mock
    let daiMock = null;

    // variable which represents the deployed controller contract
    let tuiChainController = null;

    // variable which represents the deployed market contract
    let tuiChainMarket = null;

    // variable which represents the a deployed loan contract
    let tuiChainLoan = null;

    // variable which represents the loan object
    let loanObject = null;

    // variable which represents the funds provided from account 3, also represent the amount of TuiChainTokens received
    let providedFunds = null;

    /* -------------------------------------------------------------------------- */

    // runs once before the first test
    before(async () => {
        // deploy contract which mocks DAI contract
        daiMock = await DaiMock.new();

        // loan specs
        loanObject = {
            _feeRecipient: accounts[0],
            _loanRecipient: accounts[1],
            _secondsToExpiration: 60, // 1 minute
            _fundingFeeAttoDaiPerDai: BigInt(10) ** BigInt(17), // 10% fee
            _paymentFeeAttoDaiPerDai: BigInt(10) ** BigInt(17), // 10% fee
            _requestedValueAttoDai: BigInt(1000) * BigInt(10) ** BigInt(18) // 1000 DAI
        };

        // deploy controller contract
        tuiChainController = await TuiChainController.new(
            daiMock.address,
            accounts[0],
            marketFeeAttoDaiPerNanoDai
        );

        // get loan contract from an address with at() function
        const transaction = await tuiChainController.createLoan(
            ...Object.values(loanObject)
        );
        tuiChainLoan = await TuiChainLoan.at(transaction.logs[0].address);

        // get marketplace contract from an address with at() function
        tuiChainMarket = await TuiChainMarket.at(
            await tuiChainController.market()
        );

        // get token  contract from an address with at() functions
        tuiChainToken = await TuiChainToken.at(await tuiChainLoan.token());

        // start every account with 1200 DAI
        accounts.forEach(account => {
            daiMock.mint(account, BigInt(1200) * BigInt(10) ** BigInt(18));
        });

        // Allows tokens to be transfer to our contracts
        providedFunds = 1000;
        await daiMock.increaseAllowance(
            tuiChainLoan.address,
            BigInt(1200) * BigInt(10) ** BigInt(18),
            { from: accounts[2] }
        );
        await daiMock.increaseAllowance(
            tuiChainMarket.address,
            BigInt(1200) * BigInt(10) ** BigInt(18),
            { from: accounts[3] }
        );
        await tuiChainToken.increaseAllowance(
            tuiChainMarket.address,
            providedFunds,
            { from: accounts[2] }
        );

        // account 3 funds the loan
        await tuiChainLoan.provideFunds(
            BigInt(providedFunds) * BigInt(10) ** BigInt(18),
            { from: accounts[2] }
        );
    });

    /* -------------------------------------------------------------------------- */

    it("Fails to create a sell position with an amount greater than the balance", async function() {
        const tokensToSell = 1050;
        const priceToSell = BigInt(55) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.createSellPosition(
                tuiChainToken.address,
                tokensToSell,
                priceToSell,
                { from: accounts[2] }
            )
        );
    });

    it("Fails to create a sell position with an amount smaller than the 0", async function() {
        const tokensToSell = -1;
        const priceToSell = BigInt(55) * BigInt(10) ** BigInt(18);

        try {
            await tuiChainMarket.createSellPosition(
                tuiChainToken.address,
                tokensToSell,
                priceToSell,
                { from: accounts[2] }
            );
        } catch (error) {
            return assert(error.message);
        }

        return assert(false);
    });

    it("Fails to create a sell position for a not allowed token", async function() {
        const tokensToSell = 1050;
        const priceToSell = BigInt(55) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.createSellPosition(
                daiMock.address,
                tokensToSell,
                priceToSell,
                { from: accounts[2] }
            )
        );
    });

    it("Creates sell position", async function() {
        const tokensToSell = 50;
        const priceToSell = BigInt(55) * BigInt(10) ** BigInt(18);
        const initialTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        await tuiChainMarket.createSellPosition(
            tuiChainToken.address,
            tokensToSell,
            priceToSell,
            { from: accounts[2] }
        );
        const finalTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        assert(finalTokensBalance == initialTokensBalance - tokensToSell);
    });

    it("Fails to update a non-existent sell position price", async function() {
        const updatePrice = BigInt(60) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.updateSellPositionPrice(
                tuiChainToken.address,
                updatePrice,
                { from: accounts[1] }
            )
        );
    });

    it("Updates a existent sell position price", async function() {
        const updatePrice = BigInt(60) * BigInt(10) ** BigInt(18);
        await tuiChainMarket.updateSellPositionPrice(
            tuiChainToken.address,
            updatePrice,
            { from: accounts[2] }
        );

        assert(true);
    });

    it("Fails to creates duplicated sell position", async function() {
        const tokensToSell = 50;
        const priceToSell = BigInt(55) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.createSellPosition(
                tuiChainToken.address,
                tokensToSell,
                priceToSell,
                { from: accounts[2] }
            )
        );
    });

    it("Fails to increase the amount of a non-existent sell position", async function() {
        await expectRevert.unspecified(
            tuiChainMarket.increaseSellPositionAmount(
                tuiChainToken.address,
                1,
                { from: accounts[1] }
            )
        );
    });

    it("Increases the amount of a sell position", async function() {
        const tokensToIncrease = 5;
        const initialTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        await tuiChainMarket.increaseSellPositionAmount(
            tuiChainToken.address,
            tokensToIncrease,
            { from: accounts[2] }
        );
        const finalTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        assert(finalTokensBalance == initialTokensBalance - tokensToIncrease);
    });

    it("Fails to decrease the amount of a non-existent sell position", async function() {
        await expectRevert.unspecified(
            tuiChainMarket.decreaseSellPositionAmount(
                tuiChainToken.address,
                1,
                { from: accounts[1] }
            )
        );
    });

    it("Fails to decrease the amount of a sell position to a negative value", async function() {
        await expectRevert.unspecified(
            tuiChainMarket.decreaseSellPositionAmount(
                tuiChainToken.address,
                100,
                { from: accounts[2] }
            )
        );
    });

    it("Decreases the amount of a sell position", async function() {
        const tokensToDecrease = 5;
        const initialTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        await tuiChainMarket.decreaseSellPositionAmount(
            tuiChainToken.address,
            tokensToDecrease,
            { from: accounts[2] }
        );
        const finalTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        assert(finalTokensBalance == initialTokensBalance + tokensToDecrease);
    });

    it("Fails to buy from non-existent sell position", async function() {
        const tokensToBuy = 5;
        const buyPrice = BigInt(60) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.purchase(
                tuiChainToken.address,
                accounts[1],
                tokensToBuy,
                buyPrice,
                marketFeeAttoDaiPerNanoDai,
                { from: accounts[3] }
            )
        );
    });

    it("Fails to buy from existent sell position with a different price", async function() {
        tokensToBuy = 5;
        const buyPrice = BigInt(50) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.purchase(
                tuiChainToken.address,
                accounts[2],
                tokensToBuy,
                buyPrice,
                marketFeeAttoDaiPerNanoDai,
                { from: accounts[3] }
            )
        );
    });

    it("Fails to buy an amount greater than the available from existent sell position", async function() {
        tokensToBuy = 100;
        const buyPrice = BigInt(60) * BigInt(10) ** BigInt(18);

        await expectRevert.unspecified(
            tuiChainMarket.purchase(
                tuiChainToken.address,
                accounts[2],
                tokensToBuy,
                buyPrice,
                marketFeeAttoDaiPerNanoDai,
                { from: accounts[3] }
            )
        );
    });

    // represents the amount of tokens that the account 4 wil buy from 2 (necessary for other test)
    let tokensToBuy = null;
    it("Buys from existent sell position", async function() {
        tokensToBuy = 5;
        const buyPrice = BigInt(60) * BigInt(10) ** BigInt(18);

        await tuiChainMarket.purchase(
            tuiChainToken.address,
            accounts[2],
            tokensToBuy,
            buyPrice,
            marketFeeAttoDaiPerNanoDai,
            { from: accounts[3] }
        );
        const finalTokensBalance = (
            await tuiChainToken.balanceOf(accounts[3])
        ).toNumber();

        assert(finalTokensBalance == tokensToBuy);
    });

    it("Fails to remove non-existent sell position", async function() {
        await expectRevert.unspecified(
            tuiChainMarket.removeSellPosition(tuiChainToken.address, {
                from: accounts[1]
            })
        );
    });

    it("Removes existent sell position", async function() {
        await tuiChainMarket.removeSellPosition(tuiChainToken.address, {
            from: accounts[2]
        });
        const finalTokensBalance = (
            await tuiChainToken.balanceOf(accounts[2])
        ).toNumber();

        assert(finalTokensBalance == providedFunds - tokensToBuy);
    });
});
