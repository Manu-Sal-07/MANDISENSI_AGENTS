/**
 * Words for the "Best place and day to sell" tool, in the three languages the
 * farmer surface serves. The API returns structured fields and codes, so this
 * is the only place the sentences are composed. `{x}` slots are filled by
 * `mc()`; a missing translation falls back to English.
 */

import type { Lang } from './translations';

type Entry = Record<Lang, string>;

const COPY: Record<string, Entry> = {
  'title': { en: 'Best Place & Day to Sell', kn: 'ಮಾರಲು ಉತ್ತಮ ಸ್ಥಳ ಮತ್ತು ದಿನ', hi: 'बेचने की सबसे अच्छी जगह और दिन' },
  'subtitle': { en: 'With a minimum you can count on', kn: 'ನೀವು ನಂಬಬಹುದಾದ ಕನಿಷ್ಠ ಬೆಲೆಯೊಂದಿಗೆ', hi: 'एक भरोसेमंद न्यूनतम भाव के साथ' },
  'tile.desc': {
    en: 'Which mandi, which day, and the least you will get',
    kn: 'ಯಾವ ಮಂಡಿ, ಯಾವ ದಿನ, ಮತ್ತು ಕನಿಷ್ಠ ಎಷ್ಟು ಸಿಗುತ್ತದೆ',
    hi: 'कौन सी मंडी, कौन सा दिन, और कम से कम कितना मिलेगा',
  },
  'where_are_you': { en: 'Where are you?', kn: 'ನೀವು ಎಲ್ಲಿದ್ದೀರಿ?', hi: 'आप कहाँ हैं?' },
  'use_location': { en: 'Use my location', kn: 'ನನ್ನ ಸ್ಥಳ ಬಳಸಿ', hi: 'मेरा स्थान उपयोग करें' },
  'located': { en: 'Location set', kn: 'ಸ್ಥಳ ನಿಗದಿ', hi: 'स्थान तय' },
  'quantity': { en: 'How much? (quintals)', kn: 'ಎಷ್ಟು? (ಕ್ವಿಂಟಾಲ್)', hi: 'कितना? (क्विंटल)' },
  'vehicle': { en: 'How will you carry it?', kn: 'ಹೇಗೆ ಸಾಗಿಸುತ್ತೀರಿ?', hi: 'कैसे ले जाएंगे?' },
  'veh.shared_truck': { en: 'Shared truck', kn: 'ಹಂಚಿಕೆ ಟ್ರಕ್', hi: 'साझा ट्रक' },
  'veh.tempo': { en: 'Tempo', kn: 'ಟೆಂಪೋ', hi: 'टेम्पो' },
  'veh.small_pickup': { en: 'Small pickup', kn: 'ಸಣ್ಣ ಪಿಕಪ್', hi: 'छोटा पिकअप' },
  'sure': { en: 'How sure do you want to be?', kn: 'ಎಷ್ಟು ಖಚಿತತೆ ಬೇಕು?', hi: 'कितना भरोसा चाहिए?' },
  'sure.value': { en: '{n} out of 10 times', kn: '10 ರಲ್ಲಿ {n} ಬಾರಿ', hi: '10 में से {n} बार' },
  'loading': { en: 'Comparing mandis and days…', kn: 'ಮಂಡಿ ಮತ್ತು ದಿನಗಳನ್ನು ಹೋಲಿಸಲಾಗುತ್ತಿದೆ…', hi: 'मंडियों और दिनों की तुलना हो रही है…' },
  'sell_at': { en: 'Sell at', kn: 'ಇಲ್ಲಿ ಮಾರಿ', hi: 'यहाँ बेचें' },
  'sell_farm_gate': { en: 'Sell at your farm gate', kn: 'ನಿಮ್ಮ ಜಮೀನಿನಲ್ಲೇ ಮಾರಿ', hi: 'अपने खेत पर ही बेचें' },
  'day.today': { en: 'today', kn: 'ಇಂದು', hi: 'आज' },
  'day.hold': { en: 'in {n} day(s)', kn: '{n} ದಿನದ ನಂತರ', hi: '{n} दिन बाद' },
  'expected': { en: 'Expected, after transport and spoilage', kn: 'ಸಾಗಣೆ ಮತ್ತು ಹಾಳಾಗುವಿಕೆ ನಂತರ ನಿರೀಕ್ಷೆ', hi: 'ढुलाई और खराबी के बाद अपेक्षित' },
  'per_q': { en: 'per quintal', kn: 'ಕ್ವಿಂಟಾಲ್‌ಗೆ', hi: 'प्रति क्विंटल' },
  'floor': { en: 'You can count on at least', kn: 'ಕನಿಷ್ಠ ಸಿಗುವ ಮೊತ್ತ', hi: 'कम से कम मिलेगा' },
  'floor.note': {
    en: 'This minimum was missed about {p} of the time in past tests.',
    kn: 'ಹಿಂದಿನ ಪರೀಕ್ಷೆಗಳಲ್ಲಿ ಈ ಕನಿಷ್ಠ ಮೊತ್ತ ಸುಮಾರು {p} ಬಾರಿ ತಪ್ಪಿತ್ತು.',
    hi: 'पिछले परीक्षणों में यह न्यूनतम लगभग {p} बार चूका।',
  },
  'total': { en: 'For {q} quintals', kn: '{q} ಕ್ವಿಂಟಾಲ್‌ಗೆ', hi: '{q} क्विंटल के लिए' },
  'expected_total': { en: 'expected', kn: 'ನಿರೀಕ್ಷೆ', hi: 'अपेक्षित' },
  'floor_total': { en: 'at least', kn: 'ಕನಿಷ್ಠ', hi: 'कम से कम' },
  'chance_open': { en: 'Chance the mandi is open', kn: 'ಮಂಡಿ ತೆರೆದಿರುವ ಸಾಧ್ಯತೆ', hi: 'मंडी खुली होने की संभावना' },
  'distance': { en: '{n} km away', kn: '{n} ಕಿ.ಮೀ ದೂರ', hi: '{n} किमी दूर' },
  'vs_nearest': { en: 'vs. the nearest mandi today', kn: 'ಹತ್ತಿರದ ಮಂಡಿಗೆ ಇಂದು ಹೋದರೆ ಹೋಲಿಸಿದರೆ', hi: 'आज सबसे नज़दीकी मंडी की तुलना में' },
  'more': { en: 'more', kn: 'ಹೆಚ್ಚು', hi: 'ज़्यादा' },
  'less': { en: 'less', kn: 'ಕಡಿಮೆ', hi: 'कम' },
  'safest': { en: 'Want the surest minimum instead?', kn: 'ಬದಲಾಗಿ ಅತ್ಯಂತ ಖಚಿತ ಕನಿಷ್ಠ ಬೇಕೇ?', hi: 'या सबसे पक्का न्यूनतम चाहिए?' },
  'safest.note': {
    en: 'Gives up some expected money for a higher guaranteed minimum.',
    kn: 'ಹೆಚ್ಚಿನ ಖಚಿತ ಕನಿಷ್ಠಕ್ಕಾಗಿ ನಿರೀಕ್ಷಿತ ಹಣದಲ್ಲಿ ಸ್ವಲ್ಪ ಬಿಡಬೇಕು.',
    hi: 'ज़्यादा पक्के न्यूनतम के लिए कुछ अपेक्षित पैसा छोड़ना पड़ता है।',
  },
  'others': { en: 'Other good choices', kn: 'ಇತರ ಒಳ್ಳೆಯ ಆಯ್ಕೆಗಳು', hi: 'अन्य अच्छे विकल्प' },
  'track': { en: 'How this advice has done', kn: 'ಈ ಸಲಹೆ ಹೇಗೆ ಕೆಲಸ ಮಾಡಿದೆ', hi: 'यह सलाह कैसी रही है' },
  'track.line': {
    en: 'Over {d} past days we had not seen, following this advice earned {a} per quintal. Going to the nearest mandi earned {b}.',
    kn: 'ನಾವು ನೋಡಿರದ ಕಳೆದ {d} ದಿನಗಳಲ್ಲಿ, ಈ ಸಲಹೆ ಅನುಸರಿಸಿದರೆ ಕ್ವಿಂಟಾಲ್‌ಗೆ {a} ಸಿಗುತ್ತಿತ್ತು. ಹತ್ತಿರದ ಮಂಡಿಗೆ ಹೋದರೆ {b}.',
    hi: 'पिछले {d} ऐसे दिनों में जो हमने देखे नहीं थे, इस सलाह पर चलने से प्रति क्विंटल {a} मिलता। सबसे नज़दीकी मंडी जाने पर {b}।',
  },
  'track.limited': {
    en: 'For this crop the advice did not clearly beat simply going to yesterday’s highest-priced mandi, so treat it as a guide, not a promise.',
    kn: 'ಈ ಬೆಳೆಗೆ, ನಿನ್ನೆ ಅತಿ ಹೆಚ್ಚು ಬೆಲೆ ಇದ್ದ ಮಂಡಿಗೆ ಹೋಗುವುದಕ್ಕಿಂತ ಈ ಸಲಹೆ ಸ್ಪಷ್ಟವಾಗಿ ಉತ್ತಮವಾಗಿರಲಿಲ್ಲ; ಇದನ್ನು ಮಾರ್ಗದರ್ಶನವೆಂದು ಮಾತ್ರ ಪರಿಗಣಿಸಿ.',
    hi: 'इस फसल के लिए यह सलाह कल सबसे ऊँचे भाव वाली मंडी जाने से साफ़ बेहतर नहीं रही, इसलिए इसे मार्गदर्शन समझें, वादा नहीं।',
  },
  'track.gain': { en: 'Average gain over going to yesterday’s highest-priced mandi: {g} per quintal', kn: 'ನಿನ್ನೆ ಅತಿ ಹೆಚ್ಚು ಬೆಲೆಯ ಮಂಡಿಗೆ ಹೋಗುವುದಕ್ಕಿಂತ ಸರಾಸರಿ ಲಾಭ: ಕ್ವಿಂಟಾಲ್‌ಗೆ {g}', hi: 'कल सबसे ऊँचे भाव वाली मंडी जाने से औसत फ़ायदा: प्रति क्विंटल {g}' },
  'why': { en: 'How we know this works', kn: 'ಇದು ಕೆಲಸ ಮಾಡುತ್ತದೆ ಎಂದು ಹೇಗೆ ಗೊತ್ತು', hi: 'हमें कैसे पता कि यह काम करता है' },
  'assume': {
    en: 'Assumes transport ₹{t} per quintal per km, {s}% spoilage a day, 4% mandi fee. Change the vehicle to match yours.',
    kn: 'ಸಾಗಣೆ ಕ್ವಿಂಟಾಲ್‌ಗೆ ಕಿ.ಮೀ.ಗೆ ₹{t}, ದಿನಕ್ಕೆ {s}% ಹಾಳಾಗುವಿಕೆ, 4% ಮಂಡಿ ಶುಲ್ಕ ಎಂದು ಊಹಿಸಲಾಗಿದೆ. ನಿಮ್ಮ ವಾಹನಕ್ಕೆ ತಕ್ಕಂತೆ ಬದಲಿಸಿ.',
    hi: 'मान्यता: ढुलाई ₹{t} प्रति क्विंटल प्रति किमी, {s}% रोज़ खराबी, 4% मंडी शुल्क। अपने वाहन के अनुसार बदलें।',
  },
  'asof': { en: 'Based on prices through {d}', kn: '{d}ರವರೆಗಿನ ಬೆಲೆಗಳ ಆಧಾರದ ಮೇಲೆ', hi: '{d} तक के भाव के आधार पर' },
  'caveat.limited_evidence': {
    en: 'Few mandis report for this crop, so we cannot be as sure here.',
    kn: 'ಈ ಬೆಳೆಗೆ ಕಡಿಮೆ ಮಂಡಿಗಳು ವರದಿ ಮಾಡುತ್ತವೆ, ಹಾಗಾಗಿ ಇಲ್ಲಿ ಖಚಿತತೆ ಕಡಿಮೆ.',
    hi: 'इस फसल के लिए कम मंडियाँ रिपोर्ट करती हैं, इसलिए यहाँ भरोसा कम है।',
  },
  'caveat.sale_on_sunday': {
    en: 'The sale day is a Sunday; many mandis are closed.',
    kn: 'ಮಾರಾಟದ ದಿನ ಭಾನುವಾರ; ಅನೇಕ ಮಂಡಿಗಳು ಮುಚ್ಚಿರುತ್ತವೆ.',
    hi: 'बिक्री का दिन रविवार है; कई मंडियाँ बंद रहती हैं।',
  },
  'caveat.mandi_may_be_closed': {
    en: 'This mandi is often closed on that day. Check before you go.',
    kn: 'ಆ ದಿನ ಈ ಮಂಡಿ ಆಗಾಗ ಮುಚ್ಚಿರುತ್ತದೆ. ಹೋಗುವ ಮೊದಲು ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ.',
    hi: 'उस दिन यह मंडी अक्सर बंद रहती है। जाने से पहले पता कर लें।',
  },
  'caveat.stale_data': {
    en: 'The latest prices are a few days old.',
    kn: 'ಇತ್ತೀಚಿನ ಬೆಲೆಗಳು ಕೆಲವು ದಿನ ಹಳೆಯವು.',
    hi: 'ताज़ा भाव कुछ दिन पुराने हैं।',
  },
  'unavailable': { en: 'We cannot advise on this crop yet', kn: 'ಈ ಬೆಳೆಗೆ ಇನ್ನೂ ಸಲಹೆ ನೀಡಲಾಗದು', hi: 'इस फसल पर अभी सलाह नहीं दे सकते' },
  'farm_gate.note': { en: 'Selling at the farm gate beats every mandi today.', kn: 'ಇಂದು ಜಮೀನಿನಲ್ಲೇ ಮಾರುವುದು ಎಲ್ಲಾ ಮಂಡಿಗಳಿಗಿಂತ ಉತ್ತಮ.', hi: 'आज खेत पर बेचना हर मंडी से बेहतर है।' },
};

export function mc(key: string, lang: Lang, vars: Record<string, string | number> = {}): string {
  const entry = COPY[key];
  const template = entry ? entry[lang] || entry.en : key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
}

export const mandiLabel = (o: { mandi_name: string; mandi_name_kn: string; mandi_name_hi: string }, lang: Lang): string =>
  lang === 'kn' ? o.mandi_name_kn : lang === 'hi' ? o.mandi_name_hi : o.mandi_name;

export const dayLabel = (hold: number, lang: Lang): string => (hold === 0 ? mc('day.today', lang) : mc('day.hold', lang, { n: hold }));
