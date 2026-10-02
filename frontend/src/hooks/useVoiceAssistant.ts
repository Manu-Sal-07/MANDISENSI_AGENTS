'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Speech recognition and text-to-speech, in whichever language the farmer
 * has selected.
 *
 * Built on the browser's own Web Speech API rather than a server-side
 * speech service: it costs nothing per call, needs no API key, and runs
 * entirely on-device, which matters for a rural connection where every
 * extra network round trip is a place the feature can fail silently. The
 * honest trade-off is stated rather than hidden: Kannada speech-to-text
 * support is inconsistent across Android browsers and near-absent on iOS
 * Safari, so `isSupported` is checked and surfaced rather than assumed --
 * a farmer on an unsupported device sees a plain text box, not a broken
 * microphone button.
 */

type SpeechRecognitionResultLike = {
  results: { 0: { transcript: string }; isFinal: boolean; length: number }[];
};

interface UseVoiceAssistantOptions {
  locale: string;
  onResult?: (transcript: string) => void;
}

export function useVoiceAssistant({ locale, onResult }: UseVoiceAssistantOptions) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const onResultRef = useRef(onResult);
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  const recognitionSupported =
    typeof window !== 'undefined' &&
    Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  const synthesisSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  useEffect(() => {
    return () => {
      try {
        recognitionRef.current?.stop();
        window.speechSynthesis?.cancel();
      } catch {
        // Best-effort cleanup only.
      }
    };
  }, []);

  const startListening = useCallback(() => {
    if (!recognitionSupported) {
      setError('not_supported');
      return;
    }
    setError(null);
    setTranscript('');

    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new Recognition();
    recognition.lang = locale;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: SpeechRecognitionResultLike) => {
      const said = event.results[event.results.length - 1]?.[0]?.transcript ?? '';
      setTranscript(said);
      onResultRef.current?.(said);
    };
    recognition.onerror = () => {
      setError('recognition_failed');
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    setIsListening(true);
    try {
      recognition.start();
    } catch {
      setIsListening(false);
      setError('recognition_failed');
    }
  }, [locale, recognitionSupported]);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      // Already stopped.
    }
    setIsListening(false);
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!synthesisSupported || !text) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = locale;
      utterance.rate = 0.95;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    },
    [locale, synthesisSupported]
  );

  const stopSpeaking = useCallback(() => {
    try {
      window.speechSynthesis?.cancel();
    } catch {
      // Nothing to cancel.
    }
    setIsSpeaking(false);
  }, []);

  return {
    isListening,
    isSpeaking,
    transcript,
    error,
    isRecognitionSupported: recognitionSupported,
    isSynthesisSupported: synthesisSupported,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  };
}
