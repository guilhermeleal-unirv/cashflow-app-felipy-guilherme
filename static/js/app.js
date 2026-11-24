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

// ── Código da Última Atualização no GitHub ──
async function carregarInfoGit() {
  const elSha = $id('gitCommitSha');
  const elTime = $id('gitCommitTime');
  const elSide = $id('sidebarGitSha');
  const repoUrl = 'https://github.com/guilhermeleal-unirv/cashflow-app-felipy-guilherme';

  const aplicarGit = (sha, url, dataIso, msg) => {
    const shortSha = (sha || '').slice(0, 7) || 'ver repo';
    const linkUrl = url || (sha ? `${repoUrl}/commit/${sha}` : `${repoUrl}/commits/main`);

    if (elSha) {
      elSha.textContent = shortSha;
      elSha.href = linkUrl;
      if (msg) elSha.title = `Commit: ${msg.split('\n')[0]}`;
    }
    if (elSide) {
      elSide.textContent = shortSha;
      elSide.href = linkUrl;
    }
    if (elTime && dataIso) {
      try {
        const d = new Date(dataIso);
        const fmt = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        elTime.textContent = `• ${fmt}`;
      } catch (_) {}
    }
  };

  try {
    // 1. Tenta API pública do GitHub em tempo real (dados da branch main)
    const ghRes = await fetch('https://api.github.com/repos/guilhermeleal-unirv/cashflow-app-felipy-guilherme/commits/main', {
      headers: { 'Accept': 'application/vnd.github.v3+json' },
      cache: 'no-cache'
    });
    if (ghRes.ok) {
      const gh = await ghRes.json();
      aplicarGit(gh.sha, gh.html_url, gh.commit?.author?.date, gh.commit?.message);
      return;
    }
  } catch (_) {
    // Continua para o fallback
  }

  try {
    // 2. Fallback via backend /info-git (Render env RENDER_GIT_COMMIT ou git local)
    const beRes = await fetch('/info-git');
    if (beRes.ok) {
      const be = await beRes.json();
      aplicarGit(be.commit_sha, be.commit_url);
    }
  } catch (_) {
    if (elSha) elSha.textContent = 'main';
  }
}

checkAuth();
carregarInfoGit();

// ══════════════════════════════════════════════════════════════
// ── Agente Inteligente RAG (N3: Simples e Embeddings) ──
// ══════════════════════════════════════════════════════════════
function formatarMarkdown(md) {
  if (!md) return '';
  let h = esc(md);
  // Negrito **texto**
  h = h.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Itálico *texto*
  h = h.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Listas com marcadores
  h = h.replace(/^\s*[-•*]\s+(.*)$/gm, '<li style="margin-left: 1.2rem;">$1</li>');
  // Quebras de linha
  h = h.replace(/\n\n/g, '<br><br>');
  h = h.replace(/\n/g, '<br>');
  return h;
}

function renderFonteCard(f, modo) {
  const sim = f.similaridade_score !== undefined ? f.similaridade_score : null;
  const simPill = sim !== null
    ? `<span class="sim-pill ${sim >= 0.6 ? 'sim-high' : 'sim-med'}">Similaridade: ${(sim * 100).toFixed(1)}%</span>`
    : '';

  const parcelasStr = (f.parcelas || []).length
    ? `${f.parcelas.length} parcela(s)`
    : 'Sem parcelas';

  return `
    <div class="rag-source-card">
      <div class="rag-source-header">
        <span style="color: var(--primary); font-weight: 700;">#${f.id} — ${f.tipo} | ${brl(f.valor_total)}</span>
        ${simPill}
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.3rem; margin-top: 0.3rem;">
        <div><strong>Fornecedor/Cliente:</strong> ${esc(f.parceiro || '—')}</div>
        <div><strong>Faturado:</strong> ${esc(f.titular || '—')}</div>
        <div><strong>Classificação:</strong> <span class="badge" style="background:rgba(255,255,255,0.08);">${esc(f.categoria || '—')}</span></div>
        <div><strong>Emissão:</strong> ${dataBR(f.data_emissao)}</div>
        <div><strong>Parcelas:</strong> ${parcelasStr}</div>
        <div><strong>Origem (PDF):</strong> ${esc(f.documento_pdf || 'Manual/Nenhum')}</div>
      </div>
    </div>
  `;
}

