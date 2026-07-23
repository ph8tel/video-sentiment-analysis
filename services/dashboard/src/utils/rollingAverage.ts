/**
 * Compute a rolling average over an array of numbers.
 *
 * Each output value is the mean of up to `window` preceding values
 * (inclusive). Exported separately so it can be unit-tested without
 * mounting any component.
 */
export function rollingAverage(scores: number[], window: number): number[] {
  if (window <= 0) throw new RangeError("window must be > 0");
  return scores.map((_, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = scores.slice(start, i + 1);
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
    return parseFloat(mean.toFixed(2));
  });
}
