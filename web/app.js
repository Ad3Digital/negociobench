'use strict';
const $ = (q, el = document) => el.querySelector(q);
const $$ = (q, el = document) => [...el.querySelectorAll(q)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (n, digits = 1) => n == null ? '—' : Number(n).toLocaleString('pt-BR', {maximumFractionDigits:digits});
const paths = {
  grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  layers:'m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',
  store:'M3 9v12h18V9 M2 9l2-6h16l2 6 M2 9c0 4 5 4 5 0 0 4 5 4 5 0 0 4 5 4 5 0 0 4 5 4 5 0 M9 21v-7h6v7',
  book:'M12 5v16 M12 5C8 2 4 3 2 4v16c4-2 7-1 10 1 3-2 6-3 10-1V4c-3-1-6-2-10 1',
  plus:'M12 5v14 M5 12h14', play:'m8 4 12 8-12 8z',
  chat:'M21 11a9 9 0 0 1-9 9H3l1-5a9 9 0 1 1 17-4 M8 10h8 M8 14h5',
  target:'M20 12a8 8 0 1 1-8-8 M16 12a4 4 0 1 1-4-4 M12 12 22 2 M16 2h6v6',
  spark:'m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z',
  chart:'M4 3v18h18 M8 16v-5 M13 16V7 M18 16V4',
  shield:'m12 2 9 4v6c0 5-5 8-9 10-4-2-9-5-9-10V6z m-4 10 3 3 5-6',
  chip:'M6 6h12v12H6z M9 9h6v6H9z M9 2v4 M15 2v4 M9 18v4 M15 18v4 M2 9h4 M2 15h4 M18 9h4 M18 15h4',
  clock:'M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  link:'m9 15 6-6 M8 17l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0 M16 7l1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0',
  upload:'M12 16V3 m-5 5 5-5 5 5 M4 15v6h16v-6',
  download:'M12 3v13 m-5-5 5 5 5-5 M4 16v5h16v-5',
  arrow:'M4 12h16 m-6-6 6 6-6 6',
  github:'M9 19c-4 1-4-2-6-2 M15 22v-4c0-1 0-2-1-2 4 0 7-2 7-6 0-2-1-3-2-4 0-1 0-3-1-4-2 0-3 1-4 2-2-1-4-1-6 0-1-1-2-2-4-2-1 1-1 3-1 4-1 1-2 2-2 4 0 4 3 6 7 6-1 0-1 1-1 2v4',
  check:'m5 12 4 4L19 6', copy:'M9 9h12v12H9z M15 9V3H3v12h6'
};
const icon = (name, size = 18) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.spark}"/></svg>`;
$$('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
let state, page = 'overview', caseFilter = 'all', searchTerm = '', selectedRun, selectedRow;
let pollTimer, toastTimer;

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Bench-Token':state.token},body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Não foi possível concluir a operação.');
  return body;
}
function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('show'), 4500); }
async function refresh(render = true) {
  state = await api('/api/state');
  $('#nav-count').textContent = state.tasks.length;
  $('#version').textContent = `v${state.version}`;
  if (render) renderPage();
  clearTimeout(pollTimer);
  if (state.active) pollTimer = setTimeout(async () => {try {await refresh(page === 'overview');} catch(e) {toast(e.message);}}, 1800);
}
function route() {
  const parts = location.hash.slice(1).split('/');
  page = ['overview','cases','business','method'].includes(parts[0]) ? parts[0] : 'overview';
  if (page === 'cases') caseFilter = parts[1] || 'all';
  if (state) {renderPage();window.scrollTo(0,0);}
}
window.addEventListener('hashchange', route);
function renderPage() {
  $$('nav [data-page]').forEach(el => {el.classList.toggle('active', el.dataset.page === page); if(el.dataset.page === page) el.setAttribute('aria-current','page'); else el.removeAttribute('aria-current');});
  $('#page-label').textContent = {overview:'VISÃO GERAL',cases:'EXPLORAR DESAFIOS',business:'MEU NEGÓCIO',method:'COMO FUNCIONA'}[page];
  $('#page').innerHTML = ({overview:overview, cases:casesPage, business:businessPage, method:methodPage}[page])();
}
const catName = id => state.categories.find(c => c.id === id)?.name || id;
const labelProfile = id => ({quick:'Exploração rápida', business:'Negócios',rag:'Atendimento com RAG',contexto:'Documento longo',full:'Bateria completa'}[id] || id);
const statusLabel = id => ({completed:'Concluído',running:'Em andamento',cancelled:'Cancelado',interrupted:'Interrompido'}[id] || id);
const date = value => new Date(value).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'short'});

