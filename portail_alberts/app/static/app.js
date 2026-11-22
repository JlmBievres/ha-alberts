/* Portail Les Alberts, version simple : interface voyageurs (aucune bibliothèque externe).
   Routage par l'adresse (#/...) : le bouton « retour » du navigateur fonctionne. */
'use strict';

// ------------------------------------------------------------------ état
const S = {
  etat: null, prises: null, meteo: null, guide: null,
  horsLigne: false, derniere: 0, essai: 0, glisse: false,
  recherche: '', dep: null, pile: 0,
};
try { S.guide = JSON.parse(localStorage.getItem('alberts.guide') || 'null'); } catch (e) { /* stockage indisponible */ }

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const attrJ = o => esc(JSON.stringify(o));
const $ = s => document.querySelector(s);
const local = {
  get(k) { try { return JSON.parse(localStorage.getItem('alberts.' + k) || '[]'); } catch (e) { return []; } },
  set(k, v) { try { localStorage.setItem('alberts.' + k, JSON.stringify(v)); } catch (e) { /* ignoré */ } },
};

// ------------------------------------------------------------------ icônes (traits)
const P = {
  maison: 'M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  chauffage: 'M12 3v10.5a3.5 3.5 0 1 1-4 0V5a2 2 0 0 1 4 0M16 7h4M16 11h4',
  lumieres: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z',
  meteo: 'M7 18a5 5 0 0 1 .5-10 7 7 0 0 1 13 2.5A4 4 0 0 1 19 18z',
  arrivee: 'M10 17l5-5-5-5M15 12H3M14 3h6v18h-6',
  depart: 'M15 17l5-5-5-5M20 12H8M10 3H4v18h6',
  guide: 'M4 4h6a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-6a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h7z',
  retour: 'M15 18l-6-6 6-6',
  goutte: 'M12 3s-6 7-6 11a6 6 0 0 0 12 0c0-4-6-11-6-11z',
  wifi: 'M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01',
  porte: 'M5 21V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v17M3 21h18M15 12h.01',
  flamme: 'M12 3c1 3 4 5 4 9a4 4 0 0 1-8 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 0-8zM5 21h14',
  lune: 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z',
  ok: 'M7 12.5l3.2 3L17 9',
  alerte: 'M12 3l10 18H2zM12 10v5M12 18h.01',
  horloge: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2',
  ampoule: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z',
  loupe: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-3.5-3.5',
  tel: 'M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2',
  vent: 'M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8',
  prise: 'M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4',
  soleil: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  feuille: 'M5 19c0-9 6-14 15-14 0 9-5 15-14 15M5 19l8-8',
  flocon: 'M12 2v20M4 6l16 12M20 6L4 18M9 3l3 3 3-3M9 21l3-3 3 3',
};
const ic = (n, t = 22, c = 'currentColor', w = 2) =>
  `<svg width="${t}" height="${t}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${P[n] || ''}"></path></svg>`;
const LOGO = `<svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true"><defs><linearGradient id="lgA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0E2F3E"/><stop offset=".55" stop-color="#17506A"/><stop offset="1" stop-color="#2FA6DA"/></linearGradient><clipPath id="lcA"><rect width="40" height="40" rx="10"/></clipPath></defs><g clip-path="url(#lcA)"><rect width="40" height="40" fill="url(#lgA)"/><circle cx="29" cy="11" r="4" fill="#F8C81E"/><path d="M-2 32L9 20L13 24L19 17L27 26L32 22L42 31V42H-2Z" fill="#7FCBEA" opacity=".55"/><path d="M-2 40V34L10 25L14 28L21 15L28 24L31 22L42 33V40Z" fill="#fff"/><path d="M21 15L19.4 22L21.6 20.6L20.6 26.5L23.6 20.2Z" fill="#17506A" opacity=".28"/></g></svg>`;
const FLECHE = `<svg class="fleche" width="64" height="64" viewBox="0 0 60 60" fill="none" stroke="#fff" stroke-width="2.2" aria-hidden="true"><path d="M14 6a6 6 0 0 0-6 6v36a4 4 0 0 0 4 4h36a6 6 0 0 0 0-12H28l24-24a6 6 0 0 0-8.5-8.5L20 31.5V12a6 6 0 0 0-6-6z"/></svg>`;

// ------------------------------------------------------------------ réseau
async function api(chemin, corps) {
  const r = await fetch(chemin, corps ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) } : {});
  const d = await r.json().catch(() => ({}));
  if (!r.ok && !corps) throw new Error(d.erreur || r.status);
  return d;
}

async function rafraichir() {
  try {
    S.etat = await api('/api/etat');
    S.derniere = Date.now(); S.horsLigne = false;
  } catch (e) {
    S.horsLigne = true; S.essai = 20;
  }
  if (!S.glisse && !document.querySelector('.dialogue')) rendre(false);
}

async function charger(cle, url, duree) {
  const v = S[cle];
  if (v && Date.now() - v._t < duree) return v;
  try { const d = await api(url); d._t = Date.now(); S[cle] = d; return d; } catch (e) { return v; }
}

