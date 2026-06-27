import { useEffect, useState } from 'react';
import {
  PlayCircle,
  Lock,
  CheckCircle,
  ChevronRight,
  X,
  Search,
  Sparkles,
} from 'lucide-react';

const API = '/api';

export default function App() {
  const [isPaywallOpen, setIsPaywallOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [grants, setGrants] = useState([]);
  const [services, setServices] = useState([]);
  const [course, setCourse] = useState(null);
  const [banner, setBanner] = useState(null);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedGrant, setSelectedGrant] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/meta`).then((r) => r.json()),
      fetch(`${API}/banner`).then((r) => r.json()),
      fetch(`${API}/services`).then((r) => r.json()),
      fetch(`${API}/courses`).then((r) => r.json()),
    ]).then(([metaData, bannerData, servicesData, coursesData]) => {
      setMeta(metaData);
      setBanner(bannerData);
      setServices(servicesData);
      setCourse(coursesData[0] ?? null);
    });
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true);
      const params = searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : '';
      const res = await fetch(`${API}/grants${params}`);
      const data = await res.json();
      setGrants(data);
      setLoading(false);
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const openGrant = async (grant) => {
    const res = await fetch(`${API}/grants/${grant.id}`);
    const detail = await res.json();
    setSelectedGrant(detail);
    if (detail.isPremium || detail.isLocked) {
      setIsPaywallOpen(true);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-[#e2e8f0] p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
              {meta?.title ?? 'AI Startify Grants'}
            </h1>
            <p className="text-slate-400 mt-2">
              {meta?.subtitle ?? 'Витрина возможностей'} от{' '}
              <a
                href={meta?.communityUrl ?? 'https://t.me/opportunities_zula'}
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 hover:underline"
              >
                {meta?.communityHandle ?? '@opportunities_zula'}
              </a>
            </p>
          </div>

          <div className="relative w-full md:w-96">
            <input
              type="text"
              placeholder="Поиск грантов..."
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-12 text-sm focus:outline-none focus:border-indigo-500 transition-all"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <main className="lg:col-span-8 space-y-6">
            {banner && (
              <div className="relative p-[1px] rounded-3xl bg-gradient-to-r from-indigo-600 to-purple-600 mb-8 shadow-lg shadow-indigo-500/10">
                <div className="bg-[#0f172a] rounded-[23px] p-6 flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-400 border border-indigo-500/20">
                      <Sparkles size={24} />
                    </div>
                    <div>
                      <h3 className="font-bold text-white">{banner.title}</h3>
                      <p className="text-sm text-slate-400">{banner.subtitle}</p>
                    </div>
                  </div>
                  <a
                    href={banner.ctaUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-xl text-sm font-bold transition shadow-lg shadow-indigo-600/20"
                  >
                    {banner.ctaLabel}
                  </a>
                </div>
              </div>
            )}

            {loading ? (
              <div className="text-center text-slate-500 py-20">Загрузка грантов...</div>
            ) : grants.length === 0 ? (
              <div className="text-center text-slate-500 py-20">Ничего не найдено</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {grants.map((grant) => (
                  <div
                    key={grant.id}
                    className="group bg-white/5 border border-white/5 rounded-3xl overflow-hidden flex flex-col hover:border-indigo-500/40 transition-all duration-300"
                  >
                    <div className="p-7 flex-grow">
                      <div className="flex justify-between items-start mb-5">
                        <div className="flex items-center gap-3">
                          <span className="text-3xl">{grant.flag}</span>
                          <span className="text-[11px] font-bold uppercase tracking-widest text-slate-500">
                            {grant.location}
                          </span>
                        </div>
                        <span
                          className={`text-[10px] px-3 py-1.5 rounded-xl uppercase font-black ${
                            grant.isPremium
                              ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'
                              : 'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}
                        >
                          {grant.deadline}
                        </span>
                      </div>

                      <h2 className="text-xl font-bold mb-3 text-white group-hover:text-indigo-400 transition-colors">
                        {grant.title}
                      </h2>
                      <p className="text-sm text-slate-400 line-clamp-3 mb-6">{grant.description}</p>

                      <div className="space-y-2">
                        {grant.features.map((feat, i) => (
                          <div key={i} className="flex items-center gap-3 text-sm text-slate-300">
                            <CheckCircle size={16} className="text-indigo-500" />
                            <span>{feat}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-7 pt-0">
                      <button
                        onClick={() => openGrant(grant)}
                        className="w-full py-4 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-bold transition border border-white/10"
                      >
                        {grant.isPremium ? 'Разблокировать детали' : 'Подробнее'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </main>

          <aside className="lg:col-span-4">
            <div className="sticky top-8 space-y-6">
              {course && (
                <div className="bg-white/5 border border-indigo-500/30 p-8 rounded-[32px] backdrop-blur-xl">
                  <div className="text-indigo-400 mb-6">
                    <PlayCircle size={32} />
                  </div>
                  <h4 className="text-xl font-bold mb-2 text-white">{course.title}</h4>
                  <p className="text-sm text-slate-400 mb-6 leading-relaxed">{course.description}</p>
                  <div className="text-3xl font-bold mb-6 text-white tracking-tighter">{course.price}</div>
                  <button className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold transition shadow-lg shadow-indigo-600/20">
                    Купить
                  </button>
                </div>
              )}

              <div className="bg-white/5 border border-white/10 p-6 rounded-[32px]">
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 px-2">
                  Услуги
                </h4>
                <div className="space-y-2">
                  {services.map((service) => (
                    <ExpertService key={service.id} title={service.title} price={service.price} />
                  ))}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      {isPaywallOpen && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-indigo-500/40 max-w-md w-full p-10 rounded-[40px] shadow-2xl relative text-center">
            <button
              onClick={() => setIsPaywallOpen(false)}
              className="absolute top-6 right-6 text-slate-500 hover:text-white transition"
            >
              <X size={24} />
            </button>
            <div className="w-20 h-20 bg-indigo-500/10 rounded-3xl flex items-center justify-center text-indigo-400 mx-auto mb-8">
              <Lock size={40} />
            </div>
            <h3 className="text-2xl font-bold mb-4 text-white">
              {selectedGrant?.isLocked ? 'Контент заблокирован' : selectedGrant?.title}
            </h3>
            {selectedGrant?.isLocked ? (
              <p className="text-slate-400 mb-8 leading-relaxed">
                Прямые ссылки и шаблоны документов доступны только участникам комьюнити.
              </p>
            ) : (
              <div className="text-left text-sm text-slate-300 mb-8 space-y-3">
                {selectedGrant?.premiumContent?.applicationUrl && (
                  <p>
                    <span className="text-slate-500">Ссылка:</span>{' '}
                    <a
                      href={selectedGrant.premiumContent.applicationUrl}
                      className="text-indigo-400 hover:underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Подать заявку
                    </a>
                  </p>
                )}
                {selectedGrant?.premiumContent?.requirements && (
                  <p>
                    <span className="text-slate-500">Требования:</span>{' '}
                    {selectedGrant.premiumContent.requirements}
                  </p>
                )}
                {selectedGrant?.premiumContent?.documentTemplates?.length > 0 && (
                  <div>
                    <span className="text-slate-500">Шаблоны:</span>
                    <ul className="mt-1 list-disc list-inside">
                      {selectedGrant.premiumContent.documentTemplates.map((doc) => (
                        <li key={doc}>{doc}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            {selectedGrant?.isLocked ? (
              <a
                href={meta?.communityUrl ?? 'https://t.me/opportunities_zula'}
                target="_blank"
                rel="noreferrer"
                className="block w-full py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold transition mb-4"
              >
                Получить доступ
              </a>
            ) : (
              <button
                onClick={() => setIsPaywallOpen(false)}
                className="w-full py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold transition mb-4"
              >
                Закрыть
              </button>
            )}
            <button
              onClick={() => setIsPaywallOpen(false)}
              className="text-xs text-slate-600 font-bold hover:text-slate-400 uppercase tracking-widest"
            >
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ExpertService({ title, price }) {
  return (
    <button className="w-full p-4 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/5 text-left transition group flex justify-between items-center">
      <span className="text-sm font-medium text-white">{title}</span>
      <span className="text-sm font-bold flex items-center gap-1">
        {price} <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
      </span>
    </button>
  );
}
