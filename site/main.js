const SECTION_CONFIG = [
  { key: 'papers', label: 'Papers' },
  { key: 'scholar', label: 'Pesquisas' },
  { key: 'news', label: 'Noticias' },
  { key: 'blogs', label: 'Blogs' },
];

const STORAGE_KEYS = {
  saved: 'ai_digest_saved_v1',
  history: 'ai_digest_history_v1',
};

const MAX_HISTORY_ITEMS = 240;
const MAX_SAVED_ITEMS = 120;

const state = {
  activeLibraryView: 'saved',
  currentItems: new Map(),
  savedItems: loadStore(STORAGE_KEYS.saved),
  historyItems: loadStore(STORAGE_KEYS.history),
};

const refs = {
  generatedAt: document.getElementById('generatedAt'),
  notes: document.getElementById('notes'),
  savedDockButton: document.getElementById('savedDockButton'),
  historyDockButton: document.getElementById('historyDockButton'),
  savedCount: document.getElementById('savedCount'),
  historyCount: document.getElementById('historyCount'),
  libraryPanel: document.getElementById('libraryPanel'),
  libraryBackdrop: document.getElementById('libraryBackdrop'),
  libraryTitle: document.getElementById('libraryTitle'),
  libraryEyebrow: document.getElementById('libraryEyebrow'),
  libraryHint: document.getElementById('libraryHint'),
  libraryList: document.getElementById('libraryList'),
  libraryEmpty: document.getElementById('libraryEmpty'),
  libraryClearButton: document.getElementById('libraryClearButton'),
  closeLibraryButton: document.getElementById('closeLibraryButton'),
  savedTabButton: document.getElementById('savedTabButton'),
  historyTabButton: document.getElementById('historyTabButton'),
};

initLibraryUi();
updateDockCounts();

loadDigest().catch((error) => {
  console.error(error);
  refs.generatedAt.textContent = 'erro ao carregar';
});

async function loadDigest() {
  const response = await fetch('./data/latest.json?ts=' + Date.now());
  const data = await response.json();

  refs.generatedAt.textContent = new Date(data.generated_at).toLocaleString('pt-BR');
  refs.notes.innerHTML = '';
  state.currentItems = new Map();

  const allItems = [];
  for (const section of SECTION_CONFIG) {
    const items = (data[section.key] || []).map((item) => normalizeItem(item, section.label, data.generated_at));
    items.forEach((item) => {
      state.currentItems.set(item.id, item);
      allItems.push(item);
    });
    renderCards(section.key, items);
  }

  refreshSavedItemsFromCurrentDigest();
  mergeHistoryItems(allItems, data.generated_at);
  renderNotes(data.notes || []);
  syncSaveButtons();

  if (isLibraryOpen()) {
    renderLibrary();
  }
}

function initLibraryUi() {
  refs.savedDockButton.addEventListener('click', () => openLibrary('saved'));
  refs.historyDockButton.addEventListener('click', () => openLibrary('history'));
  refs.savedTabButton.addEventListener('click', () => openLibrary('saved'));
  refs.historyTabButton.addEventListener('click', () => openLibrary('history'));
  refs.closeLibraryButton.addEventListener('click', closeLibrary);
  refs.libraryBackdrop.addEventListener('click', closeLibrary);
  refs.libraryClearButton.addEventListener('click', clearActiveLibraryView);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isLibraryOpen()) {
      closeLibrary();
    }
  });

  refs.savedDockButton.addEventListener('dragover', handleSavedDockDragOver);
  refs.savedDockButton.addEventListener('dragenter', handleSavedDockDragOver);
  refs.savedDockButton.addEventListener('dragleave', clearSavedDockDropTarget);
  refs.savedDockButton.addEventListener('drop', handleSavedDockDrop);
}

function normalizeItem(item, sectionLabel, generatedAt) {
  const title = item.title || 'Sem titulo';
  const url = item.url || '#';
  const id = buildItemId(item.type || sectionLabel, url, title);

  return {
    id,
    title,
    url,
    source: item.source || item.type || sectionLabel,
    type: item.type || sectionLabel.toLowerCase(),
    section: sectionLabel,
    summary: item.summary || '',
    authors: Array.isArray(item.authors) ? item.authors : [],
    published_at: item.published_at || null,
    publication_summary: item.publication_summary || '',
    cited_by_total: item.cited_by_total || null,
    versions_total: item.versions_total || null,
    scholar_url: item.scholar_url || null,
    scholar_url_label: item.scholar_url_label || null,
    generated_at: generatedAt,
  };
}

