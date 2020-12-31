/* -------------------------------------------------------------------------- */

function toBigInt(bn) {
  return BigInt(bn.toString());
}

const oneDai = BigInt(10) ** BigInt(18);
const oneNanoDai = BigInt(10) ** BigInt(9);
const oneAttoDai = BigInt(1);

// replicates the TuiChainLoan.Phase enumeration
const LoanPhase = Object.freeze({
  Funding: "0",
  Expired: "1",
  Canceled: "2",
  Active: "3",
  Finalized: "4"
});

/* -------------------------------------------------------------------------- */

module.exports = { toBigInt, oneDai, oneNanoDai, oneAttoDai, LoanPhase };

/* -------------------------------------------------------------------------- */
