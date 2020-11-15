const DebtToken = artifacts.require("DebtToken");

contract("DebtToken", function (accounts) {
  it("should assert true", async function () {
    await DebtToken.deployed();
    return assert.isTrue(true);
  });
});