function renderCards(targetId, items) {
  const root = document.getElementById(targetId);
  root.innerHTML = '';

  items.forEach((item) => {
    root.appendChild(createCardElement(item));
  });
}

function createCardElement(item) {
  const card = element('article', 'card');
  card.draggable = true;
  card.dataset.itemId = item.id;

  const pill = element('div', 'pill', item.source || item.type);
  const title = element('h3');
  const titleLink = element('a');
  titleLink.href = item.url;
  titleLink.target = '_blank';
  titleLink.rel = 'noreferrer';
  titleLink.textContent = item.title;
  title.appendChild(titleLink);

  const summary = element('p', '', item.summary || '');
  const footer = element('div', 'footer', formatMeta(item));
  const actions = createCardActions(item);

  card.append(pill, title, summary, footer, actions);

  card.addEventListener('dragstart', handleCardDragStart);
  card.addEventListener('dragend', handleCardDragEnd);

  return card;
}

function createCardActions(item) {
  const actions = element('div', 'actions');

  const saveButton = element('button', 'action-button', isSaved(item.id) ? 'Salvo' : 'Salvar');
  saveButton.type = 'button';
  saveButton.dataset.saveButton = 'true';
  saveButton.dataset.itemId = item.id;
  if (isSaved(item.id)) {
    saveButton.classList.add('is-saved');
  }
  saveButton.addEventListener('click', () => toggleSavedItem(item.id));
  actions.appendChild(saveButton);

  if (item.scholar_url) {
    const scholarLink = element('a', 'action-link', item.scholar_url_label || 'Abrir no Google Academico');
    scholarLink.href = item.scholar_url;
    scholarLink.target = '_blank';
    scholarLink.rel = 'noreferrer';
    actions.appendChild(scholarLink);
  }

  return actions;
}

function renderNotes(notes) {
  refs.notes.innerHTML = '';
  notes.forEach((note) => {
    const listItem = document.createElement('li');
    listItem.textContent = note;
    refs.notes.appendChild(listItem);
  });
}

function openLibrary(view) {
  state.activeLibraryView = view;
  document.body.classList.add('is-library-open');
  refs.libraryPanel.classList.add('is-open');
  refs.libraryPanel.setAttribute('aria-hidden', 'false');
  refs.libraryBackdrop.hidden = false;
  refs.libraryBackdrop.classList.add('is-visible');
  renderLibrary();
}

function closeLibrary() {
  document.body.classList.remove('is-library-open');
  refs.libraryPanel.classList.remove('is-open');
  refs.libraryPanel.setAttribute('aria-hidden', 'true');
  refs.libraryBackdrop.classList.remove('is-visible');
  refs.libraryBackdrop.hidden = true;
}

function isLibraryOpen() {
  return refs.libraryPanel.classList.contains('is-open');
}

function renderLibrary() {
  const isSavedView = state.activeLibraryView === 'saved';
  const items = isSavedView ? state.savedItems : state.historyItems;

  refs.libraryEyebrow.textContent = isSavedView ? 'Biblioteca pessoal' : 'Arquivo automatico';
  refs.libraryTitle.textContent = isSavedView ? 'Salvos' : 'Historico';
  refs.libraryHint.textContent = isSavedView
    ? 'Arraste um card para o icone de salvos ou use o botao Salvar no card.'
    : 'O historico guarda automaticamente os itens que ja apareceram no digest neste navegador.';
  refs.libraryClearButton.textContent = isSavedView ? 'Limpar salvos' : 'Limpar historico';

  refs.savedTabButton.classList.toggle('is-active', isSavedView);
  refs.savedTabButton.setAttribute('aria-selected', String(isSavedView));
  refs.historyTabButton.classList.toggle('is-active', !isSavedView);
  refs.historyTabButton.setAttribute('aria-selected', String(!isSavedView));

  refs.libraryList.innerHTML = '';

  if (!items.length) {
    refs.libraryEmpty.hidden = false;
    refs.libraryEmpty.textContent = isSavedView
      ? 'Nenhum item salvo ainda. Arraste um card para o icone de salvos.'
      : 'O historico ainda esta vazio neste navegador.';
    return;
  }

  refs.libraryEmpty.hidden = true;
  items.forEach((item) => {
    refs.libraryList.appendChild(createLibraryItem(item, isSavedView));
  });
}

