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

  // ── home hero ────────────────────────────────────────────────────────────
  'home.headline': { en: 'Sell today, or wait?', hi: 'आज बेचें या रुकें?', kn: 'ಇಂದು ಮಾರಬೇಕೆ, ಕಾಯಬೇಕೆ?' },
  'home.sell_plan_cta': { en: 'Plan my harvest sale', hi: 'मेरी फसल की बिक्री की योजना', kn: 'ನನ್ನ ಬೆಳೆ ಮಾರಾಟದ ಯೋಜನೆ' },
  'home.footer_disclaimer': {
    en: 'Prices come from government mandi records. Advice is guidance, not a guarantee.',
    hi: 'कीमतें सरकारी मंडी रिकॉर्ड से ली गई हैं। सलाह मार्गदर्शन है, गारंटी नहीं।',
    kn: 'ಬೆಲೆಗಳು ಸರ್ಕಾರಿ ಮಂಡಿ ದಾಖಲೆಗಳಿಂದ ಬಂದಿವೆ. ಸಲಹೆ ಮಾರ್ಗದರ್ಶನ, ಖಾತರಿಯಲ್ಲ.',
  },
  'home.todays_calls': { en: "Today's calls", hi: 'आज की सलाह', kn: 'ಇಂದಿನ ಸಲಹೆ' },
  'home.mandis_near_you': { en: 'Mandis near you', hi: 'आस-पास की मंडियाँ', kn: 'ಹತ್ತಿರದ ಮಂಡಿಗಳು' },
  'home.ask_another': { en: 'Ask about another crop', hi: 'दूसरी फसल के बारे में पूछें', kn: 'ಇನ್ನೊಂದು ಬೆಳೆಯ ಬಗ್ಗೆ ಕೇಳಿ' },

  // ── bottom nav ───────────────────────────────────────────────────────────
  'nav.home': { en: 'Home', hi: 'होम', kn: 'ಮುಖಪುಟ' },
  'nav.sell_plan': { en: 'Sell', hi: 'बिक्री', kn: 'ಮಾರಾಟ' },
  'nav.my_money': { en: 'My Money', hi: 'मेरा पैसा', kn: 'ನನ್ನ ಹಣ' },
  'nav.tools': { en: 'Tools', hi: 'उपकरण', kn: 'ಸಾಧನಗಳು' },
  'nav.markets': { en: 'Markets', hi: 'बाज़ार', kn: 'ಮಾರುಕಟ್ಟೆ' },

  // ── sell plan ────────────────────────────────────────────────────────────
  'sellplan.title': { en: 'Plan My Harvest Sale', hi: 'मेरी फसल की बिक्री की योजना', kn: 'ನನ್ನ ಬೆಳೆ ಮಾರಾಟದ ಯೋಜನೆ' },
  'sellplan.subtitle': {
    en: 'One answer: where, when, and how much',
    hi: 'एक जवाब: कहाँ, कब, और कितना',
    kn: 'ಒಂದು ಉತ್ತರ: ಎಲ್ಲಿ, ಯಾವಾಗ, ಮತ್ತು ಎಷ್ಟು',
  },
  'sellplan.best_plan': { en: 'Your best plan', hi: 'आपकी सबसे अच्छी योजना', kn: 'ನಿಮ್ಮ ಅತ್ಯುತ್ತಮ ಯೋಜನೆ' },
  'sellplan.sell_today_at': { en: 'Sell today at', hi: 'आज यहाँ बेचें', kn: 'ಇಂದು ಇಲ್ಲಿ ಮಾರಿ' },
  'sellplan.sell_on': { en: 'Sell on', hi: 'इस दिन बेचें', kn: 'ಈ ದಿನ ಮಾರಿ' },
  'sellplan.hold_until': { en: 'Hold until', hi: 'इस दिन तक रोकें', kn: 'ಈ ದಿನದವರೆಗೆ ಇಡಿ' },
  'sellplan.at_mandi': { en: 'at', hi: 'यहाँ', kn: 'ಇಲ್ಲಿ' },
  'sellplan.vs_selling_today': {
    en: 'more than selling today, right here',
    hi: 'आज यहीं बेचने से ज़्यादा',
    kn: 'ಇಂದು ಇಲ್ಲೇ ಮಾರುವುದಕ್ಕಿಂತ ಹೆಚ್ಚು',
  },
  'sellplan.option_sell_today': { en: 'Sell today, here', hi: 'आज, यहीं बेचें', kn: 'ಇಂದು, ಇಲ್ಲೇ ಮಾರಿ' },
  'sellplan.option_wait': { en: 'Wait for a better day', hi: 'बेहतर दिन का इंतज़ार करें', kn: 'ಉತ್ತಮ ದಿನಕ್ಕಾಗಿ ಕಾಯಿರಿ' },
  'sellplan.option_travel': { en: 'Take it to another mandi', hi: 'दूसरी मंडी ले जाएँ', kn: 'ಬೇರೆ ಮಂಡಿಗೆ ಕೊಂಡೊಯ್ಯಿರಿ' },
  'sellplan.follow_this': { en: "I'll follow this plan", hi: 'मैं यह योजना अपनाऊँगा', kn: 'ನಾನು ಈ ಯೋಜನೆ ಅನುಸರಿಸುತ್ತೇನೆ' },
  'sellplan.saved_to_my_money': {
    en: 'Saved. Check My Money later to see how it went.',
    hi: 'सहेजा गया। बाद में "मेरा पैसा" में देखें कि क्या हुआ।',
    kn: 'ಉಳಿಸಲಾಗಿದೆ. ಇದು ಹೇಗಾಯಿತು ಎಂದು ನೋಡಲು ನಂತರ "ನನ್ನ ಹಣ" ನೋಡಿ.',
  },
  'sellplan.spoilage_note': {
    en: 'This crop spoils, so waiting has a cost too — already subtracted above.',
    hi: 'यह फसल खराब होती है, इसलिए रुकने की भी कीमत है — ऊपर पहले ही घटाई गई है।',
    kn: 'ಈ ಬೆಳೆ ಕೆಡುತ್ತದೆ, ಆದ್ದರಿಂದ ಕಾಯುವುದಕ್ಕೂ ಬೆಲೆ ಇದೆ — ಮೇಲೆ ಈಗಾಗಲೇ ಕಳೆಯಲಾಗಿದೆ.',
  },

  // ── my money ─────────────────────────────────────────────────────────────
  'mymoney.title': { en: 'My Money', hi: 'मेरा पैसा', kn: 'ನನ್ನ ಹಣ' },
  'mymoney.subtitle': {
    en: 'What following MandiSense earned you',
    hi: 'मंडीसेंस अपनाने से आपको क्या मिला',
    kn: 'ಮಂಡಿಸೆನ್ಸ್ ಅನುಸರಿಸಿದ್ದರಿಂದ ನಿಮಗೆ ಏನು ಸಿಕ್ಕಿತು',
  },
  'mymoney.total_saved': { en: 'Total earned by following advice', hi: 'सलाह मानकर कुल कमाई', kn: 'ಸಲಹೆ ಅನುಸರಿಸಿ ಗಳಿಸಿದ ಒಟ್ಟು ಮೊತ್ತ' },
  'mymoney.empty_title': { en: 'No plans saved yet', hi: 'अभी कोई योजना सहेजी नहीं गई', kn: 'ಇನ್ನೂ ಯಾವುದೇ ಯೋಜನೆ ಉಳಿಸಿಲ್ಲ' },
  'mymoney.empty_body': {
    en: 'Open "Plan my harvest sale" and tap "I\'ll follow this plan" to start tracking.',
    hi: '"मेरी फसल की बिक्री की योजना" खोलें और "मैं यह योजना अपनाऊँगा" दबाएँ।',
    kn: '"ನನ್ನ ಬೆಳೆ ಮಾರಾಟದ ಯೋಜನೆ" ತೆರೆದು "ನಾನು ಈ ಯೋಜನೆ ಅನುಸರಿಸುತ್ತೇನೆ" ಒತ್ತಿ.',
  },
  'mymoney.pending': { en: 'Waiting for the target date', hi: 'तय तारीख़ का इंतज़ार', kn: 'ಗುರಿ ದಿನಾಂಕದ ನಿರೀಕ್ಷೆ' },
  'mymoney.checking': { en: 'Checking actual mandi prices…', hi: 'असली मंडी भाव जाँचे जा रहे हैं…', kn: 'ನಿಜವಾದ ಮಂಡಿ ಬೆಲೆ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…' },
  'mymoney.not_verifiable': {
    en: 'No mandi record near that date to check against',
    hi: 'उस तारीख़ के आस-पास जाँचने के लिए कोई मंडी रिकॉर्ड नहीं',
    kn: 'ಆ ದಿನಾಂಕದ ಬಳಿ ಪರಿಶೀಲಿಸಲು ಯಾವುದೇ ಮಂಡಿ ದಾಖಲೆ ಇಲ್ಲ',
  },
  'mymoney.clear_all': { en: 'Clear history', hi: 'इतिहास साफ़ करें', kn: 'ಇತಿಹಾಸ ಅಳಿಸಿ' },
  'mymoney.disclaimer': {
    en: 'On-device only. Compares the plan against MandiSense’s own recorded mandi prices, not a promise of profit.',
    hi: 'केवल इस डिवाइस पर। योजना की तुलना मंडीसेंस के दर्ज मंडी भाव से होती है, यह मुनाफ़े की गारंटी नहीं।',
    kn: 'ಈ ಸಾಧನದಲ್ಲಿ ಮಾತ್ರ. ಯೋಜನೆಯನ್ನು ಮಂಡಿಸೆನ್ಸ್‌ನ ದಾಖಲಿತ ಮಂಡಿ ಬೆಲೆಗಳೊಂದಿಗೆ ಹೋಲಿಸಲಾಗುತ್ತದೆ, ಇದು ಲಾಭದ ಖಾತರಿ ಅಲ್ಲ.',
  },
};

export function translate(key: string, lang: Lang): string {
  const entry = TRANSLATIONS[key];
  if (!entry) return key;
  return entry[lang] || entry.en || key;
}