async function chargerGuide() {
  try {
    S.guide = await api('/api/guide');
    try { localStorage.setItem('alberts.guide', JSON.stringify(S.guide)); } catch (e) { /* stockage plein ou interdit */ }
  } catch (e) { /* on garde la copie locale */ }
  return S.guide;
}

// ------------------------------------------------------------------ actions
async function agir(a, bouton) {
  S.occupe = true;
  try {
    const r = await api('/api/action', a);
    if (!r.ok) toast(r.message || 'La commande n’a pas abouti.', a);
  } catch (e) {
    toast('La maison ne répond pas. Réessayez dans un instant.', a);
  }
  S.occupe = false;
  await rafraichir();
}

function toast(msg, a) {
  const c = $('#calque');
  c.querySelector('.toast')?.remove();
  const d = document.createElement('div');
  d.className = 'toast'; d.setAttribute('role', 'alert');
  d.innerHTML = `${ic('alerte', 28, '#F08A5D', 2.2)}<div style="flex:1"><b>Ça n’a pas marché</b><p style="opacity:.85;margin:2px 0 10px">${esc(msg)}</p>
    <div class="boutons">${a ? `<button class="bouton" data-reessayer>Réessayer</button>` : ''}<a class="bouton" style="background:transparent;color:#fff;border-color:rgba(255,255,255,.5)" href="#/guide">Que faire ?</a></div></div>
    <button class="fermer" aria-label="Fermer">×</button>`;
  d.querySelector('.fermer').onclick = () => d.remove();
  const re = d.querySelector('[data-reessayer]');
  if (re) re.onclick = () => { d.remove(); agir(a); };
  c.appendChild(d);
  setTimeout(() => d.remove(), 15000);
}

document.addEventListener('click', e => {
  const r = e.target.closest('a.retour');
  if (r && S.pile > 1) { e.preventDefault(); history.back(); return; }
  const b = e.target.closest('[data-a]');
  if (b) {
    e.preventDefault(); e.stopPropagation();
    // Réponse visuelle immédiate, sans attendre Home Assistant
    if (b.classList.contains('inter')) b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') !== 'true');
    else if (b.parentElement.matches('.modes4,.ambiances')) { b.parentElement.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); }
    agir(JSON.parse(b.dataset.a), b); return;
  }
  const dp = e.target.closest('[data-dep]');
  if (dp) { e.preventDefault(); depannageChoix(JSON.parse(dp.dataset.dep)); }
});
// Curseurs d'intensité : l'ordre part quand on relâche le curseur
document.addEventListener('change', e => {
  const g = e.target.closest('[data-glisse]');
  if (g) { S.glisse = false; const a = JSON.parse(g.dataset.glisse); a[a.type === 'lampe' ? 'luminosite' : 'pct'] = +g.value; agir(a); }
});
document.addEventListener('input', e => {
  const g = e.target.closest('[data-glisse]');
  if (g) { S.glisse = true; const o = g.parentElement.querySelector('output'); if (o) o.textContent = g.value + ' %'; }
  if (e.target.id === 'recherche') { S.recherche = e.target.value; rendreListeGuide(); }
});

