/* Navegação, telas CRUD e fluxo "Lançar via IA" (Etapa 2) */

const fmtDoc = d => {
  d = String(d || '').replace(/\D/g, '');
  if (d.length === 14) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`;
  if (d.length === 11) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`;
  return d || '—';
};

const statusCol = { key: 'status', label: 'Status' };

// ── Fornecedor / Cliente (PESSOAS) ──
createCrud({
  view: 'v-pessoas', endpoint: '/parceiros', singular: 'Pessoa',
  title: 'Manter Fornecedor / Cliente', subtitle: 'Cadastro de pessoas (exclusão lógica: registros são apenas inativados).',
  search: [{ name: 'nome', label: 'Nome / Razão Social' }, { name: 'documento', label: 'CNPJ / CPF' }, { name: 'tipo', label: 'Tipo', options: ['FORNECEDOR', 'CLIENTE'] }],
  columns: [{ key: 'id', label: 'ID' }, { key: 'nome_razao', label: 'Nome / Razão Social' }, { key: 'cnpj_cpf', label: 'CNPJ / CPF', fmt: fmtDoc }, { key: 'tipo', label: 'Tipo' }, statusCol],
  form: [{ name: 'nome_razao', label: 'Nome / Razão Social', required: true }, { name: 'cnpj_cpf', label: 'CNPJ / CPF', required: true },
         { name: 'tipo', label: 'Tipo', options: ['FORNECEDOR', 'CLIENTE'], default: 'FORNECEDOR', required: true }],
});

// ── Faturado ──
createCrud({
  view: 'v-faturados', endpoint: '/titulares', singular: 'Faturado',
  title: 'Manter Faturado', subtitle: 'Pessoas em nome de quem as despesas são faturadas.',
  search: [{ name: 'nome', label: 'Nome' }, { name: 'documento', label: 'CPF / CNPJ' }],
  columns: [{ key: 'id', label: 'ID' }, { key: 'nome', label: 'Nome' }, { key: 'cpf_cnpj', label: 'CPF / CNPJ', fmt: fmtDoc }, statusCol],
  form: [{ name: 'nome', label: 'Nome', required: true }, { name: 'cpf_cnpj', label: 'CPF / CNPJ', required: true }],
});

// ── Classificação (Tipo de Despesa / Receita) ──
createCrud({
  view: 'v-class', endpoint: '/categorias', singular: 'Classificação',
  title: 'Manter Classificação', subtitle: 'Tipos de DESPESA e de RECEITA.',
  search: [{ name: 'nome', label: 'Descrição' }, { name: 'tipo', label: 'Tipo', options: ['DESPESA', 'RECEITA'] }],
  columns: [{ key: 'id', label: 'ID' }, { key: 'nome', label: 'Descrição' }, { key: 'tipo', label: 'Tipo' }, statusCol],
  form: [{ name: 'nome', label: 'Descrição', required: true }, { name: 'tipo', label: 'Tipo', options: ['DESPESA', 'RECEITA'], default: 'DESPESA', required: true }],
});