function radar() {
  return `<div class="hero-graphic" aria-label="Seis dimensões de trabalho: atendimento, vendas, marketing, análise, operação e confiança. Ilustração sem resultados."><svg viewBox="0 0 290 255" fill="none" aria-hidden="true"><g stroke="#354335"><path d="m145 28 91 53v106l-91 53-91-53V81z"/><path d="m145 57 66 38v78l-66 38-66-38V95z"/><path d="m145 85 42 25v48l-42 25-42-25v-48z"/><path d="m145 112 19 11v22l-19 11-19-11v-22z"/><path d="M145 28v212 M54 81l182 106 M54 187l182-106" stroke-dasharray="3 5"/></g><circle cx="145" cy="134" r="30" fill="#23301d" stroke="#607948"/><path d="m131 144 9-20 9 20 10-20" stroke="#b6ee70" stroke-width="3" stroke-linejoin="round"/><g fill="#b6ee70"><circle cx="145" cy="28" r="3"/><circle cx="236" cy="81" r="3"/><circle cx="236" cy="187" r="3"/><circle cx="145" cy="240" r="3"/><circle cx="54" cy="187" r="3"/><circle cx="54" cy="81" r="3"/></g><g fill="#a3afaa" font-family="monospace" font-size="8"><text x="145" y="14" text-anchor="middle">ATENDIMENTO</text><text x="244" y="83">VEN</text><text x="244" y="190">MKT</text><text x="4" y="83">CONF</text><text x="9" y="190">OPS</text></g></svg><span class="graphic-note">6 DIMENSÕES. TRABALHO DE VERDADE.</span></div>`;
}
function activePanel() {
  const a = state.active;
  if (!a) return '';
  return `<div class="progress-card" role="status"><div class="progress-top"><div><h3>${icon('chip',16)} Benchmark em andamento</h3><p>${esc(a.model)} · ${esc(a.task || 'Preparando')} · ${a.completed} de ${a.total} respostas</p></div><button class="button ghost small" data-action="cancel">Parar após este caso</button></div><progress value="${a.completed}" max="${a.total}" aria-label="Progresso da bateria"></progress></div>`;
}
function overview() {
  const complete = state.runs.filter(r => r.status === 'completed');
  const rag = state.tasks.filter(t => t.mode === 'rag').length;
  return `<section class="hero"><div class="hero-copy"><span class="eyebrow">OPEN SOURCE · FEITO PARA A VIDA REAL</span><h1>A melhor IA é a que<br><em>funciona no seu negócio.</em></h1><p>Descubra o que os modelos locais conseguem fazer no seu computador. Teste tarefas reais, compare as respostas e crie desafios com a cara do seu negócio.</p><div class="hero-actions"><button class="button primary" data-action="new-run">${icon('play',16)}Rodar meu primeiro teste</button><a class="button ghost" href="#business">Criar meus desafios ${icon('arrow',15)}</a></div></div>${radar()}</section>
  <div class="suite-label">${icon('layers',14)} Bateria ativa: <strong>${esc(state.suite_name)}</strong><a class="text-button" href="#business">Personalizar ↗</a></div>
  ${activePanel()}
  <section class="stats" aria-label="Resumo do laboratório"><div class="stat"><div class="stat-top">Desafios disponíveis${icon('layers',16)}</div><strong>${state.tasks.length}<small> casos</small></strong><p>Critérios abertos e conferíveis</p></div><div class="stat"><div class="stat-top">Atendimento com RAG${icon('book',16)}</div><strong>${rag}<small> desafios</small></strong><p>Respostas apoiadas na sua base</p></div><div class="stat"><div class="stat-top">Execuções concluídas${icon('chart',16)}</div><strong>${complete.length.toString().padStart(2,'0')}</strong><p>${complete.length ? 'Evidências salvas neste PC' : 'Seu laboratório começa aqui'}</p></div><div class="stat"><div class="stat-top">Custo de API${icon('chip',16)}</div><strong>R$ 0<small> / local</small></strong><p>Usa os recursos do seu computador</p></div></section>
  <section><div class="section-head"><div><h2>Resultados, sem achismo.</h2><p>Abra cada execução para entender o que deu certo e o que precisa melhorar.</p></div><span class="badge">NESTE COMPUTADOR</span></div>${resultsPanel()}</section>
  <section><div class="section-head"><div><h2>O que a sua IA precisa resolver?</h2><p>Escolha um tipo de trabalho para explorar os desafios.</p></div><a href="#cases">Ver todos ↗</a></div><div class="category-grid">${state.categories.map(c => `<a class="category-card" href="#cases/${c.id}"><div class="cat-top"><span class="cat-icon">${icon(c.icon,18)}</span><span class="cat-count">${state.tasks.filter(t=>t.category===c.id).length} DESAFIOS ↗</span></div><h3>${c.name}</h3><p>${c.description}</p></a>`).join('')}</div></section>
  <section class="rag-banner"><span class="rag-symbol">${icon('book',30)}</span><div><h3>Um chatbot precisa conhecer o seu negócio.</h3><p>Teste respostas com RAG: preços, políticas, fontes e até o que a IA deveria admitir que não sabe.</p></div><a href="#cases/rag" class="button secondary small">Explorar RAG ${icon('arrow',14)}</a></section>`;
}
function resultsPanel() {
  const runs = state.runs;
  const groups = new Set(runs.filter(r=>r.status==='completed').map(r=>r.protocol));
  return `<div class="panel"><div class="panel-bar"><h3>Histórico do seu laboratório</h3><span class="badge green">${runs.length ? `${groups.size} PROTOCOLO(S)` : 'PRONTO PARA COMEÇAR'}</span></div>${runs.length ? `<div class="table-scroll"><table><thead><tr><th>Modelo / execução</th><th>Critérios objetivos</th><th>Tempo mediano</th><th>Cobertura</th><th>Estado</th><th></th></tr></thead><tbody>${runs.map(r => `<tr><td><strong>${esc(r.model)}</strong><small>${date(r.created_at)} · ${esc(labelProfile(r.settings.profile))} · ${r.protocol.slice(0,7)}</small></td><td><span class="score">${number(r.summary.score)}</span><small>/ 100 · ${r.summary.errors} erros</small></td><td>${number(r.summary.median_s)} s<small>${number(r.summary.effective_tps)} tok/s efetivos</small></td><td>${r.summary.finished}/${r.summary.planned}<small>${r.summary.human_reviewed} revisões humanas</small></td><td><span class="badge ${r.status==='completed'?'green':''}">${esc(statusLabel(r.status))}</span></td><td><button class="button ghost small" data-action="run-detail" data-id="${r.id}">Abrir ↗</button></td></tr>`).join('')}</tbody></table></div>` : `<div class="empty"><div class="empty-icon">${icon('chart',31)}</div><div><h3>Seu primeiro resultado começa aqui.</h3><p>Conecte um modelo no Ollama, LM Studio ou llama.cpp. Escolha uma bateria e veja como ele se sai nas tarefas que importam.</p><button class="text-button" data-action="new-run">Conectar modelo local →</button></div></div>`}<div class="panel-note">${icon('shield',13)} ${groups.size>1?'Há protocolos diferentes. Compare notas apenas entre execuções com o mesmo código.':'Notas automáticas medem critérios objetivos. Qualidade da resposta tem revisão humana separada.'}</div></div>`;
}
function casesPage() {
  return `<div class="page-intro"><span class="eyebrow">ESCOLHA O TRABALHO. INSPECIONE O TESTE.</span><h1>Desafios que fazem sentido.</h1><p>Cenários, campos avaliados e critérios humanos ficam à vista. Os casos públicos são fictícios; no Meu negócio, você pode importar os seus.</p></div><div class="filters" aria-label="Filtrar desafios">${[['all','Todos'],['local','Negócio local'],['digital','Negócio digital'],['rag','Com RAG']].map(([id,label])=>`<button class="filter ${caseFilter===id?'active':''}" data-action="filter" data-filter="${id}">${label}</button>`).join('')}<input class="search" id="case-search" type="search" aria-label="Buscar desafio" placeholder="Buscar desafio…" value="${esc(searchTerm)}"></div><div id="case-results">${caseCards()}</div>`;
}
function caseCards() {
  const tasks = state.tasks.filter(t=>(caseFilter==='all'||t.category===caseFilter||t.track===caseFilter||(t.track==='ambos'&&['local','digital'].includes(caseFilter))||(caseFilter==='rag'&&t.mode==='rag')) && `${t.title} ${t.brief}`.toLowerCase().includes(searchTerm.toLowerCase()));
  return tasks.length ? `<div class="case-grid">${tasks.map(t=>`<article class="case-card"><div class="case-meta"><span class="case-id">${esc(t.id)} / ${esc(catName(t.category))}</span>${t.mode==='rag'?'<span class="badge cyan">RAG</span>':''}<span class="badge">${t.track==='ambos'?'LOCAL + DIGITAL':t.track.toUpperCase()}</span></div><h3>${esc(t.title)}</h3><p>${esc(t.brief)}</p><div class="case-bottom"><span>${esc(t.difficulty)} · ${Object.keys(t.fields).length} campos</span><button class="text-button" data-action="case-detail" data-id="${esc(t.id)}">Ver desafio ↗</button></div></article>`).join('')}</div>` : '<div class="panel padded muted">Nenhum desafio encontrado. Tente outro filtro.</div>';
}
function businessPage() {
  return `<div class="page-intro"><span class="eyebrow">O SEU CONTEXTO É O MELHOR TESTE</span><h1>O benchmark do seu negócio.</h1><p>Uma oficina e um curso online têm necessidades diferentes. Monte uma bateria com suas perguntas, regras e documentos — e descubra quais modelos dão conta.</p></div>
  <div class="two-columns"><section class="panel padded"><h2>Comece pequeno. Teste o que importa.</h2><div class="steps"><div class="step"><div><h3>Descreva o trabalho</h3><p>Separe 5 a 10 situações frequentes: dúvida de preço, cálculo de orçamento, troca, prazo ou análise de campanha.</p></div></div><div class="step"><div><h3>Monte a base de conhecimento</h3><p>Para RAG, adicione pequenos textos sobre produtos, horários e políticas. Cada documento tem um ID, um título e uma versão clara.</p></div></div><div class="step"><div><h3>Defina o que é uma boa resposta</h3><p>Revise valores, fontes e limites. Inclua casos fáceis, informação ausente e contradições. O gabarito precisa estar certo antes do teste.</p></div></div><div class="step"><div><h3>Rode no seu PC e olhe as respostas</h3><p>Use os mesmos casos e ajustes nos modelos. Confira a utilidade do texto, o tempo de espera e se o modelo respeita os seus dados.</p></div></div></div><div class="guide-links"><a href="/guide" target="_blank" class="button secondary small">${icon('book',15)}Guia completo</a><a href="/api/suite/example" class="button ghost small">${icon('download',15)}Baixar exemplo JSON</a></div></section>
  <div><section class="panel padded"><span class="badge green">BATERIA ATIVA</span><h2 class="break-word">${esc(state.suite_name)}</h2><p class="muted">${esc(state.suite_description)}</p><span class="mono">${state.tasks.length} CASOS / ${state.documents.length} DOCUMENTOS / TOP-${state.top_k}</span><label class="upload-area">${icon('upload',27)}<b>Importe os testes do seu negócio</b><small>Arquivo JSON · até 2 MB · sem código executável</small><input type="file" class="file-input" id="suite-file" accept=".json,application/json"></label><p class="notice">Seus casos ficam neste PC. Relatórios exportados contêm perguntas, documentos recuperados e respostas; revise antes de compartilhar.</p><div class="guide-links"><a href="/api/suite/current" class="button ghost small">Exportar bateria</a><button class="text-button" data-action="reset-suite">Voltar à bateria AD3</button></div><div id="suite-error" class="error-text" role="alert"></div><div class="detail-section"><h3>Baterias salvas neste PC</h3>${(state.saved_suites||[]).map(s=>`<div class="saved-suite"><span>${esc(s.name)} <small class="muted">· ${s.count} casos</small></span><button class="button ghost small" data-action="select-suite" data-id="${s.id}">Usar</button></div>`).join('')||'<p class="muted">As baterias importadas vão aparecer aqui.</p>'}</div></section></div></div>
  <section class="panel padded detail-section"><span class="eyebrow">UMA IA PODE AJUDAR A ESCREVER OS CASOS</span><h2>Descreva. Copie o prompt. Revise o resultado.</h2><div class="form-grid"><label>Que negócio você tem?<input id="business-type" placeholder="Ex.: assistência técnica de celulares"></label><label>O que você quer testar?<input id="business-jobs" placeholder="Ex.: dúvidas de preço, garantia e agendamento"></label></div><label>Fatos e regras aprovados<textarea id="business-facts" placeholder="Ex.: abrimos de segunda a sexta, 9h às 18h. O diagnóstico custa R$ 60. Não prometer prazo de reparo sem avaliação."></textarea><small>Use fatos autorizados. Remova dados de clientes, senhas e informações que não quer enviar a outra IA.</small></label><button class="button primary" data-action="copy-prompt">${icon('copy',16)}Copiar prompt para gerar meus testes</button><p class="muted detail-section">Cole em uma IA da sua escolha, confira o JSON e salve como <code>meu-negocio.json</code>. Depois importe acima.</p></section>`;
}
function methodPage() {
  return `<div class="page-intro"><span class="eyebrow">SEM CAIXA-PRETA</span><h1>Mais contexto. Menos achismo.</h1><p>O NegócioBench ajuda a avaliar modelos no seu próprio hardware. Ele reúne evidências para uma decisão sua; uma nota não garante que um chatbot esteja pronto para atender clientes.</p></div>
  <div class="flow"><div>Seu negócio<small>casos + documentos</small></div><span>→</span><div>Modelo local<small>mesmos ajustes</small></div><span>→</span><div>Verificação<small>campos + fontes</small></div><span>→</span><div>Sua decisão<small>resposta + tempo</small></div></div>
  <div class="method-grid"><article class="panel"><h3>01 / O que a nota mede</h3><p>Cada campo objetivo vale um critério. Números têm tolerância absoluta de R$ 0,011 ou 0,011 unidade; booleanos, null e listas precisam corresponder ao gabarito. O campo <code>ordem</code> exige a sequência exata.</p><p>Texto não vazio conta como presença, sem avaliação automática de estilo. Um erro em campo crítico zera o caso. A nota final é a média das notas por área, para equilibrar categorias de tamanhos diferentes.</p></article>
  <article class="panel"><h3>02 / O que depende de você</h3><p>Utilidade, clareza e fidelidade do texto são avaliadas por uma pessoa, de 0 a 4, ao abrir cada resposta. Essa revisão fica separada da nota automática.</p><p>Campos corretos não garantem um texto correto. Confira promessas, omissões, contradições e se a resposta realmente ajuda o cliente. Não há um juiz de IA oculto.</p></article>
  <article class="panel"><h3>03 / Como o RAG funciona</h3><p>A base é dividida em trechos pelo autor. Uma busca lexical BM25 recupera os top-K documentos para uma consulta fixa de cada caso. O modelo recebe os mesmos textos e deve citar os IDs usados.</p><p>O relatório guarda a consulta, os documentos e a cobertura das fontes esperadas. É um baseline reproduzível, sem embeddings ou reranker; não reproduz automaticamente o RAG da sua produção.</p></article>
  <article class="panel"><h3>04 / Como comparar com justiça</h3><p>Compare o mesmo código de protocolo: bateria, casos, repetições, temperatura, limite de saída e timeout. Registre também quantização, contexto, hardware e versão do servidor.</p><p>A primeira execução pode carregar o modelo. O tempo é ponta a ponta; tok/s efetivos incluem espera, prefill e geração. Não medimos VRAM, energia, TTFT ou velocidade pura de decodificação.</p></article>
  <article class="panel"><h3>05 / Falhas continuam visíveis</h3><p>Timeout, API indisponível e resposta inválida ficam registrados e recebem zero naquele caso. Falhas de infraestrutura aparecem separadas para você não confundir um servidor quebrado com um modelo ruim.</p><p>Execuções interrompidas têm cobertura parcial e não devem competir com baterias completas. Não há novas tentativas automáticas nem ajuste de prompt por modelo.</p></article>
  <article class="panel"><h3>06 / Local e aberto</h3><p>O aplicativo usa Python e o navegador, sem dependências externas, telemetria ou chaves de API. As conexões de inferência aceitam apenas o próprio computador e recusam redirecionamento.</p><p>Use um runtime local de confiança. Tags conhecidas de modelos cloud do Ollama são recusadas; um proxy que se disfarce de servidor local não pode ser auditado pelo benchmark.</p><a class="text-button" href="https://github.com/Ad3Digital/negociobench" target="_blank" rel="noreferrer">Código, licença MIT e metodologia ↗</a></article></div>`;
}

