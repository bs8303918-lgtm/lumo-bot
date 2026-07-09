import { useEffect, useRef } from 'react';
import { saveTelegramLogin } from '../api.js';
import { BOT_USERNAME } from '../constants.js';

export default function TelegramLoginButton({ onAuth, size = 'medium' }) {
  const containerRef = useRef(null);

  useEffect(() => {
    window.onTelegramAuth = (user) => {
      saveTelegramLogin(user);
      onAuth?.(user);
    };

    const container = containerRef.current;
    if (!container) return;

    container.innerHTML = '';
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', BOT_USERNAME);
    script.setAttribute('data-size', size);
    script.setAttribute('data-radius', '20');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    script.setAttribute('data-request-access', 'write');
    container.appendChild(script);

    return () => {
      delete window.onTelegramAuth;
    };
  }, [onAuth, size]);

  return <div ref={containerRef} className="inline-flex min-h-[40px] items-center" />;
}
