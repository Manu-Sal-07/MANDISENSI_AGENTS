/**
 * Words for the farmer app's data screens, in the three languages it serves.
 *
 * The API returns structured reasons (a code and its numbers) rather than
 * sentences, so this file is the only place a sentence is composed. Templates
 * use `{n}` style slots; `say()` fills them. Anything missing in a language
 * falls back to English rather than showing a key.
 */

import type { Lang } from './translations';
import type { CatalogDistrict, FarmReason, PlaceNames } from '@/services/farmerApi';

type Entry = Record<Lang, string>;

const COPY: Record<string, Entry> = {
  'home.ask': { en: 'What is your crop worth today?', kn: 'ಇಂದು ನಿಮ್ಮ ಬೆಳೆಗೆ ಎಷ್ಟು ಬೆಲೆ?', hi: 'आज आपकी फसल का भाव क्या है?' },
  'unit.qtl': { en: 'per quintal', kn: 'ಕ್ವಿಂಟಾಲ್‌ಗೆ', hi: 'प्रति क्विंटल' },
  'asof': { en: 'Prices as of {d}', kn: '{d}ರ ಬೆಲೆಗಳು', hi: '{d} तक के भाव' },
  'change.day': { en: 'since yesterday', kn: 'ನಿನ್ನೆಯಿಂದ', hi: 'कल से' },
  'change.week': { en: 'this week', kn: 'ಈ ವಾರ', hi: 'इस हफ़्ते' },
  'change.month': { en: 'this month', kn: 'ಈ ತಿಂಗಳು', hi: 'इस महीने' },

  'call.sell': { en: 'Sell now', kn: 'ಈಗಲೇ ಮಾರಿ', hi: 'अभी बेचें' },
  'call.hold': { en: 'Hold', kn: 'ಇಡಿ', hi: 'रोकें' },
  'call.wait': { en: 'No clear move', kn: 'ಸ್ಪಷ್ಟ ಸೂಚನೆ ಇಲ್ಲ', hi: 'साफ़ संकेत नहीं' },
  'call.range': { en: 'Price and range', kn: 'ಬೆಲೆ ಮತ್ತು ಶ್ರೇಣಿ', hi: 'भाव और दायरा' },
  'call.sell.why': {
    en: 'Prices are likely to ease over the next {n} days.',
    kn: 'ಮುಂದಿನ {n} ದಿನಗಳಲ್ಲಿ ಬೆಲೆ ಇಳಿಯುವ ಸಾಧ್ಯತೆ ಇದೆ.',
    hi: 'अगले {n} दिनों में भाव गिर सकते हैं।',
  },
  'call.hold.why': {
    en: 'Prices are likely to firm up over the next {n} days.',
    kn: 'ಮುಂದಿನ {n} ದಿನಗಳಲ್ಲಿ ಬೆಲೆ ಏರುವ ಸಾಧ್ಯತೆ ಇದೆ.',
    hi: 'अगले {n} दिनों में भाव बढ़ सकते हैं।',
  },
  'call.wait.why': {
    en: 'The next {n} days look close to today. No reason to rush.',
    kn: 'ಮುಂದಿನ {n} ದಿನ ಬೆಲೆ ಇಂದಿನಂತೆಯೇ ಇರುವ ಸಾಧ್ಯತೆ. ಆತುರ ಬೇಡ.',
    hi: 'अगले {n} दिन भाव आज जैसे ही रहेंगे। जल्दी की ज़रूरत नहीं।',
  },
  'call.range.why': {
    en: 'We have not yet proven a dependable sell-or-hold call for {crop} here, so we show the price and the likely range instead.',
    kn: 'ಇಲ್ಲಿ {crop}ಗೆ ನಂಬಲರ್ಹ ಮಾರುವ-ಅಥವಾ-ಇಡುವ ಸಲಹೆಯನ್ನು ಇನ್ನೂ ಸಾಬೀತುಪಡಿಸಿಲ್ಲ; ಆದ್ದರಿಂದ ಬೆಲೆ ಮತ್ತು ಸಂಭವನೀಯ ಶ್ರೇಣಿಯನ್ನು ತೋರಿಸುತ್ತೇವೆ.',
    hi: 'यहाँ {crop} के लिए हमने अभी भरोसेमंद बेचें-या-रोकें सलाह साबित नहीं की है, इसलिए भाव और संभावित दायरा दिखा रहे हैं।',
  },
  'call.none.why': { en: 'No forecast is available for this crop yet.', kn: 'ಈ ಬೆಳೆಗೆ ಇನ್ನೂ ಮುನ್ಸೂಚನೆ ಲಭ್ಯವಿಲ್ಲ.', hi: 'इस फसल का पूर्वानुमान अभी उपलब्ध नहीं है।' },

  'reason.price_up_week': { en: 'Price is up {n}% this week', kn: 'ಈ ವಾರ ಬೆಲೆ {n}% ಏರಿದೆ', hi: 'इस हफ़्ते भाव {n}% बढ़ा' },
  'reason.price_down_week': { en: 'Price is down {n}% this week', kn: 'ಈ ವಾರ ಬೆಲೆ {n}% ಇಳಿದಿದೆ', hi: 'इस हफ़्ते भाव {n}% गिरा' },
  'reason.arrivals_high': { en: 'Arrivals are {n}% above normal', kn: 'ಮಾರುಕಟ್ಟೆಗೆ ಬರುವ ಮಾಲು ಸಾಮಾನ್ಯಕ್ಕಿಂತ {n}% ಹೆಚ್ಚು', hi: 'आवक सामान्य से {n}% ज़्यादा' },
  'reason.arrivals_low': { en: 'Arrivals are {n}% below normal', kn: 'ಮಾರುಕಟ್ಟೆಗೆ ಬರುವ ಮಾಲು ಸಾಮಾನ್ಯಕ್ಕಿಂತ {n}% ಕಡಿಮೆ', hi: 'आवक सामान्य से {n}% कम' },
  'reason.above_last_year': { en: '{n}% higher than this time last year', kn: 'ಕಳೆದ ವರ್ಷ ಇದೇ ಸಮಯಕ್ಕಿಂತ {n}% ಹೆಚ್ಚು', hi: 'पिछले साल इसी समय से {n}% ज़्यादा' },
  'reason.below_last_year': { en: '{n}% lower than this time last year', kn: 'ಕಳೆದ ವರ್ಷ ಇದೇ ಸಮಯಕ್ಕಿಂತ {n}% ಕಡಿಮೆ', hi: 'पिछले साल इसी समय से {n}% कम' },
  'reason.model_expects_up': { en: 'We expect about {n}% more in {d} days', kn: '{d} ದಿನಗಳಲ್ಲಿ ಸುಮಾರು {n}% ಹೆಚ್ಚು ನಿರೀಕ್ಷೆ', hi: '{d} दिनों में लगभग {n}% ज़्यादा की उम्मीद' },
  'reason.model_expects_down': { en: 'We expect about {n}% less in {d} days', kn: '{d} ದಿನಗಳಲ್ಲಿ ಸುಮಾರು {n}% ಕಡಿಮೆ ನಿರೀಕ್ಷೆ', hi: '{d} दिनों में लगभग {n}% कम की उम्मीद' },
  'reason.spoils_fast': { en: 'This crop loses about {n}% of its value for every day it waits', kn: 'ಈ ಬೆಳೆ ಕಾಯುವ ಪ್ರತಿ ದಿನ ಸುಮಾರು {n}% ಮೌಲ್ಯ ಕಳೆದುಕೊಳ್ಳುತ್ತದೆ', hi: 'यह फसल रुकने के हर दिन लगभग {n}% मूल्य खो देती है' },
  'reason.neighbours_dearer': {
    en: 'Nearby districts are paying {n}% more — such gaps have usually closed within about {w} weeks',
    kn: 'ಹತ್ತಿರದ ಜಿಲ್ಲೆಗಳಲ್ಲಿ {n}% ಹೆಚ್ಚು ಬೆಲೆ ಇದೆ — ಇಂತಹ ವ್ಯತ್ಯಾಸ ಸಾಮಾನ್ಯವಾಗಿ ಸುಮಾರು {w} ವಾರಗಳಲ್ಲಿ ಕಡಿಮೆಯಾಗಿದೆ',
    hi: 'आस-पास के ज़िलों में {n}% ज़्यादा भाव मिल रहा है — ऐसा अंतर आमतौर पर लगभग {w} हफ़्तों में कम हो गया है',
  },
  'reason.neighbours_cheaper': {
    en: 'Nearby districts are paying {n}% less — such gaps have usually closed within about {w} weeks',
    kn: 'ಹತ್ತಿರದ ಜಿಲ್ಲೆಗಳಲ್ಲಿ {n}% ಕಡಿಮೆ ಬೆಲೆ ಇದೆ — ಇಂತಹ ವ್ಯತ್ಯಾಸ ಸಾಮಾನ್ಯವಾಗಿ ಸುಮಾರು {w} ವಾರಗಳಲ್ಲಿ ಕಡಿಮೆಯಾಗಿದೆ',
    hi: 'आस-पास के ज़िलों में {n}% कम भाव मिल रहा है — ऐसा अंतर आमतौर पर लगभग {w} हफ़्तों में कम हो गया है',
  },

  'chart.thisYear': { en: 'This year', kn: 'ಈ ವರ್ಷ', hi: 'इस साल' },
  'chart.lastYear': { en: 'Same time last year', kn: 'ಕಳೆದ ವರ್ಷ ಇದೇ ಸಮಯ', hi: 'पिछले साल इसी समय' },
  'chart.next': { en: 'Next 7 days, likely range', kn: 'ಮುಂದಿನ 7 ದಿನ, ಸಂಭವನೀಯ ಶ್ರೇಣಿ', hi: 'अगले 7 दिन, संभावित दायरा' },
  'chart.today': { en: 'Today', kn: 'ಇಂದು', hi: 'आज' },
  'chart.likely': { en: 'Likely', kn: 'ಸಂಭವನೀಯ', hi: 'संभावित' },
  'chart.hint': { en: 'Touch the chart to read a day', kn: 'ಒಂದು ದಿನದ ಬೆಲೆ ನೋಡಲು ಚಾರ್ಟ್ ಮುಟ್ಟಿ', hi: 'किसी दिन का भाव देखने के लिए चार्ट छुएँ' },

  'mandis.title': { en: 'At the mandis today', kn: 'ಇಂದು ಮಂಡಿಗಳಲ್ಲಿ', hi: 'आज मंडियों में' },
  'mandis.sub': { en: 'Lowest to highest price paid today', kn: 'ಇಂದು ಕೊಟ್ಟ ಕನಿಷ್ಠದಿಂದ ಗರಿಷ್ಠ ಬೆಲೆ', hi: 'आज दिए गए सबसे कम से सबसे ज़्यादा भाव' },
  'mandis.typical': { en: 'Typical', kn: 'ಸಾಮಾನ್ಯ', hi: 'आम भाव' },
  'mandis.tonnes': { en: '{n} t arrived', kn: '{n} ಟನ್ ಬಂದಿದೆ', hi: '{n} टन आवक' },
  'mandis.empty': { en: 'No mandi nearby reported this crop in the last few days.', kn: 'ಕಳೆದ ಕೆಲವು ದಿನಗಳಲ್ಲಿ ಹತ್ತಿರದ ಯಾವ ಮಂಡಿಯೂ ಈ ಬೆಳೆಯ ಬೆಲೆ ವರದಿ ಮಾಡಿಲ್ಲ.', hi: 'पिछले कुछ दिनों में पास की किसी मंडी ने इस फसल का भाव नहीं बताया।' },
  'mandis.here': { en: 'In your district', kn: 'ನಿಮ್ಮ ಜಿಲ್ಲೆಯಲ್ಲಿ', hi: 'आपके ज़िले में' },
  'mandis.elsewhere': { en: 'Elsewhere nearby', kn: 'ಹತ್ತಿರದ ಇತರೆಡೆ', hi: 'आस-पास अन्य जगह' },

  'supply.title': { en: 'How much is arriving', kn: 'ಮಾರುಕಟ್ಟೆಗೆ ಎಷ್ಟು ಬರುತ್ತಿದೆ', hi: 'कितनी आवक हो रही है' },
  'supply.low': { en: 'Scarce', kn: 'ಕಡಿಮೆ', hi: 'कम' },
  'supply.normal': { en: 'Normal', kn: 'ಸಾಮಾನ್ಯ', hi: 'सामान्य' },
  'supply.high': { en: 'Glut', kn: 'ಹೆಚ್ಚು', hi: 'ज़्यादा' },
  'supply.body': { en: '{a} tonnes came in; a normal day is about {b}.', kn: '{a} ಟನ್ ಬಂದಿದೆ; ಸಾಮಾನ್ಯ ದಿನ ಸುಮಾರು {b}.', hi: '{a} टन आया; सामान्य दिन लगभग {b}।' },

  'year.title': { en: 'Compared with last year', kn: 'ಕಳೆದ ವರ್ಷದೊಂದಿಗೆ ಹೋಲಿಕೆ', hi: 'पिछले साल से तुलना' },
  'year.body': { en: 'A year ago today it was ₹{p}.', kn: 'ಒಂದು ವರ್ಷದ ಹಿಂದೆ ಇಂದು ₹{p} ಇತ್ತು.', hi: 'एक साल पहले आज ₹{p} था।' },

  'trust.title': { en: 'How often have we been right?', kn: 'ನಾವು ಎಷ್ಟು ಬಾರಿ ಸರಿ?', hi: 'हम कितनी बार सही रहे?' },
  'trust.body': { en: 'On weeks we had never seen, we read the direction of the price right {n} times in 100.', kn: 'ನಾವು ಹಿಂದೆಂದೂ ನೋಡದ ವಾರಗಳಲ್ಲಿ ಬೆಲೆಯ ದಿಕ್ಕನ್ನು 100ರಲ್ಲಿ {n} ಬಾರಿ ಸರಿಯಾಗಿ ಹೇಳಿದ್ದೇವೆ.', hi: 'जिन हफ़्तों को हमने पहले कभी नहीं देखा, उनमें हमने भाव की दिशा 100 में से {n} बार सही बताई।' },
  'trust.more': { en: 'See the full record', kn: 'ಪೂರ್ಣ ದಾಖಲೆ ನೋಡಿ', hi: 'पूरा रिकॉर्ड देखें' },
  'trust.honest': { en: 'Prices move for reasons no model sees. We show our misses as plainly as our hits.', kn: 'ಬೆಲೆ ಏರಿಳಿತಕ್ಕೆ ಯಾವ ಮಾದರಿಗೂ ಕಾಣದ ಕಾರಣಗಳಿರುತ್ತವೆ. ನಮ್ಮ ತಪ್ಪುಗಳನ್ನೂ ಸರಿಗಳಷ್ಟೇ ಸ್ಪಷ್ಟವಾಗಿ ತೋರಿಸುತ್ತೇವೆ.', hi: 'भाव कई ऐसे कारणों से बदलते हैं जो कोई मॉडल नहीं देखता। हम अपनी गलतियाँ भी उतनी ही साफ़ दिखाते हैं।' },

  'place.pick': { en: 'Choose your district', kn: 'ನಿಮ್ಮ ಜಿಲ್ಲೆ ಆರಿಸಿ', hi: 'अपना ज़िला चुनें' },
  'place.locate': { en: 'Use my location', kn: 'ನನ್ನ ಸ್ಥಳ ಬಳಸಿ', hi: 'मेरी लोकेशन इस्तेमाल करें' },
  'place.locating': { en: 'Finding you…', kn: 'ಹುಡುಕುತ್ತಿದೆ…', hi: 'खोज रहे हैं…' },
  'place.denied': { en: 'Location is off. Pick your district below.', kn: 'ಸ್ಥಳ ಆಫ್ ಆಗಿದೆ. ಕೆಳಗೆ ನಿಮ್ಮ ಜಿಲ್ಲೆ ಆರಿಸಿ.', hi: 'लोकेशन बंद है। नीचे अपना ज़िला चुनें।' },

  'ask.placeholder': { en: 'Ask: “tomato in Kolar”', kn: 'ಕೇಳಿ: “ಕೋಲಾರ ಟೊಮೇಟೊ”', hi: 'पूछें: “कोलार में टमाटर”' },
  'ask.notfound': { en: 'Name a crop, like tomato, onion, potato or ginger.', kn: 'ಒಂದು ಬೆಳೆಯ ಹೆಸರು ಹೇಳಿ: ಟೊಮೇಟೊ, ಈರುಳ್ಳಿ, ಆಲೂಗಡ್ಡೆ ಅಥವಾ ಶುಂಠಿ.', hi: 'किसी फसल का नाम बताएँ: टमाटर, प्याज़, आलू या अदरक।' },

  'plan.cta': { en: 'Plan my sale', kn: 'ನನ್ನ ಮಾರಾಟ ಯೋಜಿಸಿ', hi: 'मेरी बिक्री की योजना' },
  'more.tools': { en: 'More tools', kn: 'ಇನ್ನಷ್ಟು ಸಾಧನಗಳು', hi: 'और उपकरण' },
};