function createLibraryItem(item, isSavedView) {
  const card = element('article', 'library-card');

  const top = element('div', 'library-card-top');
  const badge = element('span', 'library-badge', item.section || item.source || 'Item');
  const meta = element('span', 'library-meta-line', formatLibraryMeta(item, isSavedView));
  top.append(badge, meta);

  const title = element('h3', 'library-card-title');
  const titleLink = element('a');
  titleLink.href = item.url;
  titleLink.target = '_blank';
  titleLink.rel = 'noreferrer';
  titleLink.textContent = item.title;
  title.appendChild(titleLink);

  const summary = element('p', 'library-card-summary', truncate(item.summary || item.publication_summary || '', 220));

  const actions = element('div', 'library-card-actions');
  const openLink = element('a', 'action-link', 'Abrir');
  openLink.href = item.url;
  openLink.target = '_blank';
  openLink.rel = 'noreferrer';
  actions.appendChild(openLink);

  if (item.scholar_url) {
    const scholarLink = element('a', 'action-link', item.scholar_url_label || 'Google Academico');
    scholarLink.href = item.scholar_url;
    scholarLink.target = '_blank';
    scholarLink.rel = 'noreferrer';
    actions.appendChild(scholarLink);
  }

  if (isSavedView) {
    const removeButton = element('button', 'action-button', 'Remover');
    removeButton.type = 'button';
    removeButton.addEventListener('click', () => {
      removeSavedItem(item.id);
    });
    actions.appendChild(removeButton);
  } else {
    const saveButton = element('button', 'action-button', isSaved(item.id) ? 'Salvo' : 'Salvar');
    saveButton.type = 'button';
    if (isSaved(item.id)) {
      saveButton.classList.add('is-saved');
    }
    saveButton.addEventListener('click', () => {
      toggleSavedItem(item.id);
      renderLibrary();
    });
    actions.appendChild(saveButton);
  }

  card.append(top, title, summary, actions);
  return card;
}

function formatLibraryMeta(item, isSavedView) {
  const parts = [];

  if (item.source) {
    parts.push(item.source);
  }
  if (item.published_at) {
    parts.push(new Date(item.published_at).toLocaleDateString('pt-BR'));
  }
  if (isSavedView && item.saved_at) {
    parts.push('Salvo em ' + new Date(item.saved_at).toLocaleDateString('pt-BR'));
  }
  if (!isSavedView && item.last_seen_at) {
    parts.push('Visto em ' + new Date(item.last_seen_at).toLocaleDateString('pt-BR'));
  }
  if (!isSavedView && item.seen_count) {
    parts.push(item.seen_count + ' aparicoes');
  }

  return parts.join(' · ');
}

function toggleSavedItem(itemId) {
  if (isSaved(itemId)) {
    removeSavedItem(itemId);
  } else {
    addSavedItemById(itemId);
  }
}

function addSavedItemById(itemId) {
  const item = state.currentItems.get(itemId) || state.historyItems.find((entry) => entry.id === itemId);
  if (!item || isSaved(itemId)) {
    syncSaveButtons();
    return;
  }

  state.savedItems = [
    {
      ...item,
      saved_at: new Date().toISOString(),
    },
    ...state.savedItems,
  ].slice(0, MAX_SAVED_ITEMS);

  saveStore(STORAGE_KEYS.saved, state.savedItems);
  updateDockCounts();
  syncSaveButtons();

  if (state.activeLibraryView === 'saved' && isLibraryOpen()) {
    renderLibrary();
  }
}

function removeSavedItem(itemId) {
  state.savedItems = state.savedItems.filter((item) => item.id !== itemId);
  saveStore(STORAGE_KEYS.saved, state.savedItems);
  updateDockCounts();
  syncSaveButtons();

  if (isLibraryOpen()) {
    renderLibrary();
  }
}

function isSaved(itemId) {
  return state.savedItems.some((item) => item.id === itemId);
}

