/* Componente genérico de CRUD seguindo as recomendações de layout da N2:
   a) tabela inicia vazia          b) dados via BUSCA ou TODOS    c) TODOS => status=ATIVO
   d) indexação (ordenação) por coluna   e) busca por mais de um elemento
   f) ações Editar / Excluir (lógico)    g) CREATE: status oculto = ATIVO
   h) UPDATE: status oculto              i) DELETE: status => INATIVO                     */

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const brl = v => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dataBR = v => v ? String(v).slice(0, 10).split('-').reverse().join('/') : '—';

function toast(msg, ok = true) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'show ' + (ok ? 'ok' : 'err');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.className = '', 3500);
}

async function api(url, method = 'GET', body) {
  const r = await fetch(url, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map(x => x.msg).join('; ') : (d || 'Erro na requisição'));
  }
  return data;
}

function createCrud(cfg) {
  const root = document.getElementById(cfg.view);
  let rows = [], sortKey = null, sortDir = 1, editing = null, lookups = {};

  const searchHtml = cfg.search.map(f => f.options
    ? `<div><label>${f.label}</label><select data-s="${f.name}"><option value="">Todos</option>${f.options.map(o => `<option>${o}</option>`).join('')}</select></div>`
    : `<div><label>${f.label}</label><input data-s="${f.name}" type="${f.type || 'text'}" placeholder="${f.placeholder || ''}"></div>`).join('');

  root.innerHTML = `
    <div class="card">
      <h1 class="title">${cfg.title}</h1>
      <p class="subtitle">${cfg.subtitle}</p>
      <form class="row" data-r="form">
        ${searchHtml}
        <div><label>Status</label><select data-s="status"><option value="ATIVO">ATIVO</option><option value="INATIVO">INATIVO</option><option value="TODOS">ATIVO + INATIVO</option></select></div>
        <div class="toolbar" style="margin:0"><button class="btn blue" type="submit">🔍 Buscar</button></div>
      </form>
      <div class="toolbar">
        <button class="btn secondary" data-r="todos">📋 TODOS (ativos)</button>
        <button class="btn secondary" data-r="limpar">✖ Limpar</button>
        <span class="spacer"></span>
        <button class="btn" data-r="novo">＋ Novo</button>
      </div>
      <div class="table-wrap"><table class="grid">
        <thead><tr>${cfg.columns.map(c => `<th data-k="${c.key}">${c.label}<span class="arrow"></span></th>`).join('')}<th class="noindex">Ações</th></tr></thead>
        <tbody data-r="body"></tbody>
      </table></div>
      <div class="count" data-r="count"></div>
    </div>
    <div class="modal-bg" data-r="modal"><form class="modal" data-r="mform"><h2 data-r="mtitle"></h2><div data-r="fields"></div>
      <div class="toolbar"><span class="spacer"></span><button type="button" class="btn secondary" data-r="cancel">Cancelar</button><button class="btn" type="submit">Salvar</button></div></form></div>`;

  const $ = s => root.querySelector(`[data-r="${s}"]`);
  const body = $('body');

  function renderTable() {
    const data = [...rows];
    if (sortKey) data.sort((a, b) => {
      const x = a[sortKey] ?? '', y = b[sortKey] ?? '';
      return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'pt-BR', { numeric: true })) * sortDir;
    });
    root.querySelectorAll('th[data-k]').forEach(th => th.querySelector('.arrow').textContent = th.dataset.k === sortKey ? (sortDir > 0 ? '▲' : '▼') : '⇅');
    if (!data.length) { body.innerHTML = `<tr><td class="empty" colspan="${cfg.columns.length + 1}">${cfg._loaded ? 'Nenhum registro encontrado.' : 'Use a busca ou o botão TODOS para carregar os registros.'}</td></tr>`; $('count').textContent = ''; return; }
    body.innerHTML = data.map(r => `<tr class="${r.status === 'INATIVO' ? 'inativo' : ''}">
      ${cfg.columns.map(c => `<td>${c.fmt ? c.fmt(r[c.key], r) : (c.key === 'status' ? `<span class="badge ${r.status === 'ATIVO' ? 'ok' : 'off'}">${r.status}</span>` : esc(r[c.key]))}</td>`).join('')}
      <td><div class="acoes">
        <button class="btn sm blue" data-a="edit" data-id="${r.id}">✏️ Editar</button>
        ${r.status === 'INATIVO'
          ? `<button class="btn sm warn" data-a="react" data-id="${r.id}">↺ Reativar</button>`
          : `<button class="btn sm danger" data-a="del" data-id="${r.id}">🗑 Excluir</button>`}
      </div></td></tr>`).join('');
    $('count').textContent = `${data.length} registro(s)`;
  }

  async function load(params) {
    const qs = new URLSearchParams(params);
    if (cfg.fixed) Object.entries(cfg.fixed).forEach(([k, v]) => qs.set(k, v));
    try { rows = await api(`${cfg.endpoint}/?${qs}`); cfg._loaded = true; renderTable(); }
    catch (e) { toast(e.message, false); }
  }

  const readSearch = () => Object.fromEntries([...root.querySelectorAll('[data-s]')].map(i => [i.dataset.s, i.value.trim()]).filter(([, v]) => v));
  $('form').addEventListener('submit', e => { e.preventDefault(); load(readSearch()); });
  $('todos').addEventListener('click', () => { $('form').reset(); load({ status: 'ATIVO' }); });   // TODOS => ATIVO
  $('limpar').addEventListener('click', () => { $('form').reset(); rows = []; cfg._loaded = false; renderTable(); });
  root.querySelectorAll('th[data-k]').forEach(th => th.addEventListener('click', () => {
    sortDir = sortKey === th.dataset.k ? -sortDir : 1; sortKey = th.dataset.k; renderTable();
  }));

  // ── Modal (status NUNCA aparece no formulário) ──
  async function fillLookups() {
    for (const f of cfg.form.filter(f => f.lookup)) {
      const items = await api(`${f.lookup.url}${f.lookup.url.includes('?') ? '&' : '?'}status=ATIVO`);
      lookups[f.name] = items;
    }
  }
  function fieldHtml(f, v) {
    if (f.type === 'parcelas') return `<div class="field"><label>${f.label}</label><div data-r="parcelas"></div><button type="button" class="btn sm secondary" data-r="addparc">＋ Parcela</button></div>`;
    if (f.lookup) {
      const sel = f.multiple ? (v || []) : [v];
      return `<div class="field"><label>${f.label}</label><select name="${f.name}" ${f.multiple ? 'multiple size="4"' : ''}>${f.multiple ? '' : '<option value="">—</option>'}${(lookups[f.name] || []).map(i => `<option value="${i.id}" ${sel.includes(i.id) ? 'selected' : ''}>${esc(i[f.lookup.label])}</option>`).join('')}</select></div>`;
    }
    if (f.options) return `<div class="field"><label>${f.label}</label><select name="${f.name}" ${f.required ? 'required' : ''}>${f.options.map(o => `<option ${o === v ? 'selected' : ''}>${o}</option>`).join('')}</select></div>`;
    return `<div class="field"><label>${f.label}</label><input name="${f.name}" type="${f.type || 'text'}" step="${f.type === 'number' ? '0.01' : ''}" value="${esc(v ?? '')}" ${f.required ? 'required' : ''}></div>`;
  }
  function addParcela(p = {}) {
    const d = document.createElement('div'); d.className = 'parcela-row';
    d.innerHTML = `<input type="date" data-p="venc" value="${(p.data_vencimento || '').slice(0, 10)}" required><input type="number" step="0.01" data-p="valor" placeholder="Valor" value="${p.valor_parcela ?? ''}" required><button type="button" class="btn sm danger">✖</button>`;
    d.querySelector('button').onclick = () => d.remove();
    $('fields').querySelector('[data-r="parcelas"]').appendChild(d);
  }
  async function openModal(item) {
    editing = item;
    await fillLookups().catch(e => toast(e.message, false));
    $('mtitle').textContent = (item ? 'Editar ' : 'Novo ') + cfg.singular;
    $('fields').innerHTML = cfg.form.map(f => fieldHtml(f, item ? (f.key ? item[f.key] : item[f.name]) : f.default)).join('');
    const ap = $('fields').querySelector('[data-r="addparc"]');
    if (ap) { ap.onclick = () => addParcela(); (item?.parcelas || [{}]).forEach(addParcela); }
    $('modal').classList.add('open');
  }
  $('novo').addEventListener('click', () => openModal(null));
  $('cancel').addEventListener('click', () => $('modal').classList.remove('open'));
  $('mform').addEventListener('submit', async e => {
    e.preventDefault();
    const payload = {};
    for (const f of cfg.form) {
      if (f.type === 'parcelas') {
        payload.parcelas = [...$('fields').querySelectorAll('.parcela-row')].map(r => ({ data_vencimento: r.querySelector('[data-p=venc]').value, valor: parseFloat(r.querySelector('[data-p=valor]').value) }));
      } else if (f.multiple) {
        payload[f.name] = [...e.target.elements[f.name].selectedOptions].map(o => +o.value);
      } else {
        let v = e.target.elements[f.name].value;
        if (f.lookup) v = v ? +v : null; else if (f.type === 'number') v = parseFloat(v);
        payload[f.name] = v;
      }
    }
    Object.assign(payload, cfg.fixed ? Object.fromEntries(Object.entries(cfg.fixedBody || {})) : {});
    try {
      await api(editing ? `${cfg.endpoint}/${editing.id}` : `${cfg.endpoint}/`, editing ? 'PUT' : 'POST', payload);
      $('modal').classList.remove('open');
      toast(editing ? 'Registro atualizado com sucesso' : 'Registro criado com sucesso');
      if (cfg._loaded) load(readSearch()); else load({ status: 'ATIVO' });
    } catch (err) { toast(err.message, false); }
  });

  body.addEventListener('click', async e => {
    const b = e.target.closest('button[data-a]'); if (!b) return;
    const item = rows.find(r => r.id == b.dataset.id);
    if (b.dataset.a === 'edit') return openModal(item);
    try {
      if (b.dataset.a === 'del') {
        if (!confirm(`Inativar este registro? (exclusão lógica)`)) return;
        await api(`${cfg.endpoint}/${item.id}`, 'DELETE'); toast('Registro inativado');
      } else { await api(`${cfg.endpoint}/${item.id}/reativar`, 'PATCH'); toast('Registro reativado'); }
      load(readSearch());
    } catch (err) { toast(err.message, false); }
  });

  renderTable();
  return { reload: () => cfg._loaded && load(readSearch()) };
}
