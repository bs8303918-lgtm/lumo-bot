import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { clearAuth, isAuthenticated, syncSession } from './api.js';
import Landing from './Landing.jsx';

export default function HomeRoute() {
  const [target, setTarget] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!isAuthenticated()) {
        if (!cancelled) setTarget('landing');
        return;
      }
      try {
        await syncSession();
        if (!cancelled) setTarget('app');
      } catch {
        clearAuth();
        if (!cancelled) setTarget('landing');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (target === 'app') return <Navigate to="/app" replace />;
  if (target === 'landing') return <Landing />;
  return (
    <div className="min-h-screen bg-white flex items-center justify-center text-neutral-400 text-sm">
      Загрузка…
    </div>
  );
}
