import { useEffect, useRef } from 'react';
import { saveGoogleAuth } from '../api.js';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export default function GoogleLoginButton({ onAuth, text = 'signup_with', width = 280 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!CLIENT_ID) return undefined;

    window.handleGoogleCredential = (response) => {
      const idToken = response?.credential;
      if (!idToken) return;

      const payload = JSON.parse(atob(idToken.split('.')[1]));
      saveGoogleAuth({
        idToken,
        email: payload.email,
        name: payload.name,
        picture: payload.picture,
      });
      onAuth?.(payload);
    };

    const render = () => {
      const container = containerRef.current;
      if (!container || !window.google?.accounts?.id) return;

      container.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: window.handleGoogleCredential,
        auto_select: false,
      });
      window.google.accounts.id.renderButton(container, {
        type: 'standard',
        theme: 'outline',
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
      delete window.handleGoogleCredential;
    };
  }, [onAuth, text, width]);

  if (!CLIENT_ID) {
    return (
      <p className="text-xs text-muted-foreground text-center px-2">
        Google не настроен: добавь VITE_GOOGLE_CLIENT_ID на Vercel
      </p>
    );
  }

  return <div ref={containerRef} className="flex justify-center min-h-[44px]" />;
}
