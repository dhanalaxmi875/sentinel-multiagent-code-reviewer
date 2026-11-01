import { describe, expect, it } from 'vitest';
import { pollingInterval } from '../utils/filterLogic';

describe('Polling hook interval policy', () => {
  it('polls queued and running reviews', () => {
    expect(pollingInterval('queued')).toBe(2000);
    expect(pollingInterval('running')).toBe(2000);
  });
  it('stops polling terminal or missing reviews', () => {
    expect(pollingInterval('done')).toBe(false);
    expect(pollingInterval('failed')).toBe(false);
    expect(pollingInterval(undefined)).toBe(false);
  });
});