// ------------------------------------------------------------------ routage
const route = () => { const [r = '', a = '', b = ''] = location.hash.replace(/^#\/?/, '').split('/'); return { r, a: decodeURIComponent(a), b }; };
window.addEventListener('hashchange', () => { S.pile++; rendre(true); });
const MENU = [['', 'maison', 'Maison', 'bleu'], ['lumieres', 'lumieres', 'Lumières', 'bleu'], ['meteo', 'meteo', 'Météo', 'violet'],
  ['guide', 'guide', 'Guide', 'jaune'], ['prises', 'prise', 'Prises', 'ardoise']];
const ACTIF = { '': '', piece: '', lumieres: 'lumieres', meteo: 'meteo', guide: 'guide', depannage: 'guide', prises: 'prises' };
function menu(r) {
  const actif = ACTIF[r] ?? '';
  $('#menu').innerHTML = `<a class="marque" href="#/">${LOGO}<span><b>Les Alberts</b><small>MONTGENÈVRE</small></span></a>` +
    MENU.map(([h, i, l, c]) => `<a class="it s-${c}${h === actif ? ' on' : ''}" href="#/${h}"${h === actif ? ' aria-current="page"' : ''}>${ic(i, 24)}${l}</a>`).join('');
  $('#onglets').innerHTML = MENU.map(([h, i, l, c]) => `<a class="s-${c}${h === actif ? ' on' : ''}" href="#/${h}">${ic(i)}${l}</a>`).join('');
}
const VUES = { '': accueil, piece: vuePiece, lumieres: vueLumieres, meteo: vueMeteo, guide: vueGuide, depannage: vueDepannage, prises: vuePrises };
const STATIQUES = new Set(['guide', 'depannage', 'meteo']);

async function rendre(nouvelle = true) {
  const { r, a, b } = route();
  if (!nouvelle && STATIQUES.has(r)) return;
  menu(r);
  const v = VUES[r] || accueil;
  if (!S.etat && !STATIQUES.has(r)) {
    $('#vue').innerHTML = S.horsLigne ? horsLigneComplet() : '<div class="chargement">Lecture de la maison…</div>';
    return;
  }
  const html = await v(a, b);
  const y = window.scrollY;
  $('#vue').innerHTML = (S.horsLigne && !STATIQUES.has(r) ? bandeHorsLigne() : '') + html;
  if (nouvelle) { window.scrollTo(0, 0); $('#vue').focus({ preventScroll: true }); } else window.scrollTo(0, y);
  if (S.horsLigne && !STATIQUES.has(r)) $('#vue').querySelectorAll('button,[data-a],input').forEach(x => x.closest('.horsligne') || x.setAttribute('disabled', ''));
}

// ------------------------------------------------------------------ morceaux communs
// ------------------------------------------------------------------ morceaux communs
function bandeau(sec, sur, titre, { retour, droite = '', grand = false } = {}) {
  return `<header class="bandeau ${sec}${grand ? ' grand' : ''}">
    ${retour ? `<a class="retour" href="${retour}" aria-label="Retour">${ic('retour', 20, 'currentColor', 2.4)}</a>` : ''}
    <h1><span class="sur">${esc(sur)}</span>${titre}</h1>${droite}</header>`;
}
const heure = t => new Date(t).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }).replace(':', ' h ');
function bandeHorsLigne() {
  return `<div class="horsligne">${ic('alerte', 24, '#F8C81E')}<div style="flex:1"><b>La maison ne répond pas.</b>
    Valeurs de ${S.derniere ? heure(S.derniere) : '—'}, commandes en pause. Nouvel essai automatique.</div>
    <button class="bouton" onclick="rafraichir()">Réessayer</button><a class="bouton" href="#/guide">Ouvrir le guide</a></div>`;
}
function horsLigneComplet() {
  return bandeau('gris', 'Connexion à la maison', 'La maison ne répond pas') + `<div class="carte">
    <h2>Les commandes sont en pause</h2><p class="doux" style="margin-bottom:12px">Le portail n’arrive pas à joindre Home Assistant. Le chauffage et les automatismes continuent de fonctionner seuls.</p>
    <ol style="line-height:1.7;padding-left:22px;margin:0"><li><b>Attendez 5 minutes</b> : la box redémarre peut-être.</li><li><b>Les lumières marchent-elles ?</b> Sinon, c’est une coupure de courant.</li>
    <li><b>Votre téléphone est-il sur le WiFi de la maison ?</b></li><li>Toujours rien : appelez le propriétaire.</li></ol>
    <div class="boutons" style="margin-top:14px"><button class="bouton sombre" onclick="rafraichir()">Réessayer</button><a class="bouton" href="#/depannage/courant">Plus de courant ?</a><a class="bouton" href="#/guide">Ouvrir le guide</a></div></div>`;
}
function inter(on, label, a, taille = '') {
  return `<button class="inter${taille}" aria-label="${esc(label)}" aria-pressed="${on}" data-a='${attrJ(a)}'></button>`;
}

// ------------------------------------------------------------------ accueil
function accueil() {
  const E = S.etat, x = E.exterieur;
  return `<header class="bandeau grand"><div><span class="sur">Montgenèvre · Hautes-Alpes</span><h1>Bienvenue aux Alberts</h1></div>
    <span class="droite" style="text-shadow:0 1px 2px rgba(0,0,0,.25)">Dehors ${x.t ? esc(x.t) + ' °C' : '—'}<br>${esc((x.condition || '').toLowerCase())}</span></header>
    <h2 class="titre-page">Les pièces</h2>
    <div class="grille g5">${E.pieces.map(cartePiece).join('')}</div>`;
}
const DIAG = { chauffe: ['#FDE8D7', '#8A3E0E'], ok: ['#E4F1EA', '#2F6B4F'], panne: ['#B4561A', '#FFFFFF'], eco: ['#EEF1F3', '#3E4C56'], arret: ['#EEF1F3', '#56656F'], ko: ['#B4561A', '#FFFFFF'] };
function ligneChauffage(p) {
  const c = p.chauffage;
  if (!c) return p.t ? '<span class="petit" style="color:#8A97A1">Pas de chauffage</span>' : '<span class="petit doux">Détecteur la nuit</span>';
  if (c.type === 'poele') return `<span class="ligne-ch">${ic('flamme', 16, '#7A4E24')}<b>Poêle</b><span class="pastille" style="background:${c.etat === 'on' ? '#FDE8D7' : '#EEF1F3'};color:${c.etat === 'on' ? '#8A3E0E' : '#56656F'}">${esc(c.libelle)}</span></span>`;
  const [f, t] = DIAG[c.diag] || DIAG.arret;
  const court = { chauffe: 'chauffe', ok: 'à température', panne: 'ne chauffe pas', eco: 'éco', arret: 'hors-gel', ko: 'ne répond pas' }[c.diag];
  return `<span class="ligne-ch">${ic('chauffage', 16, '#3A6EA5')}<b>${esc(c.libelle)}</b><span class="pastille" style="background:${f};color:${t}">${court}</span></span>`;
}
function lignePorte(p, bord = true) {
  const o = p.porte.etat === 'ouverte', k = p.porte.etat === 'inconnu';
  return `<div class="pied-lum${bord ? '' : ' sans-bord'}">${ic('porte', 20, o ? '#B4561A' : k ? '#8A97A1' : '#2F6B4F')}<span style="flex:1;color:${o ? 'var(--warn)' : k ? '#8A97A1' : 'var(--ok)'}">Porte : ${k ? 'état inconnu' : o ? 'ouverte' : 'fermée'}</span></div>`;
}
function cartePiece(p) {
  const L = p.lumiere, on = L.etat === 'on';
  let pied = '';
  if (L.etat !== 'none') {
    pied = `<div class="pied-lum">${ic('ampoule', 20, on ? '#8A6A00' : '#56656F', 2.2)}<span style="flex:1;color:${on ? 'var(--lum-ink)' : 'var(--doux)'}">${on ? (L.nb > 1 ? L.texte : 'Allumée') : 'Éteinte'}</span>
       ${inter(on, 'Lumière ' + p.nom, { type: 'piece_lumiere', piece: p.id, valeur: on ? 'off' : 'on' })}</div>`;
    if (p.porte) pied = lignePorte(p) + pied.replace('class="pied-lum"', 'class="pied-lum sans-bord"');
  } else if (p.porte) {
    pied = lignePorte(p);
  } else {
    pied = `<div class="pied-lum aucun">${ic('ampoule', 20, '#8A97A1', 2.2)}Pas de lumière pilotée</div>`;
  }
  return `<div class="piece${on ? ' allumee' : ''}"><a class="nom" href="#/piece/${esc(p.id)}">${esc(p.nom)} ›</a>
    ${p.t ? `<span style="display:flex;align-items:baseline;gap:8px"><span class="temp">${esc(p.t)}°</span><span class="${p.humide ? 'etat-ko' : 'doux'}">${esc(p.h || '')}</span></span>` : '<span style="height:38px"></span>'}
    ${ligneChauffage(p)}${pied}</div>`;
}

