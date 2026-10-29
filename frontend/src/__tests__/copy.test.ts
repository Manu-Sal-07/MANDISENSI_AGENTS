import { describe, expect, it } from 'vitest';
import { dayLabel, mc } from '@/lib/i18n/marketChoiceCopy';
import { sc } from '@/lib/i18n/shockCopy';

const LANGS = ['en', 'kn', 'hi'] as const;

describe('farmer copy', () => {
  it('fills placeholders and leaves none behind', () => {
    expect(mc('sure.value', 'en', { n: 9 })).toBe('9 out of 10 times');
    for (const l of LANGS) expect(mc('sure.value', l, { n: 9 })).not.toMatch(/\{\w+\}/);
  });

  it('falls back to the key when a string is missing rather than rendering nothing', () => {
    expect(mc('no.such.key', 'kn')).toBe('no.such.key');
    expect(sc('no.such.key', 'hi')).toBe('no.such.key');
  });

  it('has a Kannada and a Hindi string for every English supply-watch label', () => {
    const keys = ['watch.title', 'watch.glut', 'watch.squeeze', 'watch.normal', 'watch.noclaim', 'why.title', 'why.cautions'];
    for (const k of keys) for (const l of ['kn', 'hi'] as const) expect(sc(k, l)).not.toBe(sc(k, 'en'));
  });

  it('never claims a price effect in the default supply-watch notice', () => {
    for (const l of LANGS) expect(sc('watch.noclaim', l)).not.toMatch(/\d/);
  });

  it('labels hold days in each language', () => {
    for (const l of LANGS) {
      expect(dayLabel(0, l)).toBe(mc('day.today', l));
      expect(dayLabel(2, l)).toContain('2');
    }
  });
});