// ── Contas a Pagar / Receber ──
function contasCfg(view, tipo, titulo, tipoPessoa, tipoClass) {
  return {
    view, endpoint: '/registros', singular: titulo, fixed: { tipo }, fixedBody: { tipo },
    title: `Registrar ${titulo}`, subtitle: `Movimento ${tipo} com uma ou mais parcelas.`,
    search: [{ name: 'parceiro', label: tipoPessoa === 'FORNECEDOR' ? 'Fornecedor' : 'Cliente' }, { name: 'titular', label: 'Faturado' },
             { name: 'valor_min', label: 'Valor mín.', type: 'number' }, { name: 'valor_max', label: 'Valor máx.', type: 'number' },
             { name: 'data_ini', label: 'Emissão de', type: 'date' }, { name: 'data_fim', label: 'Emissão até', type: 'date' }],
    columns: [{ key: 'id', label: 'ID' }, { key: 'parceiro', label: tipoPessoa === 'FORNECEDOR' ? 'Fornecedor' : 'Cliente' },
              { key: 'titular', label: 'Faturado' }, { key: 'categoria', label: 'Classificação' },
              { key: 'data_emissao', label: 'Emissão', fmt: dataBR }, { key: 'valor_total', label: 'Valor', fmt: brl },
              { key: 'proximo_vencimento', label: '1º Venc.', fmt: dataBR },
              { key: 'parcelas', label: 'Parcelas', fmt: v => (v || []).length }, statusCol],
    form: [
      { name: 'parceiro_id', label: tipoPessoa === 'FORNECEDOR' ? 'Fornecedor' : 'Cliente', lookup: { url: `/parceiros/?tipo=${tipoPessoa}`, label: 'nome_razao' } },
      { name: 'titular_id', label: 'Faturado', lookup: { url: '/titulares/', label: 'nome' } },
      { name: 'categoria_ids', label: `Classificação (${tipoClass}) – Ctrl para várias`, multiple: true, lookup: { url: `/categorias/?tipo=${tipoClass}`, label: 'nome' } },
      { name: 'data_emissao', label: 'Data de emissão', type: 'date', required: true },
      { name: 'valor_total', label: 'Valor total', type: 'number', required: true },
      { name: 'parcelas', label: 'Parcelas (soma = valor total)', type: 'parcelas' },
    ],
  };
}
createCrud(contasCfg('v-pagar', 'APAGAR', 'Conta a Pagar', 'FORNECEDOR', 'DESPESA'));
createCrud(contasCfg('v-receber', 'ARECEBER', 'Conta a Receber', 'CLIENTE', 'RECEITA'));

// ── Navegação ──
document.querySelectorAll('.nav-btn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.nav-btn').forEach(x => x.classList.toggle('active', x === b));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === b.dataset.view));
}));

// ── Lançar via IA ──
let extraido = null;
const $id = id => document.getElementById(id);

function item(k, nome, doc, st) {
  const [cls, txt] = !st.existe ? ['nao', 'NÃO EXISTE'] : st.inativo ? ['ina', `EXISTE (INATIVO – será reativado) – ID: ${st.id}`] : ['existe', `EXISTE – ID: ${st.id}`];
  return `<div class="analise-item"><div class="k">${k}</div><div class="n">${esc(nome) || '—'}</div>${doc ? `<div class="d">${doc}</div>` : ''}<div class="r ${cls}">${txt}</div></div>`;
}

function renderAnalise(v) {
  $id('analise').innerHTML =
    item('FORNECEDOR', v.fornecedor.razao_social, 'CNPJ: ' + v.fornecedor.cnpj, v.fornecedor) +
    item('FATURADO', v.faturado.nome, (v.faturado.documento.length > 14 ? 'CNPJ: ' : 'CPF: ') + v.faturado.documento, v.faturado) +
    item('DESPESA', v.despesa.descricao, '', v.despesa);
}

function renderDetalhes(d) {
  const nf = d.nota_fiscal || {}, t = d.totais || {};
  const kv = (a, b) => `<div class="kv"><span>${a}</span><span>${esc(b ?? '—')}</span></div>`;
  $id('detalhes').innerHTML = `<div class="analise-item">
    ${kv('NF-e', `${nf.numero ?? '—'} / série ${nf.serie ?? '—'}`)}${kv('Emissão', dataBR(nf.data_emissao))}
    ${kv('Valor total da nota', brl(t.valor_total_nota))}${kv('Classificação', d.classificacao_despesa)}
    ${(d.parcelas || []).map(p => kv(`Parcela ${p.numero}`, `${dataBR(p.data_vencimento)} — ${brl(p.valor)}`)).join('')}</div>`;
}

$id('btnDetalhes').addEventListener('click', () => $id('detalhes').classList.toggle('hidden'));

