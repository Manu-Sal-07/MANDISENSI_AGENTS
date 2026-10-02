import type { ChatLang, ChatPersona } from '@/services/chatApi';

/**
 * Every fixed string in the chat UI, in the three languages. The bot's own
 * answers come from the server already written in the chosen language; these
 * are only the controls, the greeting and the error messages around them.
 */
type Row = Record<ChatLang, string>;

const row = (en: string, kn: string, hi: string): Row => ({ en, kn, hi });

export const CHAT_UI = {
  open: row('Ask MandiSense', 'ಮಂಡಿಸೆನ್ಸ್ ಕೇಳಿ', 'मंडीसेंस से पूछें'),
  close: row('Close chat', 'ಚಾಟ್ ಮುಚ್ಚಿ', 'चैट बंद करें'),
  clear: row('Clear chat', 'ಚಾಟ್ ಅಳಿಸಿ', 'चैट साफ़ करें'),
  send: row('Send', 'ಕಳುಹಿಸಿ', 'भेजें'),
  speak: row('Speak', 'ಮಾತನಾಡಿ', 'बोलिए'),
  listening: row('Listening…', 'ಕೇಳುತ್ತಿದೆ…', 'सुन रहा है…'),
  readAloud: row('Read aloud', 'ಗಟ್ಟಿಯಾಗಿ ಓದಿ', 'ज़ोर से पढ़ें'),
  thinking: row('Checking the records…', 'ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದೆ…', 'रिकॉर्ड देख रहा है…'),
  error: row('I could not reach the server. Please try again.', 'ಸರ್ವರ್ ತಲುಪಲು ಆಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', 'सर्वर तक नहीं पहुँच सका। कृपया फिर कोशिश करें।'),
  retry: row('Try again', 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ', 'फिर कोशिश करें'),
  sources: row('Sources', 'ಮೂಲಗಳು', 'स्रोत'),
  checked: row('Checked', 'ಪರಿಶೀಲಿಸಿದ್ದು', 'जाँचा गया'),
  unverified: row('Some figures could not be verified against the records.', 'ಕೆಲವು ಅಂಕಿಗಳನ್ನು ದಾಖಲೆಗಳೊಂದಿಗೆ ಪರಿಶೀಲಿಸಲು ಆಗಲಿಲ್ಲ.', 'कुछ आँकड़े रिकॉर्ड से जाँचे नहीं जा सके।'),
  modeLlm: row('AI + records + live web', 'AI + ದಾಖಲೆ + ಲೈವ್ ವೆಬ್', 'AI + रिकॉर्ड + लाइव वेब'),
  modeTools: row('Records + live web', 'ದಾಖಲೆ + ಲೈವ್ ವೆಬ್', 'रिकॉर्ड + लाइव वेब'),
  disclaimer: row('Advice is guidance, not a guarantee.', 'ಸಲಹೆ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ಖಾತರಿಯಲ್ಲ.', 'सलाह मार्गदर्शन है, गारंटी नहीं।'),
  language: row('Language', 'ಭಾಷೆ', 'भाषा'),
} as const;

export const CHAT_TITLE: Record<ChatPersona, Row> = {
  farmer: row('Farm assistant', 'ಕೃಷಿ ಸಹಾಯಕ', 'खेती सहायक'),
  trader: row('Desk assistant', 'ಡೆಸ್ಕ್ ಸಹಾಯಕ', 'डेस्क सहायक'),
};

export const CHAT_PLACEHOLDER: Record<ChatPersona, Row> = {
  farmer: row('Ask about your crop…', 'ನಿಮ್ಮ ಬೆಳೆಯ ಬಗ್ಗೆ ಕೇಳಿ…', 'अपनी फसल के बारे में पूछें…'),
  trader: row('Ask about spreads, volatility, forward prices…', 'ಅಂತರ, ಏರಿಳಿತ, ಫಾರ್ವರ್ಡ್ ಬೆಲೆ ಬಗ್ಗೆ ಕೇಳಿ…', 'स्प्रेड, अस्थिरता, फ़ॉरवर्ड भाव के बारे में पूछें…'),
};

export const CHAT_GREETING: Record<ChatPersona, Row> = {
  farmer: row(
    'Namaste! Ask me what your crop is worth, whether to hold or sell, which mandi pays best, last year’s price or the weather. I can also search the web for schemes, MSP, fertiliser and pests.',
    'ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಬೆಳೆಗೆ ಎಷ್ಟು ಬೆಲೆ, ಹಿಡಿದಿಡಬೇಕೇ ಮಾರಬೇಕೇ, ಯಾವ ಮಂಡಿಯಲ್ಲಿ ಹೆಚ್ಚು ಬೆಲೆ, ಕಳೆದ ವರ್ಷದ ಬೆಲೆ, ಹವಾಮಾನ ಕೇಳಿ. ಯೋಜನೆಗಳು, ಬೆಂಬಲ ಬೆಲೆ, ಗೊಬ್ಬರ, ಕೀಟಗಳ ಬಗ್ಗೆಯೂ ವೆಬ್‌ನಲ್ಲಿ ಹುಡುಕುತ್ತೇನೆ.',
    'नमस्ते! पूछिए कि फसल का भाव क्या है, रोकें या बेचें, कौन-सी मंडी सबसे अच्छी, पिछले साल का भाव या मौसम। योजनाओं, एमएसपी, खाद और कीटों के लिए वेब पर भी खोजता हूँ।',
  ),
  trader: row(
    'Ask me to run the desk tools: mandi spreads, district gaps, volatility regime, analogs, scenarios, forward prices or a decision brief. I can also search the web for policy and news.',
    'ಡೆಸ್ಕ್ ಸಾಧನಗಳನ್ನು ಚಲಾಯಿಸಲು ಕೇಳಿ: ಮಂಡಿ ಅಂತರ, ಜಿಲ್ಲಾ ಅಂತರ, ಏರಿಳಿತ ಸ್ಥಿತಿ, ಹೋಲಿಕೆಗಳು, ಸನ್ನಿವೇಶಗಳು, ಫಾರ್ವರ್ಡ್ ಬೆಲೆ ಅಥವಾ ನಿರ್ಧಾರ ಸಾರಾಂಶ. ನೀತಿ ಮತ್ತು ಸುದ್ದಿಗಾಗಿ ವೆಬ್‌ನಲ್ಲೂ ಹುಡುಕುತ್ತೇನೆ.',
    'डेस्क के टूल चलवाइए: मंडी स्प्रेड, ज़िलों का अंतर, अस्थिरता, समानताएँ, परिदृश्य, फ़ॉरवर्ड भाव या निर्णय संक्षेप। नीति और समाचार के लिए वेब पर भी खोजता हूँ।',
  ),
};

export const CHAT_STARTERS: Record<ChatPersona, Row[]> = {
  farmer: [
    row('What is my crop worth today?', 'ಇಂದು ನನ್ನ ಬೆಳೆಗೆ ಎಷ್ಟು ಬೆಲೆ?', 'आज मेरी फसल का भाव क्या है?'),
    row('Should I hold or sell?', 'ಹಿಡಿದಿಡಲೇ ಅಥವಾ ಮಾರಲೇ?', 'रोकूँ या बेचूँ?'),
    row('Which mandi pays best?', 'ಯಾವ ಮಂಡಿಯಲ್ಲಿ ಹೆಚ್ಚು ಬೆಲೆ?', 'कौन-सी मंडी सबसे अच्छा भाव देती है?'),
    row('Will it rain this week?', 'ಈ ವಾರ ಮಳೆ ಬರುತ್ತದೆಯೇ?', 'इस हफ़्ते बारिश होगी?'),
  ],
  trader: [
    row('Is the tomato spread worth the trip?', 'ಟೊಮೇಟೊ ಮಂಡಿ ಅಂತರ ಪ್ರಯಾಣಕ್ಕೆ ಯೋಗ್ಯವೇ?', 'क्या टमाटर का स्प्रेड सफ़र लायक है?'),
    row('What is the volatility regime?', 'ಏರಿಳಿತ ಸ್ಥಿತಿ ಏನು?', 'अस्थिरता की स्थिति क्या है?'),
    row('Which scenarios are active?', 'ಯಾವ ಸನ್ನಿವೇಶಗಳು ಸಕ್ರಿಯ?', 'कौन-से परिदृश्य सक्रिय हैं?'),
    row('Latest onion export policy?', 'ಈರುಳ್ಳಿ ರಫ್ತು ನೀತಿ ಏನು?', 'प्याज़ निर्यात नीति क्या है?'),
  ],
};

/** Friendly names for the tools shown under an answer. */
export const TOOL_LABEL: Record<string, Row> = {
  get_price_board: row('price board', 'ಬೆಲೆ ಫಲಕ', 'भाव बोर्ड'),
  get_district_overview: row('district overview', 'ಜಿಲ್ಲಾ ಸಾರಾಂಶ', 'ज़िला सारांश'),
  get_sell_plan: row('sell plan', 'ಮಾರಾಟ ಯೋಜನೆ', 'बिक्री योजना'),
  get_hold_or_sell: row('hold or sell', 'ಹಿಡಿಯಿರಿ ಅಥವಾ ಮಾರಿ', 'रोकें या बेचें'),
  get_where_to_sell: row('where to sell', 'ಎಲ್ಲಿ ಮಾರಬೇಕು', 'कहाँ बेचें'),
  get_seasonal_memory: row('last year', 'ಕಳೆದ ವರ್ಷ', 'पिछला साल'),
  get_supply_signal: row('arrivals', 'ಆವಕ', 'आवक'),
  get_track_record: row('track record', 'ದಾಖಲೆ ಫಲಿತಾಂಶ', 'ट्रैक रिकॉर्ड'),
  get_accuracy: row('accuracy', 'ನಿಖರತೆ', 'सटीकता'),
  get_crop_planning: row('crop planning', 'ಬೆಳೆ ಯೋಜನೆ', 'फसल योजना'),
  get_price_on_date: row('past price', 'ಹಿಂದಿನ ಬೆಲೆ', 'पुराना भाव'),
  check_fair_price: row('fair price', 'ನ್ಯಾಯಯುತ ಬೆಲೆ', 'उचित भाव'),
  get_mandi_page: row('mandi prices', 'ಮಂಡಿ ಬೆಲೆಗಳು', 'मंडी भाव'),
  list_places: row('places', 'ಸ್ಥಳಗಳು', 'स्थान'),
  scan_spreads: row('mandi spreads', 'ಮಂಡಿ ಅಂತರ', 'मंडी स्प्रेड'),
  gap_arbitrage: row('gap arbitrage', 'ಅಂತರ ಅವಕಾಶ', 'गैप आर्बिट्रेज'),
  get_volatility: row('volatility', 'ಏರಿಳಿತ', 'अस्थिरता'),
  get_analogs: row('analogs', 'ಹೋಲಿಕೆಗಳು', 'समानताएँ'),
  run_scenarios: row('scenarios', 'ಸನ್ನಿವೇಶಗಳು', 'परिदृश्य'),
  get_forward_price: row('forward price', 'ಫಾರ್ವರ್ಡ್ ಬೆಲೆ', 'फ़ॉरवर्ड भाव'),
  get_transmission_matrix: row('transmission', 'ಪ್ರಸರಣ', 'संचरण'),
  get_decision_brief: row('decision brief', 'ನಿರ್ಧಾರ ಸಾರಾಂಶ', 'निर्णय संक्षेप'),
  web_search: row('web search', 'ವೆಬ್ ಹುಡುಕಾಟ', 'वेब खोज'),
  fetch_url: row('web page', 'ವೆಬ್ ಪುಟ', 'वेब पेज'),
  get_weather: row('weather', 'ಹವಾಮಾನ', 'मौसम'),
  calculator: row('calculator', 'ಕ್ಯಾಲ್ಕುಲೇಟರ್', 'कैलकुलेटर'),
};

export const SPEECH_LOCALE: Record<ChatLang, string> = { en: 'en-IN', kn: 'kn-IN', hi: 'hi-IN' };
