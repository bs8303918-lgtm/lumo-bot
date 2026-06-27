import { X } from 'lucide-react';

import { apiFetch, getTelegram, haptic } from '../api';

import { formatDeadlineMeta, sourceHandle } from '../utils/deadline';

import { itemTags } from '../utils/categories';
import TagChips from './TagChips';



function trackClick(catalogId, type) {

  if (!catalogId) return;

  apiFetch('/lumo/track-click', {

    method: 'POST',

    body: JSON.stringify({ type, catalogId }),

  }).catch(() => {});

}



function openTrackedLink(url, catalogId, type) {

  if (!url) return;

  haptic('light');

  trackClick(catalogId, type);

  const tg = getTelegram();
  const isTelegram = /t\.me\/|telegram\.me\//i.test(url);
  if (isTelegram && tg?.openTelegramLink) tg.openTelegramLink(url);
  else if (tg?.openLink) tg.openLink(url);
  else window.open(url, '_blank');

}



export default function DetailModal({ item, onClose }) {

  if (!item) return null;



  const tags = itemTags(item);

  const deadline = formatDeadlineMeta(item.deadline);

  const handle = sourceHandle(item);



  return (

    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/60 backdrop-blur-sm">

      <div className="lumo-card w-full sm:max-w-lg max-h-[90vh] overflow-y-auto rounded-t-[24px] sm:rounded-[24px] p-6 relative">

        <button

          type="button"

          onClick={onClose}

          className="absolute top-5 right-5 opacity-60 hover:opacity-100"

          aria-label="Закрыть"

        >

          <X size={22} />

        </button>



        <div className="flex items-start justify-between gap-3 mb-3 pr-8">
          <h3 className="text-xl font-bold leading-snug">{item.title}</h3>
          <TagChips tags={tags} />
        </div>



        <p className="text-[14px] mb-5 leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>

          {item.description}

        </p>



        <div className="text-[14px] space-y-2.5 mb-6">

          <p className="flex items-center gap-2" style={{ color: deadline.urgent ? 'var(--lumo-urgent)' : 'var(--lumo-text)' }}>

            <span style={{ color: 'var(--lumo-text-muted)' }}>Дедлайн:</span> {deadline.label}

          </p>

          <p>

            <span style={{ color: 'var(--lumo-text-muted)' }}>Канал:</span> {item.sourceChannelName}

            {handle && (

              <span className="ml-2" style={{ color: 'var(--lumo-link)' }}>

                {handle}

              </span>

            )}

          </p>

          {item.requirements && (

            <p>

              <span style={{ color: 'var(--lumo-text-muted)' }}>Требования:</span> {item.requirements}

            </p>

          )}

          {item.applicationUrl && (

            <p>

              <span style={{ color: 'var(--lumo-text-muted)' }}>Заявка:</span>{' '}

              <button

                type="button"

                className="break-all text-left underline"

                style={{ color: 'var(--lumo-link)' }}

                onClick={() => openTrackedLink(item.applicationUrl, item.id, 'apply')}

              >

                Открыть

              </button>

            </p>

          )}

          {item.messageLink && (

            <p>

              <span style={{ color: 'var(--lumo-text-muted)' }}>Пост:</span>{' '}

              <button

                type="button"

                className="underline"

                style={{ color: 'var(--lumo-link)' }}

                onClick={() => openTrackedLink(item.messageLink, item.id, 'telegram')}

              >

                Telegram

              </button>

            </p>

          )}

        </div>



        <div className="grid grid-cols-2 gap-2 mb-3">

          {item.applicationUrl && (

            <button

              type="button"

              onClick={() => openTrackedLink(item.applicationUrl, item.id, 'apply')}

              className="py-3 rounded-xl font-bold text-white text-[13px]"

              style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)' }}

            >

              Подать заявку

            </button>

          )}

          {item.messageLink && (

            <button

              type="button"

              onClick={() => openTrackedLink(item.messageLink, item.id, 'telegram')}

              className={`py-3 rounded-xl font-bold text-[13px] ${

                item.applicationUrl ? '' : 'col-span-2'

              }`}

              style={{ background: 'var(--lumo-accent-soft)', color: 'var(--lumo-accent)' }}

            >

              Открыть в Telegram

            </button>

          )}

        </div>



        <button type="button" onClick={onClose} className="w-full py-3.5 rounded-xl font-bold lumo-btn-primary">

          Закрыть

        </button>

      </div>

    </div>

  );

}