function mergeHistoryItems(items, generatedAt) {
  const itemsById = new Map(state.historyItems.map((item) => [item.id, item]));

  items.forEach((item) => {
    const existing = itemsById.get(item.id);
    if (!existing) {
      itemsById.set(item.id, {
        ...item,
        first_seen_at: generatedAt,
        last_seen_at: generatedAt,
        seen_count: 1,
      });
      return;
    }

    itemsById.set(item.id, {
      ...existing,
      ...item,
      first_seen_at: existing.first_seen_at || generatedAt,
      last_seen_at: generatedAt,
      seen_count: existing.last_seen_at === generatedAt ? existing.seen_count : (existing.seen_count || 1) + 1,
      saved_at: existing.saved_at,
    });
  });

  state.historyItems = Array.from(itemsById.values())
    .sort((left, right) => new Date(right.last_seen_at || 0) - new Date(left.last_seen_at || 0))
    .slice(0, MAX_HISTORY_ITEMS);

  saveStore(STORAGE_KEYS.history, state.historyItems);
  updateDockCounts();
}

function refreshSavedItemsFromCurrentDigest() {
  state.savedItems = state.savedItems.map((item) => {
    const currentItem = state.currentItems.get(item.id);
    if (!currentItem) {
      return item;
    }

    return {
      ...item,
      ...currentItem,
      saved_at: item.saved_at,
    };
  });

  saveStore(STORAGE_KEYS.saved, state.savedItems);
}

function clearActiveLibraryView() {
  if (state.activeLibraryView === 'saved') {
    state.savedItems = [];
    saveStore(STORAGE_KEYS.saved, state.savedItems);
    syncSaveButtons();
  } else {
    state.historyItems = [];
    saveStore(STORAGE_KEYS.history, state.historyItems);
  }

  updateDockCounts();
  renderLibrary();
}

function updateDockCounts() {
  refs.savedCount.textContent = String(state.savedItems.length);
  refs.historyCount.textContent = String(state.historyItems.length);
}

function syncSaveButtons() {
  document.querySelectorAll('[data-save-button]').forEach((button) => {
    const itemId = button.dataset.itemId;
    const saved = isSaved(itemId);
    button.textContent = saved ? 'Salvo' : 'Salvar';
    button.classList.toggle('is-saved', saved);
  });
}

function handleCardDragStart(event) {
  const itemId = event.currentTarget.dataset.itemId;
  event.dataTransfer.effectAllowed = 'copy';
  event.dataTransfer.setData('text/plain', itemId);
  document.body.classList.add('is-dragging-card');
}

function handleCardDragEnd() {
  document.body.classList.remove('is-dragging-card');
  clearSavedDockDropTarget();
}

function handleSavedDockDragOver(event) {
  event.preventDefault();
  refs.savedDockButton.classList.add('is-drop-target');
}

function clearSavedDockDropTarget() {
  refs.savedDockButton.classList.remove('is-drop-target');
}

function handleSavedDockDrop(event) {
  event.preventDefault();
  clearSavedDockDropTarget();
  document.body.classList.remove('is-dragging-card');

  const itemId = event.dataTransfer.getData('text/plain');
  if (!itemId) {
    return;
  }

  addSavedItemById(itemId);
  openLibrary('saved');
}

function loadStore(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || '[]');
  } catch (error) {
    console.warn('Nao foi possivel ler o storage', key, error);
    return [];
  }
}

function saveStore(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function buildItemId(type, url, title) {
  return [type || 'item', url || title || 'sem-url'].join('::');
}

function formatMeta(item) {
  const parts = [];

  if (item.published_at) {
    parts.push(new Date(item.published_at).toLocaleDateString('pt-BR'));
  }
  if (item.authors && item.authors.length) {
    parts.push(item.authors.slice(0, 3).join(', '));
  }
  if (item.publication_summary) {
    parts.push(truncate(item.publication_summary, 90));
  }
  if (item.cited_by_total) {
    parts.push('Citado por ' + item.cited_by_total);
  }
  if (item.versions_total) {
    parts.push(item.versions_total + ' versoes');
  }

  return parts.join(' · ');
}

function truncate(value, maxLength) {
  if (!value || value.length <= maxLength) {
    return value || '';
  }
  return value.slice(0, maxLength - 1) + '...';
}

function element(tagName, className, textContent) {
  const node = document.createElement(tagName);
  if (className) {
    node.className = className;
  }
  if (typeof textContent === 'string') {
    node.textContent = textContent;
  }
  return node;
}