// ------------------------------------------------------------------ pièce
function vuePiece(id) {
  const p = S.etat.pieces.find(x => x.id === id);
  if (!p) return bandeau('bleu', 'Pièce', 'Pièce inconnue', { retour: '#/' });
  const droite = p.t ? `<span class="droite"><b>${esc(p.t)} °C</b>${p.h ? esc(p.h) + ' d’humidité' : ''}</span>` : '';
  const droiteCol = [];
  if (p.chauffage?.type === 'poele') droiteCol.push(cartePoele(p));
  if (p.chauffage?.type === 'radiateur') droiteCol.push(carteRadiateur(p));
  if (p.porte) droiteCol.push(cartePorte(p));
  if (p.ventilation) droiteCol.push(carteVentilation(p));
  if (p.conseils.length) droiteCol.push(`<div class="carte"><h2>Bon à savoir</h2><ul style="margin:0;padding-left:20px;line-height:1.6">${p.conseils.map(c => `<li>${esc(c)}</li>`).join('')}</ul></div>`);
  const sansLumiere = p.lumiere.etat === 'none';
  let gauche = panneauLumieres(p);
  if (sansLumiere && droiteCol.length) {          // pas de lumière : le chauffage passe devant
    gauche = droiteCol.shift();
    droiteCol.push(panneauLumieres(p));
  }
  return bandeau('bleu', 'Pièce', esc(p.nom), { retour: '#/', droite }) +
    `<div class="grille" style="grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);align-items:start" id="g-piece">
     <div>${gauche}</div><div class="col">${droiteCol.join('')}</div></div>
     <style>@media (max-width:899px){#g-piece{grid-template-columns:minmax(0,1fr)!important}}</style>`;
}
function panneauLumieres(p) {
  const L = p.lumiere;
  if (L.etat === 'none') return `<div class="carte ligne">${ic('ampoule', 22, '#8A97A1')}<div><b>Pas de lumière pilotée</b><div class="doux petit">Utilisez les interrupteurs de la pièce.</div></div></div>`;
  const on = L.etat === 'on';
  const amb = L.variable ? `<div class="sous-titre">Ambiance</div><div class="ambiances">${S.etat.ambiances.map(a =>
    `<button class="${on && L.luminosite && Math.abs(L.luminosite - a.pct) <= 3 ? 'on' : ''}" data-a='${attrJ({ type: 'piece_lumiere', piece: p.id, valeur: 'ambiance', ambiance: a.id })}'>${esc(a.nom)}<span>${a.pct} %</span></button>`).join('')}</div>` : '';
  const lampes = p.lampes.length > 1 || p.lampes.some(l => l.variable || l.minuterie_min) ? `<div class="sous-titre">${p.lampes.length > 1 ? 'Lampe par lampe' : 'Réglage'}</div>${p.lampes.map(l => ligneLampe(p, l)).join('')}` : '';
  return `<section class="panneau-lum"><div class="ligne"><div style="flex:1"><h2>Lumières</h2><div class="sous">${p.lampes.length > 1 ? (L.nb_on ? `${L.nb_on} lampe${L.nb_on > 1 ? 's' : ''} allumée${L.nb_on > 1 ? 's' : ''} sur ${L.nb}` : 'Aucune lampe allumée') : esc(L.texte)}</div></div>
    ${inter(on, 'Toute la pièce', { type: 'piece_lumiere', piece: p.id, valeur: on ? 'off' : 'on' }, ' grand')}</div>
    ${amb}${lampes}<p class="petit" style="color:#6B5A1E;margin:0">Une lampe ne répond pas ? Vérifiez que son interrupteur mural est allumé.</p></section>`;
}
function ligneLampe(p, l) {
  const a = { type: 'lampe', piece: p.id, lampe: l.id };
  if (l.sans_courant) return `<div class="lampe-c"><div class="ligne">${ic('ampoule', 20, '#8A97A1')}<span style="flex:1"><b>${esc(l.nom)}</b><br><span class="petit doux">Sans courant : prise coupée</span></span></div></div>`;
  if (l.ko) return `<div class="lampe-c"><div class="ligne">${ic('ampoule', 20, '#B4561A')}<span style="flex:1"><b>${esc(l.nom)}</b><br><span class="ko">Ne répond pas : vérifiez l’interrupteur mural.</span></span>
    <button class="bouton" data-a='${attrJ(Object.assign({ valeur: 'on' }, a))}'>Réessayer</button></div></div>`;
  const glis = l.variable && l.on ? `<label class="curseur"><output>${l.luminosite || 100} %</output><input type="range" min="1" max="100" value="${l.luminosite || 100}" aria-label="Intensité ${esc(l.nom)}" data-glisse='${attrJ(Object.assign({ valeur: 'on' }, a))}'></label>` : '';
  const minu = l.minuterie_min && !l.on ? `<button class="bouton" data-a='${attrJ(Object.assign({ valeur: 'on', minutes: true }, a))}'>Allumer ${l.minuterie_min} min</button>` : '';
  const reste = l.reste ? `<br><span class="petit" style="color:#6B5A1E">S’éteint dans ${Math.ceil(l.reste / 60)} min</span>` : '';
  return `<div class="lampe-c"><div class="ligne">${ic('ampoule', 20, l.on ? '#8A6A00' : '#8A97A1')}<span style="flex:1"><b>${esc(l.nom)}</b>${reste}</span>${minu}
    ${inter(l.on, l.nom, Object.assign({ valeur: l.on ? 'off' : 'on' }, a))}</div>${glis}</div>`;
}
function cartePoele(p) {
  const c = p.chauffage, cl = c.etat === 'on' ? '' : ' gris';
  return `<section class="poele"><div class="ligne">${ic('flamme', 26, '#7A4E24')}<h2 style="flex:1">Chauffage : poêle</h2><span class="pil${cl}">${esc(c.libelle)}</span></div>
    <div>Le poêle se règle sur sa console. Remplissez-le et nettoyez-le tous les deux jours, poêle froid.</div>
    <div class="boutons"><a class="bouton poele" href="#/guide/nettoyer">Nettoyage pas à pas</a><a class="bouton" href="#/guide/alarme">Le poêle est en alarme</a></div></section>`;
}
function carteRadiateur(p) {
  const c = p.chauffage;
  if (!c.dispo) return `<section class="carte radiateur"><h2>Chauffage</h2><p class="etat-ko">Le radiateur ne répond pas. Vérifiez qu’il est sous tension.</p></section>`;
  const [f, t] = DIAG[c.diag] || DIAG.arret;
  const pre = S.etat.prechauffage;
  return `<section class="carte radiateur"><div class="ligne" style="flex-wrap:wrap"><h2 style="flex:1;margin:0">Chauffage</h2><span class="pastille grande" style="background:${f};color:${t}">${esc(c.etat)}</span></div>
    ${c.panne ? `<div class="important" style="margin-top:10px"><b>La pièce reste froide.</b> Vérifiez que le sélecteur du radiateur est sur la position pilotée et que son thermostat est monté.</div>` : ''}
    <div class="modes4" style="margin-top:12px">${c.modes.map(m => `<button class="${m.valeur === c.mode ? 'on' : ''}" aria-pressed="${m.valeur === c.mode}" data-a='${attrJ({ type: 'mode', piece: p.id, valeur: m.valeur })}'>${ic(m.icone || 'chauffage', 26, 'currentColor', 2)}<b>${esc(m.libelle)}</b><span>${esc(m.sous)}</span></button>`).join('')}</div>
    ${c.aide ? `<p class="explic">${esc(c.aide)}</p>` : ''}
    ${pre ? '<p class="doux petit" style="margin-top:8px">La nuit, la maison préchauffe en heures creuses, puis revient au mode choisi.</p>' : ''}</section>`;
}
function cartePorte(p) {
  const o = p.porte.etat === 'ouverte', k = p.porte.etat === 'inconnu';
  return `<div class="carte ligne">${ic('porte', 26, o ? '#B4561A' : '#2F6B4F')}<div style="flex:1"><b>${esc(p.porte.nom)}</b><div class="${o ? 'etat-ko' : k ? 'doux' : 'etat-on'}">${k ? 'État inconnu' : o ? 'Ouverte' : 'Fermée'}</div></div></div>`;
}
function carteVentilation(p) {
  const v = p.ventilation;
  const etat = v.ko ? '<span class="etat-ko">Ne répond pas</span>' : v.on ? `<span class="etat-on">En marche${v.reste ? ', maintenue encore ' + Math.ceil(v.reste / 60) + ' min' : ''}</span>` : '<span class="etat-off">Arrêtée</span>';
  return `<div class="carte"><div class="ligne"><div style="flex:1"><h2 style="margin:0">Ventilation</h2>${etat}</div>
    ${inter(v.on, 'Ventilation', { type: 'ventilation', piece: p.id, valeur: v.on ? 'off' : 'on' }, ' vert')}</div>
    <div class="doux petit" style="margin:6px 0 10px">${esc(v.arret_auto)}</div>
    <button class="bouton" data-a='${attrJ({ type: 'ventilation', piece: p.id, valeur: 'maintien' })}'>Maintenir ${v.maintien_min} min</button></div>`;
}

