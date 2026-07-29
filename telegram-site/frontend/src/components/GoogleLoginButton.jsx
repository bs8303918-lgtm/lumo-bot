import { useEffect, useRef } from 'react';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export default function GoogleLoginButton({ onCredential, text = 'continue_with', width = 280 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!CLIENT_ID) return undefined;

    window.handleLumoMiniAppGoogleCredential = (response) => {
      const idToken = response?.credential;
      if (idToken) onCredential?.(idToken);
    };

    const render = () => {
      const container = containerRef.current;
      if (!container || !window.google?.accounts?.id) return;

      container.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: window.handleLumoMiniAppGoogleCredential,
        auto_select: false,
      });
      window.google.accounts.id.renderButton(container, {
        type: 'standard',
        theme: 'filled_black',
        size: 'large',
        text,
        width,
        shape: 'pill',
      });
    };

    if (window.google?.accounts?.id) {
      render();
    } else {
      const existing = document.querySelector('script[data-lumo-google-gsi]');
      if (!existing) {
        const script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.dataset.lumoGoogleGsi = '1';
        script.onload = render;
        document.head.appendChild(script);
      } else {
        existing.addEventListener('load', render);
      }
    }

    return () => {
      delete window.handleLumoMiniAppGoogleCredential;
    };
  }, [onCredential, text, width]);

  if (!CLIENT_ID) {
    return (
      <p className="text-[12px] text-center px-2" style={{ color: 'var(--lumo-text-muted)' }}>
        Google Sign-In не настроен: добавь VITE_GOOGLE_CLIENT_ID на Vercel
      </p>
    );
  }

  return <div ref={containerRef} className="flex justify-center min-h-[44px]" />;
}
