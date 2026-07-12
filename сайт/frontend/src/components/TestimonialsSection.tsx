import { motion } from 'framer-motion';

import { TestimonialsColumn, type Testimonial } from '@/components/ui/testimonials-columns-1';
import { useLandingLanguage } from '@/i18n/LandingLanguageContext';

const LUMO_TESTIMONIALS: Testimonial[] = [
  {
    text: 'Очень удобный и действительно полезный бот. Всё работает быстро и понятно, без лишней путаницы. Благодаря Lumo легко находить каналы и возможности для участия.',
    name: 'Айдана',
  },
  {
    text: 'Жоско. Уже на 3 хакатона регнулся.',
    name: 'Alikhan',
  },
  {
    text: 'Довольно полезное для находок, не приходится искать через тт, соц. сети. Особенно для внеклассных активностей и по дедлайнам.',
    name: 'Asılım',
  },
  {
    text: 'Хорошее приложение. На пару каналов подписался благодаря вам.',
    name: 'Him',
  },
];

const leftColumn = [
  LUMO_TESTIMONIALS[0],
  LUMO_TESTIMONIALS[1],
  LUMO_TESTIMONIALS[2],
  LUMO_TESTIMONIALS[3],
];
const rightColumn = [
  LUMO_TESTIMONIALS[3],
  LUMO_TESTIMONIALS[0],
  LUMO_TESTIMONIALS[1],
  LUMO_TESTIMONIALS[2],
];

export function TestimonialsSection() {
  const { t } = useLandingLanguage();

  return (
    <section id="testimonials" className="px-5 py-24 md:py-32 border-t border-zinc-900 relative">
      <div className="container z-10 mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          viewport={{ once: true }}
          className="flex flex-col items-center justify-center max-w-[540px] mx-auto"
        >
          <div className="flex justify-center">
            <div className="border border-zinc-800 py-1 px-4 rounded-lg text-sm text-zinc-400">
              {t.testimonials.badge}
            </div>
          </div>

          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mt-5 text-center">
            {t.testimonials.title}
          </h2>
          <p className="text-center mt-5 text-zinc-400">{t.testimonials.subtitle}</p>
        </motion.div>

        <div className="flex justify-center gap-6 mt-10 [mask-image:linear-gradient(to_bottom,transparent,black_20%,black_80%,transparent)] max-h-[520px] overflow-hidden">
          <TestimonialsColumn testimonials={leftColumn} duration={18} variant="dark" />
          <TestimonialsColumn
            testimonials={rightColumn}
            className="hidden sm:block"
            duration={22}
            variant="dark"
          />
        </div>
      </div>
    </section>
  );
}
