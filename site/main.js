async function loadDigest() {
  const res = await fetch('./data/latest.json?ts=' + Date.now());
  const data = await res.json();

  document.getElementById('generatedAt').textContent = new Date(data.generated_at).toLocaleString('pt-BR');
  renderCards('papers', data.papers);
  renderCards('scholar', data.scholar);
  renderCards('news', data.news);
  renderCards('blogs', data.blogs);

  const notes = document.getElementById('notes');
  notes.innerHTML = '';
  (data.notes || []).forEach((note) => {
    const li = document.createElement('li');
    li.textContent = note;
    notes.appendChild(li);
  });
}

function renderCards(targetId, items) {
  const root = document.getElementById(targetId);
  root.innerHTML = '';

  items.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'card';
    card.innerHTML = `
      <div class="pill">${item.source || item.type}</div>
      <h3><a href="${item.url}" target="_blank" rel="noreferrer">${item.title}</a></h3>
      <p>${item.summary || ''}</p>
      <div class="footer">${formatMeta(item)}</div>
      ${renderActions(item)}
    `;
    root.appendChild(card);
  });
}

function renderActions(item) {
  if (!item.scholar_url) {
    return '';
  }
  return `
    <div class="actions">
      <a href="${item.scholar_url}" target="_blank" rel="noreferrer">${item.scholar_url_label || 'Abrir no Google Acadêmico'}</a>
    </div>
  `;
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
    parts.push(`Citado por ${item.cited_by_total}`);
  }
  if (item.versions_total) {
    parts.push(`${item.versions_total} versões`);
  }
  return parts.join(' · ');
}

function truncate(value, maxLength) {
  if (!value || value.length <= maxLength) {
    return value || '';
  }
  return value.slice(0, maxLength - 1) + '…';
}

loadDigest().catch((err) => {
  console.error(err);
  document.getElementById('generatedAt').textContent = 'erro ao carregar';
});