// ------------------------------------------------------------------ lumières
function vueLumieres() {
  const E = S.etat, avec = E.pieces.filter(p => p.lampes.length);
  const n = avec.filter(p => p.lumiere.etat === 'on').length;
  return bandeau('bleu', 'Piloter la maison', 'Lumières', {
    droite: `<span class="droite"><span class="pilule-b">${n ? `Allumées dans ${n} pièce${n > 1 ? 's' : ''}` : 'Tout est éteint'}</span></span>` }) +
    (n ? `<div class="boutons"><button class="bouton sombre" data-a='${attrJ({ type: 'maison_lumiere', valeur: 'off' })}'>Tout éteindre</button>
      <button class="bouton" data-a='${attrJ({ type: 'maison_lumiere', valeur: 'veilleuse' })}'>Veilleuse partout</button></div>` : '') +
    `<div class="grille g4">${avec.map(p => {
      const L = p.lumiere, on = L.etat === 'on';
      const glis = on && L.variable ? `<label class="curseur"><output>${L.luminosite || 100} %</output><input type="range" min="1" max="100" value="${L.luminosite || 100}" aria-label="Intensité ${esc(p.nom)}" data-glisse='${attrJ({ type: 'piece_lumiere', piece: p.id, valeur: 'luminosite' })}'></label>` : '';
      return `<div class="piece${on ? ' allumee' : ''}" style="min-height:0"><div class="ligne"><a class="nom" href="#/piece/${esc(p.id)}" style="flex:1">${esc(p.nom)} ›<br><span class="petit" style="font-weight:600;color:${on ? 'var(--lum-ink)' : 'var(--doux)'}">${esc(L.texte)}${on && L.luminosite ? ', ' + L.luminosite + ' %' : ''}</span></a>
        ${inter(on, 'Lumière ' + p.nom, { type: 'piece_lumiere', piece: p.id, valeur: on ? 'off' : 'on' })}</div>${glis}
        <div class="boutons">${p.lampes.map(l => `<span class="chip${l.on ? ' chip-on' : ''}">${esc(l.nom)}${l.ko ? ' : ne répond pas' : ''}</span>`).join('')}</div></div>`;
    }).join('')}</div>`;
}

