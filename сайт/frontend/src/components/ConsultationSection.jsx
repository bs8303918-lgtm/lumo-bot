import { useState } from 'react';
import { Loader2 } from 'lucide-react';

import { apiFetch } from '../api.js';
import { useLandingLanguage } from '@/i18n/LandingLanguageContext';

export default function ConsultationSection() {
  const { t } = useLandingLanguage();
  const c = t.consultation;

  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [interest, setInterest] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const contactVal = contact.trim();
    if (!contactVal || contactVal.length < 3) {
      setError(c.contactError);
      return;
    }
    const interestLabel = c.interests.find((i) => i.id === interest)?.label || interest || '—';

    setLoading(true);
    setError(null);
    try {
      await apiFetch('/leads/contact', {
        method: 'POST',
        auth: false,
        body: JSON.stringify({
          name: name.trim() || undefined,
          contact: contactVal,
          message: `Консультация с лендинга. Интерес: ${interestLabel}`,
        }),
      });
      setDone(true);
      setName('');
      setContact('');
      setInterest('');
    } catch (err) {
      setError(err.message || c.submitError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="consultation" className="px-5 py-24 md:py-32 bg-neutral-950 text-white">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-[clamp(1.75rem,4vw,2.75rem)] font-bold leading-tight tracking-tight mb-5">
          {c.title}
          <br />
          <span className="font-serif italic font-normal text-white/95">{c.titleAccent}</span>
        </h2>
        <p className="text-neutral-400 text-base md:text-lg leading-relaxed mb-10 max-w-2xl mx-auto">
          {c.subtitle}
        </p>

        {done ? (
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-6 py-5 text-emerald-300 text-sm md:text-base">
            {c.success}
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3 text-left">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={c.namePlaceholder}
                maxLength={120}
                className="w-full px-4 py-3.5 rounded-xl bg-neutral-800/80 border border-neutral-700 text-white placeholder:text-neutral-500 focus:outline-none focus:border-neutral-500"
              />
              <input
                type="text"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder={c.contactPlaceholder}
                required
                className="w-full px-4 py-3.5 rounded-xl bg-neutral-800/80 border border-neutral-700 text-white placeholder:text-neutral-500 focus:outline-none focus:border-neutral-500"
              />
              <select
                value={interest}
                onChange={(e) => setInterest(e.target.value)}
                className="w-full px-4 py-3.5 rounded-xl bg-neutral-800/80 border border-neutral-700 text-white focus:outline-none focus:border-neutral-500 appearance-none"
              >
                <option value="">{c.interestPlaceholder}</option>
                {c.interests.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            {error && <p className="text-red-400 text-sm text-center">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-base transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : null}
              {c.button}
            </button>
          </form>
        )}

        <p className="mt-6 text-sm text-neutral-500">
          {c.contactHint}{' '}
          <a
            href="https://t.me/LumoAI1bot"
            target="_blank"
            rel="noreferrer"
            className="text-neutral-300 hover:text-white underline underline-offset-2"
          >
            {c.telegram}
          </a>
        </p>
      </div>
    </section>
  );
}
