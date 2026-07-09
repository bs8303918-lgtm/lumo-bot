import { useEffect, useRef, useState } from 'react';

import { apiFetch, isAuthenticated } from '../api.js';

import ChatInput from './ChatInput.jsx';

import OpportunityCard from './OpportunityCard.jsx';



export default function ChatView({ onOpenItem, onOpenPricing, onNeedsAuth }) {

  const scrollRef = useRef(null);

  const [input, setInput] = useState('');

  const [loading, setLoading] = useState(false);

  const [messages, setMessages] = useState([]);



  useEffect(() => {

    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });

  }, [messages, loading]);



  const submit = async (text = input) => {

    const query = text.trim();

    if (query.length < 3 || loading) return;



    if (!isAuthenticated()) {

      onNeedsAuth?.();

      return;

    }



    setInput('');

    setLoading(true);

    setMessages((prev) => [...prev, { role: 'user', content: query }]);



    try {

      const data = await apiFetch('/lumo/match', {

        method: 'POST',

        body: JSON.stringify({ query }),

      });

      setMessages((prev) => [

        ...prev,

        {

          role: 'assistant',

          content: data.message,

          items: data.items ?? [],

          categories: data.categories ?? [],

        },

      ]);

    } catch (err) {

      if (err.needsAuth) {

        onNeedsAuth?.();

        setMessages((prev) => prev.slice(0, -1));

        return;

      }

      setMessages((prev) => [

        ...prev,

        {

          role: 'assistant',

          content: err.message || 'Что-то пошло не так. Попробуй ещё раз.',

          error: true,

          showPricing: err.showPricing,

        },

      ]);

    } finally {

      setLoading(false);

    }

  };



  const isEmpty = messages.length === 0;



  if (isEmpty) {

    return (

      <div className="flex flex-col h-full min-h-0 items-center justify-center px-4 pb-6">

        <div className="w-full max-w-2xl text-center mb-8">

          <h1 className="text-[1.75rem] md:text-[2rem] font-semibold text-foreground tracking-tight mb-3">

            Какой конкурс, грант или стажировку ищешь?

          </h1>

          <p className="text-muted-foreground text-[15px]">

            Опиши запрос — Lumo подберёт возможности из базы

          </p>

        </div>



        <div className="w-full max-w-2xl">

          <ChatInput

            value={input}

            onChange={setInput}

            onSubmit={() => submit()}

            loading={loading}

            placeholder="Например: гранты для IT-стартапа, 1 курс, Казахстан…"

          />

        </div>

      </div>

    );

  }



  return (

    <div className="flex flex-col h-full min-h-0">

      <div ref={scrollRef} className="flex-1 overflow-y-auto">

        <div className="max-w-3xl mx-auto px-4 md:px-6 py-8 space-y-8">

          {messages.map((msg, i) => (

            <div key={i}>

              {msg.role === 'user' ? (

                <div className="flex justify-end">

                  <div className="max-w-[85%] md:max-w-xl px-4 py-3 rounded-3xl bg-muted text-foreground text-[15px] leading-relaxed">

                    {msg.content}

                  </div>

                </div>

              ) : (

                <div className="space-y-4">

                  <p className={`text-[15px] leading-relaxed ${msg.error ? 'text-red-500' : 'text-foreground'}`}>

                    {msg.content}

                  </p>



                  {msg.categories?.length > 0 && (

                    <div className="flex flex-wrap gap-2">

                      {msg.categories.map((cat) => (

                        <span

                          key={cat.type}

                          className="text-xs px-3 py-1 rounded-full bg-muted text-muted-foreground"

                        >

                          {cat.emoji} {cat.label}

                        </span>

                      ))}

                    </div>

                  )}



                  {msg.items?.length > 0 ? (

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">

                      {msg.items.map((item) => (

                        <OpportunityCard key={item.id} item={item} onOpen={onOpenItem} />

                      ))}

                    </div>

                  ) : !msg.error ? (

                    <p className="text-sm text-muted-foreground">

                      Попробуй уточнить запрос или{' '}

                      <button type="button" onClick={onOpenPricing} className="underline hover:text-foreground">

                        посмотри тарифы

                      </button>

                    </p>

                  ) : msg.showPricing ? (

                    <button type="button" onClick={onOpenPricing} className="text-sm underline text-primary">

                      Открыть тарифы

                    </button>

                  ) : null}

                </div>

              )}

            </div>

          ))}



          {loading && (

            <p className="text-sm text-muted-foreground animate-pulse">Lumo ищет…</p>

          )}

        </div>

      </div>



      <div className="shrink-0 px-4 md:px-6 pb-5 pt-2">

        <div className="max-w-3xl mx-auto">

          <ChatInput

            value={input}

            onChange={setInput}

            onSubmit={() => submit()}

            loading={loading}

            placeholder="Уточни запрос…"

            compact

          />

        </div>

      </div>

    </div>

  );

}

