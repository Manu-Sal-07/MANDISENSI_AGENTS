/**
 * Layer 3: Service Infrastructure - Logging Prep
 * Purpose: Centralized logging utility for system monitoring.
 */

type LogLevel = 'info' | 'warn' | 'error' | 'debug';

export const logger = {
  logInfo: (message: string, context?: any): void => {
    log('info', message, context);
  },

  logWarn: (message: string, context?: any): void => {
    log('warn', message, context);
  },

  logError: (message: string, context?: any): void => {
    log('error', message, context);
  },

  logDebug: (message: string, context?: any): void => {
    if (process.env.NODE_ENV === 'development') {
      log('debug', message, context);
    }
  }
};

function log(level: LogLevel, message: string, context?: any): void {
  const timestamp = new Date().toISOString();
  const formattedMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;

  switch (level) {
    case 'info':
      console.log(formattedMessage, context || '');
      break;
    case 'warn':
      console.warn(formattedMessage, context || '');
      break;
    case 'error':
      console.error(formattedMessage, context || '');
      break;
    case 'debug':
      console.debug(formattedMessage, context || '');
      break;
  }
}