function showDialog(content) {$('#detail-content').innerHTML=content; if (!$('#detail-dialog').open) $('#detail-dialog').showModal();}
function dialogHead(eyebrow,title){return `<div class="dialog-head"><div><span class="eyebrow">${esc(eyebrow)}</span><h2 id="detail-title">${esc(title)}</h2></div><button class="icon-button" data-action="close" aria-label="Fechar">×</button></div>`;}
function caseDetail(id) {
  const t = state.tasks.find(t=>t.id===id); if(!t) return;
  showDialog(dialogHead(`${t.id} / ${catName(t.category)}`,t.title)+`<p class="detail-brief">${esc(t.brief)}</p><div class="detail-section"><h3>Campos solicitados ao modelo</h3><pre class="code-block">${esc(JSON.stringify(t.fields,null,2))}</pre></div>${t.mode==='rag'?`<div class="notice">RAG: busca BM25 com a consulta <strong>${esc(t.query)}</strong>. Até ${state.top_k} documentos entram no contexto. Fontes efetivamente recuperadas aparecem no relatório da execução.</div>`:''}<div class="detail-section"><h3>Revisão humana</h3><ul>${t.rubric.map(r=>`<li>${esc(r)}</li>`).join('')}</ul></div><p class="muted">O gabarito fica na bateria exportável. Ele não é enviado ao modelo.</p><div class="dialog-foot"><a href="/api/suite/current" class="text-button">Baixar bateria e gabaritos ↗</a><button class="button primary" data-action="new-run">Testar uma bateria</button></div>`);
}
function runDetail(id) {
  const r = state.runs.find(r=>r.id===id); if(!r)return; selectedRun=r;
  showDialog(dialogHead(`${statusLabel(r.status)} / ${r.protocol.slice(0,7)}`,r.model)+`<div class="stats"><div class="stat"><div class="stat-top">Critérios objetivos</div><strong>${number(r.summary.score)}<small> / 100</small></strong></div><div class="stat"><div class="stat-top">Cobertura</div><strong>${r.summary.finished}<small> / ${r.summary.planned}</small></strong></div><div class="stat"><div class="stat-top">Mediana</div><strong>${number(r.summary.median_s)}<small> s</small></strong></div><div class="stat"><div class="stat-top">Falhas críticas</div><strong>${r.summary.critical_failures}</strong></div></div><p class="muted break-word">${esc(r.settings.hardware)} · ${esc(r.settings.runtime)} · temperatura ${r.settings.temperature} · ${r.settings.max_tokens} tokens de saída · ${r.settings.repeats} repetição(ões)</p><div class="filters">${Object.entries(r.summary.categories).map(([k,v])=>`<span class="badge">${esc(catName(k))} ${number(v)}</span>`).join('')}</div><div class="result-list">${r.results.map((row,i)=>`<button class="result-row" data-action="answer-detail" data-id="${r.id}" data-index="${i}"><small>${esc(row.task_id)}</small><span>${esc(state.tasks.find(t=>t.id===row.task_id)?.title)}<small> · repetição ${row.repeat}${row.status==='error'?' · erro de infraestrutura':''}${row.finish_reason==='length'?' · limite de saída atingido':''}</small></span><b>${number(row.evaluation.score)}</b><small>${number(row.elapsed_s)} s ↗</small></button>`).join('')||'<p class="muted">Aguardando a primeira resposta…</p>'}</div><div class="dialog-foot detail-section"><span>Revise a resposta completa, além dos campos.</span><a class="button secondary" href="/api/export/${r.id}">${icon('download',16)}Exportar relatório JSON</a></div>`);
}
function answerDetail(id,index) {
  const r=state.runs.find(r=>r.id===id); const row=r?.results[index]; if(!row)return; selectedRun=r;selectedRow=row;
  const t=state.tasks.find(t=>t.id===row.task_id), review=row.human_review;
  showDialog(dialogHead(`${esc(r.model)} / repetição ${row.repeat}`,t.title)+`<div class="case-meta"><span class="badge green">${number(row.evaluation.score)} / 100 OBJETIVO</span><span class="badge">${number(row.elapsed_s)} s</span>${row.evaluation.critical_failure?'<span class="badge orange">FALHA CRÍTICA</span>':''}${row.finish_reason==='length'?'<span class="badge orange">SAÍDA TRUNCADA</span>':''}</div><p class="detail-brief">${esc(t.brief)}</p>${row.error?`<p class="error-text">${esc(row.error)}</p>`:''}<div class="detail-section"><h3>Resposta completa do modelo</h3><pre class="code-block">${esc(row.raw || '(sem resposta textual)')}</pre></div><div class="detail-section"><h3>Verificação dos critérios</h3>${row.evaluation.format_error?`<p class="error-text">${esc(row.evaluation.format_error)}</p>`:''}<div class="check-list">${row.evaluation.checks.map(c=>`<div class="check"><b class="${c.passed?'pass':'fail'}">${c.passed?'✓':'×'}</b><strong>${esc(c.field)}</strong><code>esperado: ${esc(JSON.stringify(c.expected))} · recebido: ${esc(JSON.stringify(c.actual))}</code></div>`).join('')}</div></div>${row.retrieved?.length?`<div class="detail-section"><h3>Documentos recuperados · cobertura das fontes esperadas ${number(row.retrieval_recall*100)}%</h3><p class="muted">Busca fixa: ${esc(t.query)}</p>${row.retrieved.map(d=>`<details class="source-doc"><summary>${esc(d.id)} · ${esc(d.title)} · BM25 ${number(d.retrieval_score,2)}</summary><p>${esc(d.text)}</p></details>`).join('')}</div>`:''}<form class="review-form" id="review-form"><h3>A resposta foi boa para o negócio?</h3><p>0 = falhou · 1 = fraca · 2 = precisa de ajustes · 3 = boa · 4 = pronta para o cenário. Revisão humana separada da nota automática.</p><ul>${t.rubric.map(v=>`<li class="muted">${esc(v)}</li>`).join('')}</ul><div class="form-grid three">${['utilidade','clareza','fidelidade'].map(k=>`<label>${k[0].toUpperCase()+k.slice(1)}<select name="${k}" required><option value="">Avaliar…</option>${[0,1,2,3,4].map(n=>`<option value="${n}" ${review?.[k]===n?'selected':''}>${n}</option>`).join('')}</select></label>`).join('')}</div><label>Observação<textarea name="note" maxlength="2000">${esc(review?.note||'')}</textarea></label><div class="dialog-foot"><button class="button ghost" type="button" data-action="run-detail" data-id="${r.id}">← Execução</button><button class="button primary" type="submit">Salvar revisão</button></div></form>`);
}

