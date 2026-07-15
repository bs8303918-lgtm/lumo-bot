import { useMediaQuery } from '@/hooks/use-media-query';
import { cn } from '@/lib/utils';
import NumberFlow from '@number-flow/react';
import { motion } from 'framer-motion';
import { Check, Star } from 'lucide-react';

export interface PricingPlan {
  name: string;
  price: number;
  period: string;
  features: string[];
  description: string;
  buttonText: string;
  href: string;
  isPopular: boolean;
}

export interface PricingProps {
  plans: PricingPlan[];
  title?: string;
  description?: string;
  variant?: 'light' | 'dark';
}

export function Pricing({
  plans,
  title = 'Тарифы',
  description = 'Начни бесплатно — апгрейд, когда понадобится больше.',
  variant = 'light',
}: PricingProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const isDark = variant === 'dark';

  return (
    <div className="container py-20 px-5">
      <div className="text-center space-y-4 mb-12">
        <h2
          className={cn(
            'text-3xl md:text-4xl font-bold tracking-tight',
            isDark ? 'gradient-heading' : 'text-foreground',
          )}
        >
          {title}
        </h2>
        <p
          className={cn(
            'text-lg whitespace-pre-line',
            isDark ? 'text-zinc-400' : 'text-muted-foreground',
          )}
        >
          {description}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-5xl mx-auto">
        {plans.map((plan, index) => (
          <motion.div
            key={plan.name}
            initial={{ y: 50, opacity: 1 }}
            whileInView={
              isDesktop
                ? {
                    y: plan.isPopular ? -16 : 0,
                    opacity: 1,
                    x: index === 2 ? -20 : index === 0 ? 20 : 0,
                    scale: index === 0 || index === 2 ? 0.96 : 1,
                  }
                : {}
            }
            viewport={{ once: true }}
            transition={{
              duration: 1.2,
              type: 'spring',
              stiffness: 100,
              damping: 30,
              delay: 0.2,
            }}
            className={cn(
              'rounded-2xl border p-7 text-center relative flex flex-col',
              isDark
                ? 'bg-zinc-900/70 border-zinc-800 backdrop-blur-sm'
                : 'bg-card',
              plan.isPopular
                ? isDark
                  ? 'border-sky-500/40 shadow-[0_0_40px_rgba(56,189,248,0.12)]'
                  : 'border-neutral-900 shadow-lg shadow-black/10'
                : isDark
                  ? 'border-zinc-800 hover:border-zinc-700'
                  : 'border-border hover:border-primary/30',
              !plan.isPopular && 'md:mt-4',
              plan.isPopular ? 'z-10' : 'z-0',
            )}
          >
            {plan.isPopular && (
              <div className="absolute top-0 right-0 bg-neutral-900 py-1 px-2.5 rounded-bl-xl rounded-tr-2xl flex items-center gap-1">
                <Star className="text-white h-3.5 w-3.5 fill-current" />
                <span className="text-white text-xs font-semibold">Популярный</span>
              </div>
            )}

            <div className="flex-1 flex flex-col">
              <p
                className={cn(
                  'text-sm font-semibold uppercase tracking-wide',
                  isDark ? 'text-zinc-400' : 'text-muted-foreground',
                )}
              >
                {plan.name}
              </p>

              <div className="mt-6 flex items-baseline justify-center gap-1">
                <span
                  className={cn(
                    'text-5xl font-bold tracking-tight',
                    isDark ? 'text-white' : 'text-foreground',
                  )}
                >
                  {plan.price === 0 ? (
                    '0'
                  ) : (
                    <NumberFlow
                      value={plan.price}
                      format={{
                        style: 'decimal',
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      }}
                      transformTiming={{ duration: 500, easing: 'ease-out' }}
                      willChange
                      className="tabular-nums"
                    />
                  )}
                </span>
                <span className={cn('text-lg font-semibold', isDark ? 'text-zinc-400' : 'text-muted-foreground')}>
                  ₸
                </span>
              </div>

              <p className={cn('text-sm mt-1', isDark ? 'text-zinc-500' : 'text-muted-foreground')}>
                / {plan.period}
              </p>

              <ul className="mt-6 gap-2.5 flex flex-col text-left">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5">
                    <Check
                      className={cn(
                        'h-4 w-4 mt-0.5 shrink-0',
                        isDark ? 'text-sky-400' : 'text-neutral-900',
                      )}
                    />
                    <span className={cn('text-sm', isDark ? 'text-zinc-300' : 'text-foreground/80')}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <hr className={cn('w-full my-5', isDark ? 'border-zinc-800' : 'border-border')} />

              <a
                href={plan.href}
                target={plan.href.startsWith('http') ? '_blank' : undefined}
                rel={plan.href.startsWith('http') ? 'noreferrer' : undefined}
                className={cn(
                  'inline-flex items-center justify-center w-full py-3.5 rounded-full font-semibold text-base transition-all',
                  plan.isPopular
                    ? 'bg-neutral-900 text-white hover:bg-neutral-800 shadow-md shadow-black/10'
                    : isDark
                      ? 'border border-zinc-700 bg-zinc-800/90 text-white hover:bg-zinc-700 hover:border-zinc-600'
                      : 'border border-border bg-muted text-foreground hover:bg-accent',
                )}
              >
                {plan.buttonText}
              </a>

              <p
                className={cn(
                  'mt-5 text-xs leading-relaxed',
                  isDark ? 'text-zinc-500' : 'text-muted-foreground',
                )}
              >
                {plan.description}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export const LUMO_PRICING_PLANS: PricingPlan[] = [
  {
    name: 'Бесплатно',
    price: 0,
    period: 'навсегда',
    features: [
      '3 AI-запроса',
      'Базовая подборка конкурсов',
      'Доступ к каталогу возможностей',
      'Обновления базы',
    ],
    description: 'Попробуй Lumo без карты',
    buttonText: 'Начать бесплатно',
    href: 'https://t.me/LumoAI1bot',
    isPopular: false,
  },
  {
    name: 'Старт',
    price: 4990,
    period: '3 месяца',
    features: [
      'Безлимитные AI-запросы',
      'Умные алерты о дедлайнах',
      '5 своих каналов для мониторинга',
      'Приоритетная подборка',
      'Профиль интересов',
    ],
    description: 'Для активного поиска возможностей',
    buttonText: 'Выбрать Старт',
    href: 'https://t.me/LumoAI1bot',
    isPopular: true,
  },
  {
    name: 'Про',
    price: 7990,
    period: '6 месяцев',
    features: [
      'Всё из тарифа Старт',
      'Расширенный профиль',
      'Ранний доступ к новым фичам',
      'Приоритетная поддержка',
      'Эксклюзивные подборки',
    ],
    description: 'Максимум возможностей на полгода',
    buttonText: 'Выбрать Про',
    href: 'https://t.me/LumoAI1bot',
    isPopular: false,
  },
];
