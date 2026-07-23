import { describe, it, expect } from "vitest";
import { rollingAverage } from "./rollingAverage";

describe("rollingAverage", () => {
  it("returns empty array for empty input", () => {
    expect(rollingAverage([], 3)).toEqual([]);
  });

  it("window=1 is the identity function", () => {
    expect(rollingAverage([2, 5, 8], 1)).toEqual([2, 5, 8]);
  });

  it("computes correct 3-window average", () => {
    // [2], [2,8], [2,8,5] → 2, 5, 5
    const result = rollingAverage([2, 8, 5], 3);
    expect(result).toEqual([2, 5, 5]);
  });

  it("handles window larger than array length", () => {
    // averages over whatever is available
    const result = rollingAverage([4, 6], 10);
    expect(result).toEqual([4, 5]);
  });

  it("rounds to 2 decimal places", () => {
    const result = rollingAverage([1, 2, 3], 3);
    // [1], [1,2], [1,2,3] → 1, 1.5, 2
    expect(result).toEqual([1, 1.5, 2]);
  });

  it("single element array returns that element", () => {
    expect(rollingAverage([7], 3)).toEqual([7]);
  });

  it("throws for window <= 0", () => {
    expect(() => rollingAverage([1, 2], 0)).toThrow(RangeError);
  });
});
