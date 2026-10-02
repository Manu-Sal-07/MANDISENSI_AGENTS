'use client';

/**
 * How accurate are we — the whole record, including where we are not good.
 *
 * Every figure comes from `models/farmer/model_report.json`, written by the
 * farmer build from walk-forward tests: the model is fitted on the past, scored
 * on the weeks after it, and moved forward, four times. Nothing here is measured
 * on data the model trained on.
 */

import PageHero from '@/components/farm/PageHero';
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Check, Minus, Target } from 'lucide-react';

import ProduceIcon, { produceScript, resolveProduce } from '@/components/farm/ProduceIcon';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { placeName, tri } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';

const pct = (v: number | null | undefined, digits = 0) => (v == null ? '—' : `${(v * 100).toFixed(digits)}`);

export default function AccuracyPage() {
  const { lang } = useLanguage();
  const { catalog } = useFarm();
  const { data, isLoading } = useQuery({ queryKey: ['farm-accuracy'], queryFn: () => farmerApi.accuracy() });

  if (isLoading) return <div className="farm-surface min-h-screen" />;
  if (!data?.available || !data.overall) {
    return (
      <div className="farm-surface min-h-screen px-4 pt-10">
        <p className="mx-auto max-w-xl text-[var(--farm-ink-soft)]">{tri(lang, 'The accuracy record is not available yet.', 'ನಿಖರತೆಯ ದಾಖಲೆ ಇನ್ನೂ ಲಭ್ಯವಿಲ್ಲ.', 'सटीकता का रिकॉर्ड अभी उपलब्ध नहीं है।')}</p>
      </div>
    );
  }

  const horizons = Object.entries(data.horizons ?? {}).filter(([, h]) => h.promoted);
  const cover = horizons.length ? horizons.reduce((s, [, h]) => s + (h.coverage_90 ?? 0), 0) / horizons.length : null;
  const series = Object.entries(data.series_quality ?? {}).sort((a, b) => b[1].skill_vs_no_change - a[1].skill_vs_no_change);

  const nameOf = (key: string) => {
    const [crop, place] = key.split('/');
    const d = catalog?.districts.find((x) => x.id === place);
    return { crop, place: d ? placeName(d, lang) : place };
  };

  const facts = [
    { n: pct(data.overall.direction_right), u: '/100', t: tri(lang, 'times we read the direction of the price right', 'ಬಾರಿ ಬೆಲೆಯ ದಿಕ್ಕನ್ನು ಸರಿಯಾಗಿ ಹೇಳಿದ್ದೇವೆ', 'बार हमने भाव की दिशा सही बताई') },
    { n: pct(cover), u: '/100', t: tri(lang, 'times the real price landed inside our 90% range', 'ಬಾರಿ ನಿಜವಾದ ಬೆಲೆ ನಮ್ಮ 90% ಶ್ರೇಣಿಯೊಳಗೆ ಬಂತು', 'बार असली भाव हमारे 90% दायरे के भीतर रहा') },
    { n: `${(data.overall.skill_vs_no_change * 100).toFixed(1)}%`, u: '', t: tri(lang, 'smaller miss than assuming “the price will not change”', 'ಕಡಿಮೆ ತಪ್ಪು — “ಬೆಲೆ ಬದಲಾಗುವುದಿಲ್ಲ” ಎಂದು ಊಹಿಸುವುದಕ್ಕಿಂತ', 'कम गलती — “भाव नहीं बदलेगा” मान लेने से') },
  ];

  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-2xl px-4 pb-10 pt-7 lg:max-w-3xl">
        <PageHero photo="vendor-stall" title={tri(lang, 'How accurate are we?', 'ನಾವು ಎಷ್ಟು ನಿಖರ?', 'हम कितने सटीक हैं?')} icon={<Target className="h-7 w-7" />} produce={['tomato', 'onion', 'potato']} />
        <p className="mt-2 max-w-[60ch] text-[15px] leading-relaxed text-[var(--farm-ink-soft)]">
          {tri(
            lang,
            `Tested on ${data.overall.forecasts.toLocaleString('en-IN')} forecasts for weeks the model had never seen, between ${data.data?.from} and ${data.data?.to}.`,
            `ಮಾದರಿ ಹಿಂದೆಂದೂ ನೋಡದ ವಾರಗಳ ${data.overall.forecasts.toLocaleString('en-IN')} ಮುನ್ಸೂಚನೆಗಳ ಮೇಲೆ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ (${data.data?.from} ರಿಂದ ${data.data?.to}).`,
            `मॉडल ने जो हफ़्ते कभी नहीं देखे, उनके ${data.overall.forecasts.toLocaleString('en-IN')} पूर्वानुमानों पर जाँचा गया (${data.data?.from} से ${data.data?.to})।`
          )}
        </p>

        <ul className="mt-6 grid gap-3 sm:grid-cols-3">
          {facts.map((f) => (
            <li key={f.t} className="farm-row p-4">
              <p className="farm-display text-4xl tabular-nums text-[var(--leaf-deep)]">{f.n}<span className="text-xl text-[var(--farm-ink-faint)]">{f.u}</span></p>
              <p className="mt-1 text-sm leading-snug text-[var(--farm-ink-soft)]">{f.t}</p>
            </li>
          ))}
        </ul>

        <section className="farm-section mt-8">
          <h2 className="farm-display text-xl text-[var(--farm-ink)]">{tri(lang, 'Which crops can you trust?', 'ಯಾವ ಬೆಳೆಗಳನ್ನು ನಂಬಬಹುದು?', 'किन फसलों पर भरोसा करें?')}</h2>
          <p className="mb-4 mt-1 text-sm text-[var(--farm-ink-faint)]">
            {tri(
              lang,
              'We give a sell-or-hold call only where our gain over “no change” passes a statistical test that allows for having checked every crop and district.',
              'ಎಲ್ಲಾ ಬೆಳೆ-ಜಿಲ್ಲೆಗಳನ್ನು ಪರೀಕ್ಷಿಸಿದ್ದನ್ನು ಪರಿಗಣಿಸಿಯೂ, “ಬದಲಾವಣೆ ಇಲ್ಲ” ಎಂಬುದಕ್ಕಿಂತ ನಮ್ಮ ಲಾಭ ಸಾಂಖ್ಯಿಕ ಪರೀಕ್ಷೆಯಲ್ಲಿ ಗಟ್ಟಿಯಾಗಿ ನಿಂತಲ್ಲಿ ಮಾತ್ರ ಮಾರುವ/ಇಡುವ ಸಲಹೆ ನೀಡುತ್ತೇವೆ.',
              'हम बेचें/रोकें सलाह तभी देते हैं जब “कोई बदलाव नहीं” पर हमारा लाभ उस सांख्यिकीय परीक्षण में टिके जो सभी फसल-ज़िलों की जाँच को ध्यान में रखता है।'
            )}
          </p>
          <ul className="divide-y divide-[var(--farm-line)]">
            {series.map(([key, q], i) => {
              const { crop, place } = nameOf(key);
              const right = (q.direction_right ?? 0) * 100;
              return (
                <li key={key} className="py-3">
                  <div className="flex items-center gap-3">
                    <ProduceIcon name={crop} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-[var(--farm-ink)]">{produceScript(resolveProduce(crop), lang).text} · {place}</p>
                      <div className="relative mt-1.5 h-2 rounded-full bg-[var(--farm-line)]">
                        <motion.span
                          className="absolute inset-y-0 left-0 rounded-full"
                          style={{ background: q.serves_call ? 'var(--leaf)' : 'var(--farm-ink-faint)' }}
                          initial={{ width: 0 }}
                          animate={{ width: `${right}%` }}
                          transition={{ delay: 0.1 + i * 0.03, duration: 0.6 }}
                        />
                        <span className="absolute -top-1 h-4 w-0.5 bg-[var(--farm-ink)]" style={{ left: '50%' }} aria-hidden="true" />
                      </div>
                    </div>
                    <div className="w-[7.5rem] shrink-0 text-right">
                      <p className="text-sm font-bold tabular-nums text-[var(--farm-ink)]">{right.toFixed(0)}/100</p>
                      <p className="flex items-center justify-end gap-1 text-[11px] font-bold" style={{ color: q.serves_call ? 'var(--leaf-deep)' : 'var(--farm-ink-faint)' }}>
                        {q.serves_call ? <Check className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
                        {q.serves_call ? tri(lang, 'Gives calls', 'ಸಲಹೆ ಕೊಡುತ್ತೇವೆ', 'सलाह देते हैं') : tri(lang, 'Price and range', 'ಬೆಲೆ ಮತ್ತು ಶ್ರೇಣಿ', 'भाव और दायरा')}
                      </p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-[var(--farm-ink-faint)]">{tri(lang, 'The vertical tick marks 50: a coin toss.', 'ನೇರ ಗೆರೆ 50 ಅನ್ನು ಸೂಚಿಸುತ್ತದೆ: ಚಿಮ್ಮಿ ಹಾಕಿದಂತೆ.', 'खड़ी रेखा 50 दिखाती है: सिक्का उछालने जैसा।')}</p>
        </section>

        <section className="farm-section farm-section-warm mt-6">
          <h2 className="farm-display text-xl text-[var(--farm-ink)]">{tri(lang, 'What we do not know', 'ನಮಗೆ ಗೊತ್ತಿಲ್ಲದ್ದು', 'जो हम नहीं जानते')}</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-[var(--farm-ink)]">
            <li>{tri(lang, 'Rain, festivals, strikes and government orders move prices in ways no past record shows.', 'ಮಳೆ, ಹಬ್ಬ, ಮುಷ್ಕರ, ಸರ್ಕಾರಿ ಆದೇಶಗಳು ಹಿಂದಿನ ದಾಖಲೆ ತೋರಿಸದ ರೀತಿಯಲ್ಲಿ ಬೆಲೆ ಬದಲಿಸುತ್ತವೆ.', 'बारिश, त्योहार, हड़ताल और सरकारी आदेश भाव को ऐसे बदलते हैं जो पुराने रिकॉर्ड में नहीं दिखता।')}</li>
            <li>{tri(lang, 'Tomato prices swing so much that our likely range is wide. That is the honest size of the uncertainty, not a flaw in the drawing.', 'ಟೊಮೇಟೊ ಬೆಲೆ ಬಹಳ ಏರಿಳಿಯುವುದರಿಂದ ನಮ್ಮ ಶ್ರೇಣಿ ಅಗಲವಾಗಿದೆ. ಇದು ಅನಿಶ್ಚಿತತೆಯ ನಿಜವಾದ ಗಾತ್ರ.', 'टमाटर के भाव इतना उछलते हैं कि हमारा दायरा चौड़ा है। यह अनिश्चितता का सही आकार है, चित्र की कमी नहीं।')}</li>
            <li>{tri(lang, 'We chose which crops get calls using these same test weeks, so the per-crop figures above are a little flattering. The overall figures are not affected by that choice.', 'ಯಾವ ಬೆಳೆಗೆ ಸಲಹೆ ಕೊಡಬೇಕೆಂದು ಇದೇ ಪರೀಕ್ಷಾ ವಾರಗಳನ್ನು ಬಳಸಿ ನಿರ್ಧರಿಸಿದ್ದೇವೆ, ಆದ್ದರಿಂದ ಮೇಲಿನ ಬೆಳೆವಾರು ಅಂಕಿಗಳು ಸ್ವಲ್ಪ ಹೆಚ್ಚು ಒಳ್ಳೆಯದಾಗಿ ಕಾಣುತ್ತವೆ.', 'किन फसलों को सलाह मिले, यह इन्हीं परीक्षण हफ़्तों से तय किया गया, इसलिए ऊपर के फसलवार आँकड़े थोड़े बेहतर दिखते हैं।')}</li>
            <li>{tri(lang, 'A one-day-ahead forecast was no better than assuming no change, so we do not offer one.', 'ಒಂದು ದಿನದ ಮುನ್ಸೂಚನೆ “ಬದಲಾವಣೆ ಇಲ್ಲ” ಎನ್ನುವುದಕ್ಕಿಂತ ಉತ್ತಮವಾಗಿರಲಿಲ್ಲ, ಆದ್ದರಿಂದ ನೀಡುವುದಿಲ್ಲ.', 'एक दिन आगे का पूर्वानुमान “कोई बदलाव नहीं” से बेहतर नहीं था, इसलिए हम नहीं देते।')}</li>
          </ul>
        </section>

        {data.data && (
          <p className="mt-6 text-center text-xs text-[var(--farm-ink-faint)]">
            {tri(lang, 'Data', 'ದತ್ತಾಂಶ', 'डेटा')}: {data.data.source} · {data.data.series} {tri(lang, 'crop-district series', 'ಬೆಳೆ-ಜಿಲ್ಲೆ ಸರಣಿ', 'फसल-ज़िला श्रृंखला')} · {data.data.rows.toLocaleString('en-IN')} {tri(lang, 'daily prices', 'ದೈನಂದಿನ ಬೆಲೆಗಳು', 'दैनिक भाव')} · {data.data.from} → {data.data.to}
          </p>
        )}
      </main>
    </div>
  );
}
