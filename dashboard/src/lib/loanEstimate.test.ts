import { describe, expect, it } from 'vitest';
import { calculateEmi, calculateProposedFoir } from './loanEstimate';

describe('borrower loan estimate helpers', () => {
  it('calculates the illustrative EMI at the configured annual rate', () => {
    expect(calculateEmi(150000, 24)).toBe(7096);
  });

  it('handles a zero-interest estimate', () => {
    expect(calculateEmi(12000, 12, 0)).toBe(1000);
  });

  it('rejects invalid principal and tenure', () => {
    expect(calculateEmi(0, 12)).toBe(0);
    expect(calculateEmi(1000, 0)).toBe(0);
  });

  it('adds estimated EMI-to-income ratio to existing FOIR', () => {
    expect(calculateProposedFoir(50000, 30, 10000)).toBe(50);
  });

  it('returns unavailable when income is zero or invalid', () => {
    expect(calculateProposedFoir(0, 30, 10000)).toBeNull();
    expect(calculateProposedFoir(50000, 30, -1)).toBeNull();
  });
});