function openRun() {
  if(state.active){toast('Já existe uma bateria em andamento. Veja o progresso na visão geral.');location.hash='overview';return;}
  if($('#detail-dialog').open)$('#detail-dialog').close();
  $('#profile').innerHTML=Object.entries(state.profiles).filter(([,v])=>v.length).map(([k,v])=>`<option value="${k}">${labelProfile(k)} · ${v.length} casos</option>`).join('');
  $('#run-error').textContent='';$('#run-dialog').showModal();updateRunSize();
}
function updateRunSize(){const form=$('#run-form');const p=form.elements.profile.value;const models=$$('input[name=model]:checked',form).length;const reps=Number(form.elements.repeats.value);$('#run-size').textContent=`${state.profiles[p]?.length||0} casos × ${reps} repetição(ões) × ${models} modelo(s)`;}
async function discover() {
  const button=$('[data-action=discover]');button.disabled=true;$('#connection-status').textContent='Consultando o servidor local…';$('#model-list').innerHTML='<p class="muted">Buscando…</p>';
  try {const body=await api('/api/models',{endpoint:$('#endpoint').value,runtime:$('#runtime').value});$('#model-list').innerHTML=body.models.length?body.models.map(m=>`<label><input type="checkbox" name="model" value="${esc(m)}">${esc(m)}</label>`).join(''):'<p class="muted">Nenhum modelo local encontrado. Carregue ou baixe um no seu runtime.</p>';$('#connection-status').textContent=`${body.models.length} modelo(s) local(is) disponível(is).`;}
  catch(e){$('#connection-status').textContent=e.message;$('#model-list').innerHTML='<p class="muted">Não conectado. Confira o endereço e se o servidor está aberto.</p>';}
  finally{button.disabled=false;updateRunSize();}
}
async function copyPrompt() {
  const example=await api('/api/suite/example');
  const prompt=`Crie uma bateria personalizada para o NegócioBench. Responda somente JSON válido, sem markdown, seguindo exatamente o formato do exemplo abaixo.

Meu negócio: ${$('#business-type').value||'(descrever)'}
Trabalhos a avaliar: ${$('#business-jobs').value||'(descrever)'}
Fatos aprovados: ${$('#business-facts').value||'(pedir informações antes de criar casos)'}

Regras: use somente fatos fornecidos; peça o que faltar. Crie de 5 a 10 casos com níveis variados. Inclua pergunta frequente, cálculo (se aplicável), informação ausente, documento antigo e tentativa de injeção. Não invente políticas, depoimentos ou preços. Dados pessoais devem ser fictícios.
Separe documentos curtos com ID e título. Nos casos RAG, mode=rag, query contém a busca fixa e expected.fontes lista somente IDs que sustentam a resposta. Escolha top_k entre 1 e 10.
Categorias permitidas: atendimento, vendas, marketing, analise, operacao, confianca. track: local, digital ou ambos. mode: direct ou rag.
fields e expected devem ter exatamente as mesmas chaves. O gabarito aceita número, booleano, null, string curta e lista simples. Campos de texto livre ficam em rubric, NÃO em expected. O campo resposta já é adicionado pelo programa. Use o nome ordem apenas para lista em que a sequência importa. critical lista campos cujo erro deve zerar o caso. Não marque tudo como crítico.
Calcule os gabaritos passo a passo internamente e confira antes de responder. O modelo testado só receberá brief, fields e documentos recuperados; nunca dependa de informações ausentes ali. Inclua o que não está documentado como null, sem inventar respostas.
Vou revisar os gabaritos manualmente antes de importar. Não alegue que uma resposta esperada foi validada por uma pessoa.

Exemplo de estrutura:
${JSON.stringify(example,null,2)}`;
  try{await navigator.clipboard.writeText(prompt);toast('Prompt copiado. Cole na IA que você usa e revise os casos gerados.');}
  catch {showDialog(dialogHead('PRONTO PARA COPIAR','Prompt para criar seus testes')+`<textarea aria-label="Prompt para copiar" rows="18">${esc(prompt)}</textarea>`);}
}

