import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import CatalogPreview from './CatalogPreview.jsx';
import './index.css';

// Тест карточек из базы Lumo. Чтобы вернуть макет с мок-данными — импорт App вместо CatalogPreview.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CatalogPreview />
  </StrictMode>,
);
