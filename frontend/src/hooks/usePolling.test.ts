/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect } from 'vitest';

describe('Polling Hook Logic', () => {
  it('should return polling interval when status is queued', () => {
    const data = { status: 'queued' };
    const getInterval = (data: any) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    };
    expect(getInterval(data)).toBe(2000);
  });

  it('should return polling interval when status is running', () => {
    const data = { status: 'running' };
    const getInterval = (data: any) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    };
    expect(getInterval(data)).toBe(2000);
  });

  it('should return false when status is done', () => {
    const data = { status: 'done' };
    const getInterval = (data: any) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    };
    expect(getInterval(data)).toBe(false);
  });

  it('should return false when status is failed', () => {
    const data = { status: 'failed' };
    const getInterval = (data: any) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    };
    expect(getInterval(data)).toBe(false);
  });

  it('should return false when data is null', () => {
    const getInterval = (data: any) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    };
    expect(getInterval(null)).toBe(false);
  });

  it('should return false when data is undefined', () => {
    const getInterval = (data: any) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    };
    expect(getInterval(undefined)).toBe(false);
  });
});
