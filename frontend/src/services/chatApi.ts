import { apiClient } from './api';

export type ChatPersona = 'farmer' | 'trader';
export type ChatLang = 'en' | 'kn' | 'hi';

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatContext {
  district?: string;
  crop?: string;
  mandi_id?: string;
  last_entities?: Record<string, unknown>;
}

export interface ChatSource {
  title: string;
  url: string;
}

export interface ToolUse {
  tool: string;
  args: Record<string, unknown>;
  ok: boolean;
}

export interface ChatReply {
  reply: string;
  lang: ChatLang;
  /** 'llm' when a hosted model wrote it, 'tools' for the tool-driven answer. */
  mode: 'llm' | 'tools';
  provider: string;
  note: string | null;
  intent: string;
  sources: ChatSource[];
  tools_used: ToolUse[];
  grounded: boolean;
  ungrounded_numbers: number[];
  context: Record<string, unknown>;
  suggestions: string[];
}

export const chatApi = {
  send: (body: { persona: ChatPersona; message: string; lang: ChatLang; history: ChatTurn[]; context: ChatContext }, signal?: AbortSignal) =>
    apiClient<ChatReply>('/v1/chat', { method: 'POST', body: JSON.stringify(body), signal }),
};