// ------------------------------------------------------------------ prises (lecture seule)
async function vuePrises() {
  try { S.prises = await api('/api/prises'); } catch (e) { /* on garde la dernière lecture */ }
  const P = S.prises;
  if (!P) return bandeau('ardoise', 'État de la maison', 'Prises') + '<div class="carte doux">État indisponible pour le moment.</div>';
  const n = P.compte;
  return bandeau('ardoise', 'État de la maison', 'Prises', { droite: `<span class="droite">${n.on} allumée${n.on > 1 ? 's' : ''} · ${n.off} coupée${n.off > 1 ? 's' : ''}${n.ko ? `<br><span style="color:#FFD0B5">${n.ko} ne répond pas</span>` : ''}</span>` }) +
    `<div class="grille g2" style="align-items:start">${P.groupes.map(g => `<section class="carte"><h2 style="margin-bottom:2px">${esc(g.groupe)}</h2>${g.prises.map(x =>
      `<div class="prise"><span class="point ${x.etat}"></span><span style="flex:1;font-weight:700">${esc(x.nom)}</span><span class="pil-${x.etat}">${esc(x.texte)}</span></div>`).join('')}</section>`).join('')}</div>
    <p class="doux petit">Lecture seule : les prises se commandent depuis Home Assistant. Mis à jour à ${heure(Date.now())}.</p>`;
}

