import React from 'react';
import { motion } from 'framer-motion';
import { User } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface Testimonial {
  text: string;
  name?: string;
  role?: string;
  image?: string;
}

function TestimonialAvatar({ name, isDark }: { name?: string; isDark?: boolean }) {
  const initial = name?.trim()?.charAt(0)?.toUpperCase();
  return (
    <div
      className={cn(
        'h-10 w-10 rounded-full shrink-0 flex items-center justify-center border',
        isDark
          ? 'bg-zinc-800 border-zinc-700 text-zinc-300'
          : 'bg-neutral-100 border-neutral-200 text-neutral-700',
      )}
      aria-hidden
    >
      {initial ? (
        <span className="text-sm font-semibold">{initial}</span>
      ) : (
        <User size={18} className="text-zinc-500" />
      )}
    </div>
  );
}

export function TestimonialsColumn(props: {
  className?: string;
  testimonials: Testimonial[];
  duration?: number;
  variant?: 'light' | 'dark';
}) {
  const isDark = props.variant === 'dark';

  return (
    <div className={props.className}>
      <motion.div
        animate={{ translateY: '-50%' }}
        transition={{
          duration: props.duration || 10,
          repeat: Infinity,
          ease: 'linear',
          repeatType: 'loop',
        }}
        className="flex flex-col gap-6 pb-6"
      >
        {[...new Array(2).fill(0).map((_, index) => (
          <React.Fragment key={index}>
            {props.testimonials.map(({ text, name, role }, i) => (
              <div
                key={`${index}-${i}`}
                className={cn(
                  'p-8 rounded-3xl border max-w-xs w-full',
                  isDark
                    ? 'border-zinc-800 bg-zinc-900/70 shadow-lg shadow-sky-500/5 text-zinc-200'
                    : 'border-neutral-200 bg-white shadow-md shadow-black/[0.04] text-neutral-800',
                )}
              >
                <div className="text-sm leading-relaxed">{text}</div>
                {(name || role) && (
                  <div className="flex items-center gap-2 mt-5">
                    <TestimonialAvatar name={name} isDark={isDark} />
                    <div className="flex flex-col min-w-0">
                      {name && (
                        <div className="font-medium tracking-tight leading-5 truncate">{name}</div>
                      )}
                      {role && (
                        <div
                          className={cn(
                            'leading-5 tracking-tight text-sm truncate',
                            isDark ? 'text-zinc-500' : 'opacity-60',
                          )}
                        >
                          {role}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </React.Fragment>
        ))]}
      </motion.div>
    </div>
  );
}
