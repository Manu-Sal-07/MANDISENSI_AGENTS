/**
 * Words for the farmer's "why this advice" panel and supply watch, in the three
 * farmer-surface languages. Sentences with figures come from the server (the
 * explanation is composed by code); only labels and fixed notices live here.
 */

import type { Lang } from './translations';

type Entry = Record<Lang, string>;

const COPY: Record<string, Entry> = {
  'why.title': { en: 'Why this advice', kn: 'ಈ ಸಲಹೆ ಏಕೆ', hi: 'यह सलाह क्यों' },
  'why.show': { en: 'Show the reasons', kn: 'ಕಾರಣಗಳನ್ನು ತೋರಿಸಿ', hi: 'कारण दिखाएँ' },
  'why.loading': { en: 'Writing the reasons…', kn: 'ಕಾರಣಗಳನ್ನು ಬರೆಯಲಾಗುತ್ತಿದೆ…', hi: 'कारण लिखे जा रहे हैं…' },
  'why.unavailable': {
    en: 'Reasons are not available right now. The advice above still stands.',
    kn: 'ಕಾರಣಗಳು ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಮೇಲಿನ ಸಲಹೆ ಹಾಗೆಯೇ ಇದೆ.',
    hi: 'कारण अभी उपलब्ध नहीं हैं। ऊपर की सलाह वैसी ही है।',
  },
  'why.author.llm': {
    en: 'Worded by an AI assistant. Every number and name is filled in by our system from the same data as the advice.',
    kn: 'AI ಸಹಾಯಕ ಪದಗಳನ್ನು ಬರೆದಿದೆ. ಪ್ರತಿ ಸಂಖ್ಯೆ ಮತ್ತು ಹೆಸರನ್ನು ಸಲಹೆಯ ಅದೇ ಮಾಹಿತಿಯಿಂದ ನಮ್ಮ ವ್ಯವಸ್ಥೆ ತುಂಬಿದೆ.',
    hi: 'शब्द AI सहायक ने लिखे हैं। हर संख्या और नाम हमारा सिस्टम उसी डेटा से भरता है जिससे सलाह बनी है।',
  },
  'why.author.rules': {
    en: 'Written by our system from the same data as the advice.',
    kn: 'ಸಲಹೆಯ ಅದೇ ಮಾಹಿತಿಯಿಂದ ನಮ್ಮ ವ್ಯವಸ್ಥೆ ಬರೆದಿದೆ.',
    hi: 'सलाह वाले ही डेटा से हमारे सिस्टम ने लिखा है।',
  },
  'why.cautions': { en: 'Keep in mind', kn: 'ನೆನಪಿಡಿ', hi: 'ध्यान रखें' },

  'watch.title': { en: 'Supply watch', kn: 'ಪೂರೈಕೆ ನಿಗಾ', hi: 'आवक पर नज़र' },
  'watch.arrivals': {
    en: 'Arrivals at {place} compared with a normal week',
    kn: '{place} ನಲ್ಲಿ ಆವಕ ಸಾಮಾನ್ಯ ವಾರಕ್ಕೆ ಹೋಲಿಸಿದರೆ',
    hi: '{place} में आवक, सामान्य सप्ताह की तुलना में',
  },
  'watch.glut': { en: 'Much more than normal', kn: 'ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಹೆಚ್ಚು', hi: 'सामान्य से काफ़ी ज़्यादा' },
  'watch.squeeze': { en: 'Much less than normal', kn: 'ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಕಡಿಮೆ', hi: 'सामान्य से काफ़ी कम' },
  'watch.normal': { en: 'About normal', kn: 'ಸುಮಾರು ಸಾಮಾನ್ಯ', hi: 'लगभग सामान्य' },
  'watch.times': { en: '{x} times normal', kn: 'ಸಾಮಾನ್ಯದ {x} ಪಟ್ಟು', hi: 'सामान्य का {x} गुना' },
  'watch.stale': {
    en: 'The latest arrival report is {n} days old, so this may not be current.',
    kn: 'ಇತ್ತೀಚಿನ ಆವಕ ವರದಿ {n} ದಿನ ಹಳೆಯದು, ಹಾಗಾಗಿ ಇದು ಈಗಿನದಾಗಿಲ್ಲದಿರಬಹುದು.',
    hi: 'आवक की ताज़ा रिपोर्ट {n} दिन पुरानी है, इसलिए यह अभी की स्थिति न हो।',
  },
  'watch.gap': {
    en: 'Neighbouring districts pay {p}% {dir} than {place} for {crop}',
    kn: 'ಅಕ್ಕಪಕ್ಕದ ಜಿಲ್ಲೆಗಳಲ್ಲಿ {crop} ಗೆ {place} ಗಿಂತ {p}% {dir} ಬೆಲೆ ಇದೆ',
    hi: 'पड़ोसी ज़िलों में {crop} का भाव {place} से {p}% {dir} है',
  },
  'watch.more': { en: 'more', kn: 'ಹೆಚ್ಚು', hi: 'ज़्यादा' },
  'watch.less': { en: 'less', kn: 'ಕಡಿಮೆ', hi: 'कम' },
  'watch.gapnote': {
    en: 'Gaps like this have usually closed within about {w} weeks, but we cannot yet say which way the price will move.',
    kn: 'ಇಂತಹ ಅಂತರ ಸಾಮಾನ್ಯವಾಗಿ ಸುಮಾರು {w} ವಾರಗಳಲ್ಲಿ ಮುಚ್ಚಿದೆ, ಆದರೆ ಬೆಲೆ ಯಾವ ಕಡೆ ಹೋಗುತ್ತದೆ ಎಂದು ಇನ್ನೂ ಹೇಳಲಾಗದು.',
    hi: 'ऐसे अंतर आम तौर पर लगभग {w} सप्ताह में कम हुए हैं, पर भाव किस ओर जाएगा यह अभी नहीं कह सकते।',
  },
  'watch.noclaim': {
    en: 'We do not claim that a rush or shortage of arrivals will move your price. In our tests that was not reliable enough to tell you.',
    kn: 'ಆವಕದ ಹೆಚ್ಚಳ ಅಥವಾ ಕೊರತೆ ನಿಮ್ಮ ಬೆಲೆಯನ್ನು ಬದಲಿಸುತ್ತದೆ ಎಂದು ನಾವು ಹೇಳುವುದಿಲ್ಲ. ನಮ್ಮ ಪರೀಕ್ಷೆಗಳಲ್ಲಿ ಅದು ಹೇಳುವಷ್ಟು ನಂಬಲರ್ಹವಾಗಿರಲಿಲ್ಲ.',
    hi: 'हम यह दावा नहीं करते कि आवक की भीड़ या कमी आपका भाव बदल देगी। हमारे परीक्षणों में यह बताने लायक भरोसेमंद नहीं निकला।',
  },
  'watch.robust': {
    en: 'In past data, after such a spell prices typically changed by {p}% within {d} days.',
    kn: 'ಹಿಂದಿನ ಮಾಹಿತಿಯಲ್ಲಿ ಇಂತಹ ಸ್ಥಿತಿಯ ನಂತರ {d} ದಿನಗಳಲ್ಲಿ ಬೆಲೆ ಸಾಮಾನ್ಯವಾಗಿ {p}% ಬದಲಾಗಿದೆ.',
    hi: 'पिछले डेटा में ऐसी स्थिति के बाद {d} दिन में भाव आम तौर पर {p}% बदला।',
  },
};

export function sc(key: string, lang: Lang, vars: Record<string, string | number> = {}): string {
  const entry = COPY[key];
  const template = entry ? entry[lang] || entry.en : key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
}
