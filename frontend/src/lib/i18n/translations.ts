/**
 * Translation dictionary for the farmer surface.
 *
 * Three languages, in the order this population actually reads them:
 * Kannada first (every tracked mandi is in Karnataka, and Kannada was
 * entirely absent from the frontend before this file existed — only Hindi
 * names were carried, on `ProduceIcon`/`CallCard`), then Hindi, then English
 * as the fallback for anyone reading this codebase.
 *
 * Kept as a flat key -> {en, hi, kn} record rather than nested namespaces:
 * this surface is small enough that a flat lookup stays readable, and a
 * missing translation is easy to spot as a hole in one row rather than a
 * missing branch in a tree.
 */

export type Lang = 'en' | 'hi' | 'kn';

export const LANGUAGE_LABELS: Record<Lang, string> = {
  en: 'English',
  hi: 'हिन्दी',
  kn: 'ಕನ್ನಡ',
};

type Entry = Record<Lang, string>;

export const TRANSLATIONS: Record<string, Entry> = {
  // ── shared ──────────────────────────────────────────────────────────────
  'common.loading': { en: 'Loading…', hi: 'लोड हो रहा है…', kn: 'ಲೋಡ್ ಆಗುತ್ತಿದೆ…' },
  'common.retry': { en: 'Try again', hi: 'फिर से कोशिश करें', kn: 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ' },
  'common.close': { en: 'Close', hi: 'बंद करें', kn: 'ಮುಚ್ಚಿ' },
  'common.quintal': { en: 'quintal', hi: 'क्विंटल', kn: 'ಕ್ವಿಂಟಾಲ್' },
  'common.quintals': { en: 'quintals', hi: 'क्विंटल', kn: 'ಕ್ವಿಂಟಾಲ್' },
  'common.unavailable_title': { en: 'Not enough data yet', hi: 'अभी पर्याप्त जानकारी नहीं है', kn: 'ಇನ್ನೂ ಸಾಕಷ್ಟು ಮಾಹಿತಿ ಇಲ್ಲ' },
  'common.submit': { en: 'Check', hi: 'जांचें', kn: 'ಪರಿಶೀಲಿಸಿ' },
  'common.cancel': { en: 'Cancel', hi: 'रद्द करें', kn: 'ರದ್ದುಮಾಡಿ' },

  // ── tools hub ───────────────────────────────────────────────────────────
  'tools.title': { en: 'Farmer Tools', hi: 'किसान उपकरण', kn: 'ರೈತ ಸಾಧನಗಳು' },
  'tools.subtitle': {
    en: 'Everything beyond today’s call',
    hi: 'आज की सलाह से आगे सब कुछ',
    kn: 'ಇಂದಿನ ಸಲಹೆಯ ಆಚೆಗಿನ ಎಲ್ಲವೂ',
  },

  'tool.fair_price.title': { en: 'Fair Price Check', hi: 'उचित मूल्य जांच', kn: 'ನ್ಯಾಯಯುತ ಬೆಲೆ ಪರಿಶೀಲನೆ' },
  'tool.fair_price.desc': {
    en: 'Is the trader’s offer fair, right now?',
    hi: 'क्या व्यापारी का प्रस्ताव अभी उचित है?',
    kn: 'ವ್ಯಾಪಾರಿಯ ಆಫರ್ ಈಗ ನ್ಯಾಯಯುತವೇ?',
  },
  'tool.harvest.title': { en: 'My Harvest in Rupees', hi: 'मेरी फसल, रुपयों में', kn: 'ನನ್ನ ಬೆಳೆ, ರೂಪಾಯಿಗಳಲ್ಲಿ' },
  'tool.harvest.desc': {
    en: 'What your crop is worth on each day ahead',
    hi: 'आने वाले हर दिन आपकी फसल की कीमत',
    kn: 'ಮುಂಬರುವ ಪ್ರತಿ ದಿನ ನಿಮ್ಮ ಬೆಳೆಯ ಮೌಲ್ಯ',
  },
  'tool.hold_or_rot.title': { en: 'Hold or Sell', hi: 'रोकें या बेचें', kn: 'ಇಡಬೇಕೆ ಅಥವಾ ಮಾರಬೇಕೆ' },
  'tool.hold_or_rot.desc': {
    en: 'Waiting has a cost — is it worth it?',
    hi: 'रुकने की कीमत है — क्या यह फायदेमंद है?',
    kn: 'ಕಾಯುವುದಕ್ಕೂ ಬೆಲೆ ಇದೆ — ಅದು ಯೋಗ್ಯವೇ?',
  },
  'tool.seasonal_memory.title': { en: 'This Time Last Year', hi: 'पिछले साल इसी समय', kn: 'ಕಳೆದ ವರ್ಷ ಇದೇ ಸಮಯ' },
  'tool.seasonal_memory.desc': {
    en: 'How today compares to seasons past',
    hi: 'आज की तुलना बीते मौसमों से',
    kn: 'ಇಂದಿನ ಬೆಲೆ ಹಿಂದಿನ ಋತುಗಳಿಗೆ ಹೇಗೆ ಹೋಲಿಸುತ್ತದೆ',
  },
  'tool.where_to_sell.title': { en: 'Where to Sell', hi: 'कहाँ बेचें', kn: 'ಎಲ್ಲಿ ಮಾರಾಟ ಮಾಡುವುದು' },
  'tool.where_to_sell.desc': {
    en: 'Best net price after transport, nearby',
    hi: 'आस-पास, परिवहन के बाद सबसे अच्छा दाम',
    kn: 'ಹತ್ತಿರದಲ್ಲಿ, ಸಾರಿಗೆ ನಂತರ ಉತ್ತಮ ನಿವ್ವಳ ಬೆಲೆ',
  },
  'tool.supply_signal.title': { en: 'Supply Signal', hi: 'आपूर्ति संकेत', kn: 'ಪೂರೈಕೆ ಸಂಕೇತ' },
  'tool.supply_signal.desc': {
    en: 'Is too much (or too little) arriving?',
    hi: 'क्या बहुत ज्यादा (या बहुत कम) आ रहा है?',
    kn: 'ಹೆಚ್ಚು (ಅಥವಾ ಕಡಿಮೆ) ಬರುತ್ತಿದೆಯೇ?',
  },
  'tool.track_record.title': { en: 'Did We Get It Right?', hi: 'क्या हमारी सलाह सही थी?', kn: 'ನಮ್ಮ ಸಲಹೆ ಸರಿಯಾಗಿತ್ತೇ?' },
  'tool.track_record.desc': {
    en: 'Our own scorecard, checked against real outcomes',
    hi: 'हमारा अपना रिकॉर्ड, असली नतीजों से जांचा गया',
    kn: 'ನಮ್ಮ ಸ್ಕೋರ್‌ಕಾರ್ಡ್, ನಿಜವಾದ ಫಲಿತಾಂಶಗಳ ಜೊತೆ ಪರಿಶೀಲಿಸಲಾಗಿದೆ',
  },
  'tool.truck_share.title': { en: 'Truck Sharing', hi: 'ट्रक साझा करें', kn: 'ಟ್ರಕ್ ಹಂಚಿಕೆ' },
  'tool.truck_share.desc': {
    en: 'Split a trip, split the transport cost',
    hi: 'यात्रा बाँटें, परिवहन खर्च बाँटें',
    kn: 'ಪ್ರಯಾಣ ಹಂಚಿ, ಸಾರಿಗೆ ವೆಚ್ಚ ಹಂಚಿ',
  },
  'tool.crop_planning.title': { en: 'What to Plant Next', hi: 'आगे क्या बोएँ', kn: 'ಮುಂದೆ ಏನು ಬೆಳೆಯುವುದು' },
  'tool.crop_planning.desc': {
    en: 'Seasonal patterns across crops at your mandi',
    hi: 'आपकी मंडी में फसलों के मौसमी रुझान',
    kn: 'ನಿಮ್ಮ ಮಂಡಿಯಲ್ಲಿ ಬೆಳೆಗಳ ಋತುಮಾನದ ಪ್ರವೃತ್ತಿ',
  },
  'tool.alerts.title': { en: 'Price Alerts', hi: 'मूल्य अलर्ट', kn: 'ಬೆಲೆ ಎಚ್ಚರಿಕೆಗಳು' },
  'tool.alerts.desc': {
    en: 'Get notified the moment your price hits',
    hi: 'आपकी कीमत आते ही सूचना पाएँ',
    kn: 'ನಿಮ್ಮ ಬೆಲೆ ತಲುಪಿದ ಕ್ಷಣ ಸೂಚನೆ ಪಡೆಯಿರಿ',
  },

  // ── voice assistant ─────────────────────────────────────────────────────
  'voice.listening': { en: 'Listening…', hi: 'सुन रहा है…', kn: 'ಕೇಳುತ್ತಿದೆ…' },
  'voice.tap_to_speak': { en: 'Tap and speak your question', hi: 'टैप करें और अपना सवाल बोलें', kn: 'ಟ್ಯಾಪ್ ಮಾಡಿ ಮತ್ತು ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಕೇಳಿ' },
  'voice.not_supported': {
    en: 'Voice is not supported on this browser',
    hi: 'इस ब्राउज़र में आवाज़ सुविधा उपलब्ध नहीं है',
    kn: 'ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಸೌಲಭ್ಯ ಲಭ್ಯವಿಲ್ಲ',
  },
  'voice.read_aloud': { en: 'Read aloud', hi: 'ज़ोर से पढ़ें', kn: 'ಗಟ್ಟಿಯಾಗಿ ಓದಿ' },
};

export function translate(key: string, lang: Lang): string {
  const entry = TRANSLATIONS[key];
  if (!entry) return key;
  return entry[lang] || entry.en || key;
}
