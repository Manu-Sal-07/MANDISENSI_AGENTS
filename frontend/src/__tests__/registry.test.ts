import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { TRADER_TOOLS, toolBySlug } from '@/lib/traderTools';

describe('trader tool registry', () => {
  it('has unique slugs and hrefs', () => {
    expect(new Set(TRADER_TOOLS.map((t) => t.slug)).size).toBe(TRADER_TOOLS.length);
    expect(new Set(TRADER_TOOLS.map((t) => t.href)).size).toBe(TRADER_TOOLS.length);
  });

  it('points every tool at a page that exists', () => {
    for (const t of TRADER_TOOLS) {
      expect(t.href).toBe(`/trader-tools/${t.slug}`);
      expect(existsSync(path.resolve(__dirname, '..', 'app', 'trader-tools', t.slug, 'page.tsx'))).toBe(true);
    }
  });

  it('has a page for no tool the registry does not list', () => {
    const dir = path.resolve(__dirname, '..', 'app', 'trader-tools');
    const pages = readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name);
    for (const p of pages) expect(toolBySlug(p), `page /trader-tools/${p} is missing from the registry`).toBeDefined();
  });

  it('describes every tool', () => {
    for (const t of TRADER_TOOLS) {
      expect(t.title.length).toBeGreaterThan(3);
      expect(t.blurb.length).toBeGreaterThan(20);
    }
  });
});