// ------------------------------------------------------------------ météo
const VENTS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO'];
const CIEL = { 'clear-night': '☾', sunny: '☀', partlycloudy: '⛅', cloudy: '☁', rainy: '🌧', pouring: '🌧', snowy: '❄', 'snowy-rainy': '🌨', fog: '🌫', lightning: '⚡', 'lightning-rainy': '⛈', windy: '💨', hail: '🌨' };
async function vueMeteo() {
  const M = await charger('meteo', '/api/meteo', 600000);
  if (!M) return bandeau('violet', 'S’informer', 'Météo') + '<div class="carte doux">Météo indisponible pour le moment.</div>';
  const vig = M.vigilance && !/vert|green/i.test(M.vigilance) ? `<span class="droite"><span class="pilule-b" style="background:#FFE58A;color:#4A3A00">Vigilance ${esc(M.vigilance.toLowerCase())}</span></span>` : '';
  const conseils = [];
  const gel = M.jours.filter(j => j.min && parseFloat(j.min.replace(',', '.')) < 0);
  if (gel.length) conseils.push(`Gel prévu ${gel.length > 1 ? 'plusieurs nuits' : 'cette nuit'} : routes glissantes le matin.`);
  const neige = M.jours.find(j => /snow/.test(j.cond || ''));
  if (neige) conseils.push(`Neige possible ${esc(neige.j)} (${esc(neige.mm)} mm) : pneus neige ou chaînes.`);
  if (M.vigilance && !/vert|green/i.test(M.vigilance)) conseils.push('Vigilance en cours : consultez Météo-France avant de prendre la route.');
  conseils.push('Rentrez le bois et les granulés au sec.');
  const vd = M.vent_dir != null ? VENTS[Math.round(M.vent_dir / 22.5) % 16] + ', ' : '';
  return bandeau('violet', 'S’informer', 'Météo', { droite: vig }) + `<div class="grille g2" style="align-items:start"><div class="col">
    <div class="carte"><div class="ligne"><span style="font-size:54px;line-height:1" aria-hidden="true">${CIEL[M.cond] || ''}</span><div style="flex:1"><b style="font-size:24px">${esc(M.cond_txt || '')}</b><div class="doux">${esc(M.lieu)}</div></div><b style="font-size:56px;line-height:1">${esc(M.t || '–')}°</b></div>
      <div class="g2f" style="margin-top:12px"><div><span class="doux">Vent</span><br><b>${vd}${esc(M.vent || '–')} km/h</b></div><div><span class="doux">Humidité</span><br><b>${M.humidite ?? '–'} %</b></div>
      <div><span class="doux">Pression</span><br><b>${esc(M.pression || '–')} hPa</b></div><div><span class="doux">Nuages</span><br><b>${M.nuages ?? '–'} %</b></div></div></div>
    <div class="carte"><h2>Prochaines heures</h2><div class="heures">${M.heures.map(x => `<div><b>${esc(x.h)}</b><div style="font-size:22px" aria-hidden="true">${CIEL[x.cond] || ''}</div><b>${esc(x.t)}°</b><div class="petit" style="color:#3A6EA5">${esc(x.mm)} mm</div></div>`).join('')}</div></div>
    <div class="carte"><h2>Soleil</h2><div class="soleil">${[['Aube', 'aube'], ['Lever', 'lever'], ['Midi solaire', 'midi'], ['Coucher', 'coucher'], ['Crépuscule', 'crepuscule']].map(([l, k]) => `<div><span class="doux petit">${l}</span><br><b>${esc(M.soleil[k] || '–')}</b></div>`).join('')}</div></div></div>
    <div class="col"><div class="carte jours"><h2>Prochains jours</h2>${M.jours.map(j => `<div class="j"><b>${esc(j.j)}</b><span><span aria-hidden="true">${CIEL[j.cond] || ''}</span> <span class="doux">${esc(j.mm)} mm</span></span><b>${esc(j.max)}°</b><span style="color:#3A6EA5;font-weight:700">${esc(j.min)}°</span></div>`).join('')}</div>
    <div class="conseils-sejour"><h2 style="font-size:19px;margin-bottom:6px">Conseils pour votre séjour</h2><ul style="margin:0;padding-left:20px;line-height:1.6">${conseils.map(c => `<li>${c}</li>`).join('')}</ul></div></div></div>`;
}

