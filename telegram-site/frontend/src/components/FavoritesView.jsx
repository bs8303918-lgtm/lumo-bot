import { useState } from 'react';
import { Heart } from 'lucide-react';
import { loadFavorites, toggleFavorite } from '../utils/localFeatures';
import OpportunityCard from './OpportunityCard';

export default function FavoritesView({ onOpenItem }) {
  const [favorites, setFavorites] = useState(() => loadFavorites());

  return (
    <div className="pb-8">
      <header className="mb-5">
        <h1 className="text-[22px] font-bold mb-2">Избранное</h1>
        <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Возможности, которые ты сохранил себе
        </p>
      </header>

      {favorites.length === 0 ? (
        <div className="flex flex-col items-center py-16 text-center">
          <Heart size={28} style={{ color: 'var(--lumo-text-muted)' }} className="mb-3" />
          <p className="text-[13px] max-w-[240px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Пока пусто — нажми на сердечко на карточке в каталоге, чтобы сохранить сюда
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {favorites.map((item) => (
            <OpportunityCard
              key={item.id}
              item={item}
              onOpen={onOpenItem}
              isFavorite
              onToggleFavorite={(it) => setFavorites(toggleFavorite(it))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