document.addEventListener('click',async event=>{
  const el=event.target.closest('[data-action]');if(!el)return;
  try{
    switch(el.dataset.action){
      case 'new-run':openRun();break;
      case 'close':el.closest('dialog').close();break;
      case 'discover':await discover();break;
      case 'filter':caseFilter=el.dataset.filter;renderPage();break;
      case 'case-detail':caseDetail(el.dataset.id);break;
      case 'run-detail':runDetail(el.dataset.id);break;
      case 'answer-detail':answerDetail(el.dataset.id,Number(el.dataset.index));break;
      case 'cancel':await api('/api/cancel',{});el.disabled=true;el.textContent='Parada solicitada';toast('A execução para quando a requisição atual terminar ou atingir o timeout.');break;
      case 'reset-suite':await api('/api/suite/reset',{});await refresh();toast('Bateria AD3 selecionada. Seus testes e resultados anteriores continuam salvos.');break;
      case 'select-suite':await api('/api/suite/select',{id:el.dataset.id});await refresh();toast('Bateria selecionada.');break;
      case 'copy-prompt':await copyPrompt();break;
    }
  }catch(e){toast(e.message);}
});
document.addEventListener('input',event=>{if(event.target.id==='case-search'){searchTerm=event.target.value;$('#case-results').innerHTML=caseCards();}});
document.addEventListener('change',async event=>{
  if(event.target.id==='runtime'){const ports={ollama:11434,lmstudio:1234,llamacpp:8080};$('#endpoint').value=`http://127.0.0.1:${ports[event.target.value]}/v1`;$('#model-list').innerHTML='<p class="muted">Busque os modelos deste servidor.</p>';$('#connection-status').textContent='Abra o servidor local antes de conectar.';}
  if(event.target.closest('#run-form'))updateRunSize();
  if(event.target.id==='suite-file'){
    const file=event.target.files[0];if(!file)return;
    try{if(file.size>2_000_000)throw new Error('O limite do arquivo é 2 MB. Divida a base em trechos menores.');const suite=JSON.parse((await file.text()).replace(/^\uFEFF/,''));await api('/api/suite',suite);await refresh();toast('Bateria importada. Confira os casos antes de rodar.');}
    catch(e){$('#suite-error').textContent=e.message;}
  }
});
document.addEventListener('submit',async event=>{
  if(event.target.id==='run-form'){
    event.preventDefault();const form=event.target;const data=Object.fromEntries(new FormData(form));data.models=$$('input[name=model]:checked',form).map(i=>i.value);delete data.model;
    for(const k of ['repeats','temperature','max_tokens','timeout'])data[k]=Number(data[k]);
    $('#start-button').disabled=true;$('#run-error').textContent='';
    try{await api('/api/run',data);$('#run-dialog').close();location.hash='overview';await refresh();toast('Benchmark iniciado. Cada resposta fica salva neste PC.');}
    catch(e){$('#run-error').textContent=e.message;}finally{$('#start-button').disabled=false;}
  }
  if(event.target.id==='review-form'){
    event.preventDefault();const data=Object.fromEntries(new FormData(event.target));for(const k of ['utilidade','clareza','fidelidade'])data[k]=Number(data[k]);
    try{await api('/api/review',{...data,run_id:selectedRun.id,task_id:selectedRow.task_id,repeat:selectedRow.repeat});await refresh(false);toast('Revisão humana salva.');}
    catch(e){toast(e.message);}
  }
});
route();
refresh().catch(e=>{$('#page').innerHTML=`<div class="panel padded"><h2>Não conseguimos conectar ao laboratório.</h2><p class="muted">${esc(e.message)}</p><p>Abra o aplicativo com <code>python bench.py</code> e recarregue esta página.</p></div>`;});