export function say(key: string, lang: Lang, vars: Record<string, string | number> = {}): string {
  const entry = COPY[key];
  const template = entry ? entry[lang] || entry.en : key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
}

export function reasonText(reason: FarmReason, lang: Lang): string {
  const n = reason.value == null ? '' : Math.abs(reason.value).toFixed(reason.code === 'spoils_fast' ? 0 : 0);
  return say(`reason.${reason.code}`, lang, { n, d: reason.days ?? '', w: reason.weeks ?? '' });
}

export function placeName(entry: PlaceNames | { name: string; name_kn: string; name_hi: string } | null | undefined, lang: Lang): string {
  if (!entry) return '';
  if ('en' in entry) return entry[lang] || entry.en;
  return lang === 'kn' ? entry.name_kn : lang === 'hi' ? entry.name_hi : entry.name;
}

export function districtName(d: CatalogDistrict, lang: Lang): string {
  return placeName(d, lang);
}

export const rupees = (value: number | null | undefined): string =>
  value == null || Number.isNaN(value) ? '—' : `₹${new Intl.NumberFormat('en-IN').format(Math.round(value))}`;

export function shortDate(iso: string, lang: Lang): string {
  try {
    return new Date(iso).toLocaleDateString(lang === 'kn' ? 'kn-IN' : lang === 'hi' ? 'hi-IN' : 'en-IN', {
      day: 'numeric',
      month: 'short',
    });
  } catch {
    return iso;
  }
}

/** One-off trilingual strings, for copy that belongs to a single screen. */
export const tri = (lang: Lang, en: string, kn: string, hi: string): string => (lang === 'kn' ? kn : lang === 'hi' ? hi : en);