// ------------------------------------------------------------------ guide
function toutesFiches(G) { return (G?.themes || []).flatMap(t => (t.fiches || []).map(f => Object.assign({ theme: t.titre, couleur: t.couleur }, f))); }
async function vueGuide(id) {
  const G = await chargerGuide();
  if (!G) return bandeau('jaune', 'Guide', 'Guide de la maison') + '<div class="carte doux">Guide indisponible.</div>';
  const tel = matchMedia('(max-width:899px)').matches;
  const fiches = toutesFiches(G);
  const f = fiches.find(x => x.id === id) || (!tel ? fiches[0] : null);
  let h = bandeau('jaune', f && tel ? f.theme : 'Guide', f && tel ? esc(f.titre) : esc(G.titre || 'Guide de la maison'), { retour: f && tel ? '#/guide' : null });
  if (!(f && tel)) {
    h += `<div class="carte"><h2 style="margin-bottom:8px">Un problème ?</h2><div class="boutons">${(G.depannages || []).map(d => `<a class="bouton" href="#/depannage/${esc(d.id)}">${esc(d.titre)}</a>`).join('')}</div></div>`;
  }
  const liste = `<div><label class="recherche">${ic('loupe', 20, '#56656F')}<span class="cache">Chercher dans le guide</span><input id="recherche" type="search" placeholder="Chercher : granulés, Linky, draps…" value="${esc(S.recherche)}"></label>
    <nav class="liste-fiches" id="liste-fiches" aria-label="Fiches du guide" style="margin-top:10px">${listeFiches(G, f && f.id)}</nav></div>`;
  if (tel) return h + (f ? fiche(f, fiches) : liste);
  return h + `<div class="guide">${liste}${f ? fiche(f, fiches) : ''}</div>`;
}
function listeFiches(G, actif) {
  const q = S.recherche.trim().toLowerCase();
  return (G.themes || []).map(t => {
    const fs = (t.fiches || []).filter(f => !q || (f.titre + ' ' + (f.etapes || []).join(' ')).toLowerCase().includes(q));
    if (!fs.length) return '';
    return `<h3 style="color:${esc(t.couleur || 'var(--doux)')}">${esc(t.titre)}</h3>${fs.map(f => `<a href="#/guide/${esc(f.id)}" class="${f.id === actif ? 'on' : ''}">${esc(f.titre)}</a>`).join('')}`;
  }).join('') || '<p class="doux" style="padding:12px 16px">Aucune fiche ne correspond.</p>';
}
function rendreListeGuide() {
  const l = $('#liste-fiches');
  if (l && S.guide) l.innerHTML = listeFiches(S.guide, route().a);
}
function fiche(f, fiches) {
  const voir = (f.voir_aussi || []).map(id => fiches.find(x => x.id === id)).filter(Boolean);
  return `<article class="carte"><span class="doux petit gras" style="color:${esc(f.couleur || '')}">${esc(f.theme)}</span><h2 style="font-size:26px;margin:2px 0 8px">${esc(f.titre)}</h2>
    ${f.duree ? `<span class="chip">${esc(f.duree)}</span>` : ''}
    ${f.photo ? `<img class="photo" style="margin-top:12px" src="/guide/photos/${encodeURIComponent(f.photo)}" alt="${esc(f.titre)}">` : ''}
    <ol class="etapes" style="margin-top:10px">${(f.etapes || []).map(e => `<li>${esc(e)}</li>`).join('')}</ol>
    ${f.important ? `<div class="important" style="margin-top:10px"><b>Important :</b> ${esc(f.important)}</div>` : ''}
    ${voir.length ? `<h3 style="margin:16px 0 6px">Voir aussi</h3><div class="boutons">${voir.map(v => `<a class="bouton" href="#/guide/${esc(v.id)}">${esc(v.titre)}</a>`).join('')}</div>` : ''}</article>`;
}

// ------------------------------------------------------------------ dépannage
async function vueDepannage(id) {
  const G = await chargerGuide();
  const d = (G?.depannages || []).find(x => x.id === id);
  if (!d) return bandeau('jaune', 'Un problème ?', 'Dépannage introuvable', { retour: '#/guide' });
  if (!S.dep || S.dep.id !== id) S.dep = { id, q: d.debut || d.questions[0].id, n: 1, fin: null };
  const fiches = toutesFiches(G);
  let corps;
  if (S.dep.fiche) {
    const f = fiches.find(x => x.id === S.dep.fiche);
    corps = `<span class="doux petit gras">Solution</span>${f ? fiche(f, fiches) : ''}`;
  } else if (S.dep.fin) {
    corps = `<div class="carte"><span class="doux petit gras">Solution</span><p style="font-size:18px;margin-top:6px">${esc(S.dep.fin)}</p></div>`;
  } else {
    const q = d.questions.find(x => x.id === S.dep.q);
    corps = `<div class="carte"><span class="doux petit gras">Question ${S.dep.n}</span><h2 style="font-size:22px;margin:4px 0">${esc(q.texte)}</h2>${q.aide ? `<p class="doux" style="margin-bottom:10px">${esc(q.aide)}</p>` : ''}
      <div class="reponses">${q.reponses.map(r => `<button class="bouton" data-dep='${attrJ(r)}'>${esc(r.texte)}</button>`).join('')}</div></div>`;
  }
  const contact = (G.contacts || [])[0];
  return bandeau('jaune', 'Un problème ?', esc(d.titre), { retour: '#/guide' }) + `<p class="doux">Répondez aux questions, le guide vous mène à la bonne solution.</p>${corps}
    <div class="boutons">${S.dep.n > 1 || S.dep.fin || S.dep.fiche ? `<button class="bouton" data-dep='${attrJ({ recommencer: true })}'>Recommencer</button>` : ''}
    ${contact && /[0-9]/.test(contact.tel) ? `<a class="bouton sombre" href="tel:${esc(String(contact.tel).replace(/[^0-9+]/g, ''))}">Toujours bloqué ? Appeler : ${esc(contact.nom)}</a>` : ''}</div>`;
}
function depannageChoix(r) {
  if (r.recommencer) { S.dep = null; return rendre(); }
  if (r.depannage) { S.dep = null; location.hash = '#/depannage/' + r.depannage; return; }
  if (r.suite) Object.assign(S.dep, { q: r.suite, n: S.dep.n + 1 });
  else if (r.fiche) S.dep.fiche = r.fiche;
  else if (r.fin) S.dep.fin = r.fin;
  rendre();
}

// ------------------------------------------------------------------ démarrage
window.rafraichir = rafraichir;
(async () => {
  S.pile = 1;
  await rafraichir();
  rendre(true);
  setInterval(() => { if (!document.hidden && !S.occupe) rafraichir(); }, 3000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) rafraichir(); });
})();
