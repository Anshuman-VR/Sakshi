/** Illustrative calculations for the borrower preview only; not lender policy. */
export function calculateEmi(amount: number, tenureMonths: number, annualRate = 0.125): number {
  if (!Number.isFinite(amount) || amount <= 0 || !Number.isFinite(tenureMonths) || tenureMonths <= 0) return 0;
  const monthlyRate = annualRate / 12;
  if (monthlyRate === 0) return Math.round(amount / tenureMonths);
  const factor = Math.pow(1 + monthlyRate, tenureMonths);
  return Math.round(amount * monthlyRate * factor / (factor - 1));
}

export function calculateProposedFoir(income: number, existingFoir: number, emi: number): number | null {
  if (!Number.isFinite(income) || income <= 0 || !Number.isFinite(existingFoir) || !Number.isFinite(emi) || emi < 0) return null;
  return existingFoir + (emi / income) * 100;
}
