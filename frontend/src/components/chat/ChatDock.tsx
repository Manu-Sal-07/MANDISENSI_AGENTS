'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { MessageCircle } from 'lucide-react';

import ChatPanel from '@/components/chat/ChatPanel';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { CHAT_UI } from '@/lib/i18n/chatCopy';
import { isDeskRoute, isFarmRoute } from '@/lib/surfaces';
import type { ChatLang } from '@/services/chatApi';
import { useDeskFocus } from '@/store/deskFocus';

const TRADER_LANG_KEY = 'mandisense-chat-trader-lang';

/**
 * The chatbot launcher, mounted once in the root layout. On farmer pages it opens
 * the farm assistant in the app's language; on the trading desk it opens the desk
 * assistant with its own language choice. The Command Center keeps its own copilot
 * panel, so no launcher is shown there.
 */
export default function ChatDock() {
  const pathname = usePathname();
  const reduce = useReducedMotion();
  const { lang: farmLang } = useLanguage();
  const { district, crop, mandi } = useFarm();
  const { commodity, mandiId } = useDeskFocus();
  const [open, setOpen] = useState(false);
  const [traderLang, setTraderLang] = useState<ChatLang>('en');

  const farm = isFarmRoute(pathname);
  const desk = !farm && isDeskRoute(pathname) && !pathname?.startsWith('/terminal');

  useEffect(() => {
    try {
      const saved = localStorage.getItem(TRADER_LANG_KEY);
      if (saved === 'en' || saved === 'kn' || saved === 'hi') setTraderLang(saved);
    } catch {
      /* default stays English */
    }
  }, []);
  useEffect(() => setOpen(false), [pathname]);

  const changeTraderLang = (l: ChatLang) => {
    setTraderLang(l);
    try {
      localStorage.setItem(TRADER_LANG_KEY, l);
    } catch {
      /* not remembered */
    }
  };

  const farmContext = useMemo(() => ({ district, crop, ...(mandi ? { mandi_id: mandi } : {}) }), [district, crop, mandi]);
  const deskContext = useMemo(() => ({ crop: commodity, mandi_id: mandiId }), [commodity, mandiId]);

  if (!farm && !desk) return null;
  const lang: ChatLang = farm ? (farmLang as ChatLang) : traderLang;
  const persona = farm ? 'farmer' : 'trader';

  return (
    <>
      <AnimatePresence>
        {open && (
          <ChatPanel
            key={persona}
            persona={persona}
            variant={farm ? 'farm' : 'desk'}
            lang={lang}
            onLangChange={farm ? undefined : changeTraderLang}
            context={farm ? farmContext : deskContext}
            onClose={() => setOpen(false)}
          />
        )}
      </AnimatePresence>

      {!open && (
        <motion.button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={CHAT_UI.open[lang]}
          initial={reduce ? false : { opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          whileTap={{ scale: 0.95 }}
          className={`chat-fab ${farm ? 'chat-fab-farm' : 'chat-fab-desk'} farm-focus fixed bottom-[5.9rem] right-4 z-[60] flex h-14 items-center gap-2.5 rounded-full pl-4 pr-5 md:bottom-6 md:right-6`}
        >
          <MessageCircle className="h-6 w-6" />
          <span className="text-[15px] font-extrabold">{CHAT_UI.open[lang]}</span>
        </motion.button>
      )}
    </>
  );
}
