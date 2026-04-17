async function loadDigest() {
  const res = await fetch('./data/latest.json?ts=' + Date.now());
  const data = await res.json();

  document.getElementById('generatedAt').textContent = new Date(data.generated_at).toLocaleString('pt-BR');
  renderCards('papers', data.papers);
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
    `;
    root.appendChild(card);
  });
}

function formatMeta(item) {
  const parts = [];
  if (item.published_at) {
    parts.push(new Date(item.published_at).toLocaleDateString('pt-BR'));
  }
  if (item.authors && item.authors.length) {
    parts.push(item.authors.slice(0, 3).join(', '));
  }
  return parts.join(' · ');
}

loadDigest().catch((err) => {
  console.error(err);
  document.getElementById('generatedAt').textContent = 'erro ao carregar';
});