// Chips de perguntas de exemplo
document.querySelectorAll('.btn-chip').forEach(btn => {
  btn.addEventListener('click', () => {
    const q = btn.dataset.q;
    const txt = $id('ragQuery');
    if (txt && q) {
      txt.value = q;
      txt.focus();
    }
  });
});

// Botão de alternar exibição das fontes
const btnToggleSources = $id('btnToggleSources');
if (btnToggleSources) {
  btnToggleSources.addEventListener('click', () => {
    const list = $id('ragSourcesList');
    if (list) list.classList.toggle('hidden');
  });
}

// Submissão do formulário de consulta RAG
const ragForm = $id('ragForm');
if (ragForm) {
  ragForm.addEventListener('submit', async e => {
    e.preventDefault();
    const query = ($id('ragQuery')?.value || '').trim();
    const modo = $id('ragModo')?.value || 'simples';
    // Pega API Key do campo RAG ou da tela Lançar via IA
    const apiKey = ($id('ragApiKey')?.value || '').trim() || ($id('apiKey')?.value || '').trim();

    if (!query) {
      toast('Por favor, digite sua pergunta sobre o banco.', false);
      return;
    }

    const btn = $id('ragSubmitBtn');
    const loader = $id('ragLoader');
    const btnText = $id('ragBtnText');
    const resultCard = $id('ragResultCard');
    const singleResult = $id('ragSingleResult');
    const compareResult = $id('ragCompareResult');

    btn.disabled = true;
    if (loader) loader.style.display = 'inline-block';
    if (btnText) btnText.textContent = 'Processando com IA...';

    try {
      const data = await api('/rag/consultar', 'POST', {
        query,
        modo,
        top_k: 5,
        api_key: apiKey || undefined
      });

      resultCard.classList.remove('hidden');

      if (data.modo === 'ambos') {
        singleResult.classList.add('hidden');
        compareResult.classList.remove('hidden');

        $id('compareSimplesAnswer').innerHTML = formatarMarkdown(data.simples.resposta);
        $id('compareSimplesMeta').textContent = `Recuperados ${data.simples.total_fontes} registros estruturados via SQL.`;

        $id('compareEmbeddingsAnswer').innerHTML = formatarMarkdown(data.embeddings.resposta);
        $id('compareEmbeddingsMeta').textContent = `Recuperados os ${data.embeddings.total_fontes} registros mais próximos via similaridade de cosseno.`;
      } else {
        compareResult.classList.add('hidden');
        singleResult.classList.remove('hidden');

        const isSemantico = data.modo === 'embeddings';
        const badge = $id('ragModeBadge');
        if (badge) {
          badge.textContent = isSemantico ? 'RAG EMBEDDINGS (SEMÂNTICO)' : 'RAG SIMPLES (SQL)';
          badge.style.background = isSemantico ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)';
          badge.style.color = isSemantico ? '#10b981' : '#3b82f6';
        }

        $id('ragAnswerContent').innerHTML = formatarMarkdown(data.resposta);

        const fontes = data.fontes || [];
        $id('ragSourcesCount').textContent = fontes.length;

        const sourcesList = $id('ragSourcesList');
        if (sourcesList) {
          sourcesList.classList.remove('hidden');
          sourcesList.innerHTML = fontes.length
            ? fontes.map(f => renderFonteCard(f, data.modo)).join('')
            : '<p style="color:var(--muted); font-size:0.85rem;">Nenhum registro recuperado do banco para esta consulta.</p>';
        }
      }

      toast('Consulta RAG processada com sucesso!');
      resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      toast(err.message || 'Erro ao consultar RAG', false);
    } finally {
      btn.disabled = false;
      if (loader) loader.style.display = 'none';
      if (btnText) btnText.textContent = '🔍 Consultar com IA';
    }
  });
}