$id('extractForm').addEventListener('submit', async e => {
  e.preventDefault();
  const file = $id('pdfFile').files[0];
  const btn = $id('submitBtn');
  btn.disabled = true; btn.classList.add('loading'); $id('btnText').textContent = 'Analisando...';
  $id('analiseCard').classList.add('hidden'); $id('lancarMsg').classList.add('hidden');
  try {
    const fd = new FormData(); fd.append('file', file); fd.append('api_key', $id('apiKey').value);
    const token = localStorage.getItem('cashflow_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const r = await fetch('/documentos/extrair_via_llm', { method: 'POST', body: fd, headers });
    if (r.status === 401) {
      localStorage.removeItem('cashflow_token');
      window.showLoginModal();
      throw new Error('Sessão expirada. Faça login novamente.');
    }
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Erro ao extrair');
    extraido = { ...data, nome_arquivo: file.name };
    renderAnalise(await api('/documentos/verificar', 'POST', extraido));
    renderDetalhes(data);
    $id('btnLancar').disabled = false;
    $id('analiseCard').classList.remove('hidden');
    $id('analiseCard').scrollIntoView({ behavior: 'smooth' });
  } catch (err) { toast(err.message, false); }
  finally { btn.disabled = false; btn.classList.remove('loading'); $id('btnText').textContent = '⚡ Analisar com IA'; }
});

$id('btnLancar').addEventListener('click', async () => {
  if (!extraido) return;
  $id('btnLancar').disabled = true;
  try {
    const r = await api('/documentos/lancar', 'POST', extraido);
    const box = $id('lancarMsg');
    box.className = 'analise-item';
    box.innerHTML = `<div class="r existe">✅ ${r.message}</div><div class="d">Criados agora: ${r.criados.length ? r.criados.join(', ') : 'nenhum (cadastros já existiam)'} · Movimento ID ${r.ids.registro}</div>`;
    toast('Registro lançado com sucesso!');
    renderAnalise(await api('/documentos/verificar', 'POST', extraido));
    extraido = null;
  } catch (err) { toast(err.message, false); $id('btnLancar').disabled = false; }
});

// ── Controle de Login / Sessão ──
window.showLoginModal = function() {
  $id('loginModal').style.display = 'flex';
  $id('loginError').classList.add('hidden');
  $id('loginUsername').value = '';
  $id('loginPassword').value = '';
};

function checkAuth() {
  const token = localStorage.getItem('cashflow_token');
  const user = localStorage.getItem('cashflow_user');
  if (!token) {
    window.showLoginModal();
  } else {
    $id('loginModal').style.display = 'none';
    $id('userNameLabel').textContent = user || 'Usuário';
  }
}

$id('loginForm').addEventListener('submit', async e => {
  e.preventDefault();
  const u = $id('loginUsername').value.trim();
  const p = $id('loginPassword').value;
  const btn = $id('btnLoginSubmit');
  const ldr = $id('loginLoader');
  const txt = $id('loginBtnText');
  const errBox = $id('loginError');

  btn.disabled = true;
  ldr.style.display = 'inline-block';
  txt.textContent = 'Autenticando...';
  errBox.classList.add('hidden');

  try {
    const res = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: u, password: p })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Usuário ou senha inválidos.');
    }
    localStorage.setItem('cashflow_token', data.access_token);
    localStorage.setItem('cashflow_user', u);
    $id('userNameLabel').textContent = u;
    $id('loginModal').style.display = 'none';
    toast('Login efetuado com sucesso!');
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    ldr.style.display = 'none';
    txt.textContent = 'Entrar';
  }
});

$id('btnLogout').addEventListener('click', () => {
  if (confirm('Deseja realmente sair?')) {
    localStorage.removeItem('cashflow_token');
    localStorage.removeItem('cashflow_user');
    window.showLoginModal();
    toast('Você saiu do sistema.');
  }
});

checkAuth();
