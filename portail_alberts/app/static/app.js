/* Portail Les Alberts : interface voyageurs (aucune bibliothèque externe).
   Routage par l'adresse (#/...) : le bouton « retour » du navigateur fonctionne. */
'use strict';

// ------------------------------------------------------------------ état
const S = {
  etat: null, conso: null, meteo: null, guide: null, conv: {},
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
  if (a.confirmer && !confirm(a.confirmer)) return;
  if (bouton) bouton.classList.add('attente');
  try {
    const r = await api('/api/action', a);
    if (!r.ok) toast(r.message || 'La commande n’a pas abouti.', a);
  } catch (e) {
    toast('La maison ne répond pas. Réessayez dans un instant.', a);
  }
  if (bouton) bouton.classList.remove('attente');
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
  if (b) { e.preventDefault(); agir(JSON.parse(b.dataset.a), b); return; }
  const m = e.target.closest('[data-mois]');
  if (m) { e.preventDefault(); S.moisConv = m.dataset.mois; rendre(); return; }
  const dp = e.target.closest('[data-dep]');
  if (dp) { e.preventDefault(); depannageChoix(JSON.parse(dp.dataset.dep)); }
  const f = e.target.closest('[data-fermer]');
  if (f) { e.preventDefault(); dialogueFermeture(); }
});
document.addEventListener('change', e => {
  const c = e.target.closest('[data-coche]');
  if (c) {
    const [k, id] = c.dataset.coche.split('|');
    const v = new Set(local.get(k)); c.checked ? v.add(id) : v.delete(id); local.set(k, [...v]);
    rendre(false); return;
  }
  const g = e.target.closest('[data-lum]');
  if (g) { S.glisse = false; agir(Object.assign(JSON.parse(g.dataset.lum), { luminosite: +g.value })); }
});
document.addEventListener('input', e => {
  if (e.target.closest('[data-lum]')) S.glisse = true;
  if (e.target.id === 'recherche') { S.recherche = e.target.value; rendreListeGuide(); }
});

// ------------------------------------------------------------------ routage
const SECTION = { '': 'bleu', piece: 'bleu', chauffage: 'bleu', convecteur: 'bleu', lumieres: 'bleu',
  meteo: 'violet', arrivee: 'violet', depart: 'violet', sejour: 'violet', guide: 'jaune', depannage: 'jaune' };
const route = () => { const [r = '', a = '', b = ''] = location.hash.replace(/^#\/?/, '').split('/'); return { r, a: decodeURIComponent(a), b }; };
window.addEventListener('hashchange', () => { S.pile++; S.moisConv = null; rendre(true); });

function menu(r) {
  const it = (h, n, l, on) => `<a class="it${on ? ' on' : ''}" href="#/${h}"${on ? ' aria-current="page"' : ''}>${ic(n)}${l}</a>`;
  const actif = { '': 'maison', piece: 'maison', chauffage: 'chauffage', convecteur: 'chauffage', lumieres: 'lumieres', meteo: 'meteo',
    arrivee: 'arrivee', depart: 'depart', sejour: 'meteo', guide: 'guide', depannage: 'guide' }[r];
  $('#menu').innerHTML = `<a class="marque" href="#/">${LOGO}<span><b>Les Alberts</b><small>MONTGENÈVRE</small></span></a>
    <div class="groupe g-bleu"><span>Piloter la maison</span>${it('', 'maison', 'Maison', actif === 'maison')}${it('chauffage', 'chauffage', 'Chauffage', actif === 'chauffage')}${it('lumieres', 'lumieres', 'Lumières', actif === 'lumieres')}</div>
    <div class="groupe g-violet"><span>S’informer</span>${it('meteo', 'meteo', 'Météo', actif === 'meteo')}${it('arrivee', 'arrivee', 'Arrivée', actif === 'arrivee')}${it('depart', 'depart', 'Départ', actif === 'depart')}</div>
    <div class="groupe g-jaune"><span>Guide</span>${it('guide', 'guide', 'Guide', actif === 'guide')}</div>`;
  const tab = { '': 'maison', piece: 'maison', chauffage: 'chauffage', convecteur: 'chauffage', lumieres: 'lumieres',
    meteo: 'sejour', arrivee: 'sejour', depart: 'sejour', sejour: 'sejour', guide: 'guide', depannage: 'guide' }[r];
  const o = (h, n, l, k, cl = '') => `<a class="${cl}${tab === k ? ' on' : ''}" href="#/${h}">${ic(n)}${l}</a>`;
  $('#onglets').innerHTML = o('', 'maison', 'Maison', 'maison') + o('chauffage', 'chauffage', 'Chauffage', 'chauffage') +
    o('lumieres', 'lumieres', 'Lumières', 'lumieres') + o('sejour', 'meteo', 'Séjour', 'sejour', 'sej') + o('guide', 'guide', 'Guide', 'guide', 'gui');
}

const VUES = { '': accueil, piece: vuePiece, chauffage: vueChauffage, convecteur: vueConvecteur, lumieres: vueLumieres,
  meteo: vueMeteo, arrivee: vueArrivee, depart: vueDepart, sejour: vueSejour, guide: vueGuide, depannage: vueDepannage };
const STATIQUES = new Set(['guide', 'depannage', 'meteo']);   // ne dépendent pas de l'état temps réel

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
const etatTexte = a => a.etat === 'on' ? 'etat-on' : (a.etat === 'ko' ? 'etat-ko' : 'etat-off');
function carteAppareil(a) {
  const b = a.bouton ? `<button class="bouton" data-a='${attrJ({ type: 'commande', id: a.id, valeur: a.bouton.valeur, confirmer: a.confirmation || undefined })}'>${esc(a.bouton.libelle)}</button>` : '';
  const ico = a.etat === 'demarrage' ? '<span class="rond encours"></span>' : ic(a.icone || 'ampoule', 26, '#7A4E24');
  return `<div class="appareil">${ico}<div style="flex:1;min-width:0"><div class="nom">${esc(a.nom)}</div><div class="${etatTexte(a)}">${esc(a.texte)}</div></div>${b}</div>`;
}
function cartePortes() {
  const p = S.etat.portes;
  if (!p.length) return '';
  return `<div class="appareil">${ic('porte', 26, '#7A4E24')}<div><div class="nom">Portes d’entrée</div><div class="petit gras">${p.map(d =>
    `<span style="color:${d.ko ? '#8A97A1' : d.ouverte ? 'var(--warn)' : 'var(--ok)'}">${esc(d.nom)} : ${d.ko ? 'inconnue' : d.ouverte ? 'ouverte' : 'fermée'}</span>`).join(' · ')}</div></div></div>`;
}
function carteAlerte(a) {
  let b = '';
  if (a.action) b = `<button class="bouton sombre" data-a='${attrJ(a.action)}'>${esc(a.action.libelle)}</button>`;
  else if (a.lien) b = `<a class="bouton" href="${esc(a.lien)}">${esc(a.bouton || 'Voir')}</a>`;
  return `<div class="alerte ${a.niveau}"><div style="flex:1"><b>${esc(a.titre)}</b><span class="doux">${esc(a.texte)}</span></div>${b}</div>`;
}

// ------------------------------------------------------------------ accueil
function accueil() {
  const E = S.etat, x = E.exterieur;
  const meteo = `${esc(x.lieu)} : ${x.t ? esc(x.t) + ' °C' : '—'}${x.condition ? ', ' + esc(x.condition.toLowerCase()) : ''}<br>${E.veille ? 'Maison en veille' : 'Vigilance ' + esc((x.vigilance || 'verte').toLowerCase())}`;
  let h = `<header class="bandeau grand"><div style="text-align:right"><span class="sur">Montgenèvre · Hautes-Alpes</span>
    <h1>${E.veille ? 'La maison<br>vous attend' : 'Bienvenue<br>aux Alberts'}</h1></div>${FLECHE}<span class="droite" style="text-shadow:0 1px 2px rgba(0,0,0,.25)">${meteo}</span></header>`;
  if (E.veille) {
    h += `<div class="veille">${ic('lune', 40, '#A3376F')}<div style="flex:1;min-width:240px"><b>La maison est en veille</b><span class="doux">Radiateurs en hors-gel, eau chaude arrêtée. Comptez environ 3 heures pour une maison agréable.</span></div>
      <a class="bouton violet" href="#/arrivee">Mettre la maison en route</a></div>`;
  } else if (E.alertes.length) {
    h += `<div class="grille g2">${E.alertes.map(carteAlerte).join('')}</div>`;
  } else {
    h += `<div class="toutvabien">${ic('ok', 30, '#2F6B4F', 2.4)}<div><b>Tout va bien dans la maison</b>Chauffage à température, humidité normale.</div></div>`;
  }
  h += `<div class="grille g3">${E.appareils.map(carteAppareil).join('')}${cartePortes()}</div>`;
  h += `<div class="titre-sec"><h2>Pièces</h2><span class="doux">Chauffage électrique : ${E.chauffage.puissance} W en ce moment</span></div>
    <div class="grille g5">${E.pieces.map(cartePiece).join('')}</div>`;
  if (matchMedia('(max-width:899px)').matches) {
    h += `<div class="grille g2" style="grid-template-columns:1fr 1fr"><a class="hub plein" href="#/arrivee">${ic('arrivee', 30)}<span><b>J’arrive</b>Mise en route</span></a>
      <a class="hub sombre" href="#/depart">${ic('depart', 30)}<span><b>Je pars</b>Fermer la maison</span></a></div>`;
  }
  return h;
}
function cartePiece(p) {
  return `<a class="piece" href="#/piece/${esc(p.id)}"><span class="nom">${esc(p.nom)}</span>
    <span style="display:flex;align-items:baseline;gap:8px"><span class="temp">${p.t ? esc(p.t) + '°' : '–'}</span><span class="doux">${esc(p.h || '')}</span></span>
    <span><span class="chip${p.warn ? ' warn' : ''}">${esc(p.chip)}</span></span>
    <span class="lum ${p.lumiere.etat}">${ic('ampoule', 16, 'currentColor', 2.2)}${esc(p.lumiere.texte)}</span></a>`;
}

// ------------------------------------------------------------------ pièce
const SUR = { convecteur: 'Pièce', poele: 'Pièce · avec poêle', sans_chauffage: 'Pièce · sans chauffage', passage: 'Passage · éclairage automatique' };
function vuePiece(id) {
  const p = S.etat.pieces.find(x => x.id === id);
  if (!p) return bandeau('bleu', 'Pièce', 'Pièce inconnue', { retour: '#/' });
  const droite = p.t ? `<span class="droite"><b>${esc(p.t)} °C</b>${p.h ? esc(p.h) + ' d’humidité' : ''}</span>` : '';
  let h = bandeau('bleu', SUR[p.type] || 'Pièce', esc(p.nom), { retour: '#/', droite });
  const al = S.etat.alertes.filter(a => a.piece === id);
  h += al.map(a => `<div class="important" style="border-left:6px solid var(--warn)"><b>${esc(a.titre)}.</b> ${esc(a.texte)}
    ${a.action ? `<div class="boutons" style="margin-top:8px"><button class="bouton sombre" data-a='${attrJ(a.action)}'>${esc(a.action.libelle)}</button></div>` : ''}</div>`).join('');
  const gauche = [], droiteC = [];
  if (p.convecteur) {
    gauche.push(`<div class="carte"><div class="mesures"><div class="mesure"><b${p.convecteur.diag === 'panne' ? ' style="color:var(--warn)"' : ''}>${esc(p.t || '–')} °C</b><span>Température</span></div>
      <div class="mesure"><b${p.h_num > 70 ? ' style="color:var(--warn)"' : ''}>${esc(p.h || '–')}</b><span>Humidité</span></div>
      <div class="mesure"><b>${esc(p.convecteur.w_txt)}</b><span>${p.convecteur.diag === 'chauffe' ? 'Chauffe en ce moment' : p.convecteur.diag === 'panne' ? 'Convecteur, ne chauffe pas' : 'Convecteur'}</span></div></div></div>`);
    gauche.push(carteChauffage(p));
  } else if (p.poele) {
    gauche.push(cartePoele(p));
  } else if (p.type === 'sans_chauffage') {
    gauche.push(`<div class="carte ligne">${ic('chauffage', 26, '#3A6EA5')}<div><h2 style="margin:0">Pas de chauffage piloté</h2><span class="doux">Rien à régler ici.</span></div></div>`);
  }
  if (p.ventilation) gauche.push(carteVentilation(p));
  droiteC.push(blocLumieres(p));
  if (p.conseils.length) droiteC.push(`<div class="carte"><h2>Bon à savoir</h2><ul style="margin:0;padding-left:20px;line-height:1.6">${p.conseils.map(c => `<li>${esc(c)}</li>`).join('')}</ul></div>`);
  if (!gauche.length) return h + `<div class="grille g2"><div class="col">${droiteC.join('')}</div></div>`;
  return h + `<div class="grille g2" style="align-items:start"><div class="col">${gauche.join('')}</div><div class="col">${droiteC.join('')}</div></div>`;
}
function carteChauffage(p) {
  const c = p.convecteur;
  if (!c.dispo) return `<div class="carte"><h2>Chauffage</h2><p class="etat-ko">Le convecteur ne répond pas. Vérifiez qu’il est sous tension.</p></div>`;
  const pre = S.etat.chauffage.prechauffage;
  return `<div class="carte"><h2>Chauffage <span class="doux petit" style="font-weight:600">· convecteur</span></h2>
    <div class="modes">${c.modes.map(m => `<button class="${m.valeur === c.mode ? 'on' : ''}" aria-pressed="${m.valeur === c.mode}" data-a='${attrJ({ type: 'mode', piece: p.id, valeur: m.valeur })}'>${esc(m.libelle)}</button>`).join('')}</div>
    <div class="explic"><b>${esc(c.mode_libelle)} :</b> ${esc(c.aide)}</div>
    ${pre === null ? '' : `<div class="ligne" style="margin-top:8px;font-size:15px">${ic('horloge', 20, '#3A6EA5')}<span><b>Préchauffage heures creuses : ${pre ? 'activé' : 'désactivé'}.</b> <span class="doux">${pre ? 'La maison chauffe en Confort la nuit, puis revient au mode choisi.' : ''}</span></span></div>`}
    <a href="#/convecteur/${esc(p.id)}" style="display:inline-block;margin-top:8px;padding:6px 0">Détail du convecteur et consommation ›</a></div>`;
}
function cartePoele(p) {
  const on = p.poele.etat === 'on';
  return `<section class="poele"><div class="ligne" style="flex-wrap:wrap">${ic('flamme', 26, '#7A4E24')}<div style="flex:1 1 180px"><h2>Poêle à granulés</h2><div class="sous">Hoben. Chauffage de la pièce</div></div>
    <span class="pil${on ? '' : ' gris'}">${esc(p.poele.texte)}</span></div>
    <div class="info">Le portail voit seulement si la prise du poêle est sous tension. <b>Allumage, arrêt et température se règlent sur la console du poêle.</b></div>
    <div class="grille g2" style="gap:10px"><div class="info"><div class="petit" style="color:var(--poele-doux)">Remplir en granulés</div><b>Tous les 2 jours</b></div>
    <div class="info"><div class="petit" style="color:var(--poele-doux)">Nettoyer, poêle froid</div><b>Tous les 2 jours</b></div></div>
    <div class="important"><b>Important :</b> ne coupez jamais la prise pendant la ventilation d’extinction.</div>
    <div class="boutons"><a class="bouton poele" href="#/guide/nettoyer">Nettoyage pas à pas</a><a class="bouton" href="#/guide/poeles">Utiliser les poêles</a><a class="bouton" href="#/guide/alarme">Le poêle est en alarme</a></div></section>`;
}
function carteVentilation(p) {
  const v = p.ventilation;
  const etat = v.ko ? '<span class="etat-ko">Ne répond pas</span>' : v.on ? `<span class="etat-on">En marche${v.reste ? ', maintenue encore ' + Math.ceil(v.reste / 60) + ' min' : ''}</span>` : '<span style="color:var(--warn);font-weight:700">Arrêtée</span>';
  return `<div class="carte ligne" style="flex-wrap:wrap"><div style="flex:1;min-width:180px"><h2 style="margin:0">Ventilation</h2>${etat}<div class="doux petit">${esc(v.arret_auto)}</div></div>
    <button class="bouton" data-a='${attrJ({ type: 'ventilation', piece: p.id, valeur: 'maintien' })}'>Maintenir ${v.maintien_min} min</button>
    <button class="inter vert" aria-label="Ventilation" aria-pressed="${v.on}" data-a='${attrJ({ type: 'ventilation', piece: p.id, valeur: v.on ? 'off' : 'on' })}'></button></div>`;
}
function blocLumieres(p) {
  if (!p.lampes.length) return `<div class="carte ligne">${ic('ampoule', 22, '#8A97A1')}<div><b>Pas de lumière pilotée</b><div class="doux petit">Utilisez les interrupteurs de la pièce.</div></div></div>`;
  const lignes = p.lampes.map(l => {
    const a = { type: 'lampe', piece: p.id, lampe: l.id };
    if (l.ko) return `<div class="lampe"><div class="nom">${esc(l.nom)}<div class="ko">Ne répond pas : vérifiez l’interrupteur mural.</div></div><button class="bouton" data-a='${attrJ(Object.assign({ valeur: 'on' }, a))}'>Réessayer</button></div>`;
    const glis = l.variable && l.on ? `<label class="doux petit ligne" style="gap:8px">Intensité<input type="range" min="1" max="100" value="${l.luminosite || 100}" data-lum='${attrJ(Object.assign({ valeur: 'on' }, a))}'></label>` : '';
    const minu = l.minuterie_min && !l.on ? `<button class="bouton sombre" data-a='${attrJ(Object.assign({ valeur: 'on', minutes: true }, a))}'>Allumer ${l.minuterie_min} min</button>` : '';
    const reste = l.reste ? `<div class="petit" style="color:#6B5A1E">S’éteint dans ${Math.ceil(l.reste / 60)} min</div>` : '';
    return `<div class="lampe"><div class="nom">${esc(l.nom)}${reste}</div>${glis}${minu}<button class="inter" aria-label="${esc(l.nom)}" aria-pressed="${l.on}" data-a='${attrJ(Object.assign({ valeur: l.on ? 'off' : 'on' }, a))}'></button></div>`;
  }).join('');
  const tout = p.lampes.length > 1 && p.lampes.some(l => l.on) ? `<div style="margin-top:8px"><button class="bouton sombre" data-a='${attrJ({ type: 'lumieres_piece', piece: p.id, valeur: 'off' })}'>Tout éteindre dans la pièce</button></div>` : '';
  return `<div class="eclairage"><div class="ligne" style="gap:8px">${ic('ampoule', 22, '#8A6A00')}<h2>Éclairage</h2></div><div class="sous">${esc(p.lumiere.texte)}</div>${lignes}${tout}</div>`;
}

// ------------------------------------------------------------------ chauffage
async function vueChauffage() {
  const E = S.etat;
  const C = await charger('conso', '/api/conso', 300000);
  const poeles = E.pieces.filter(p => p.poele), convs = E.pieces.filter(p => p.convecteur);
  const kpi = (l, k) => C ? `<div class="kpi"><b>${esc(C[k].kwh)} kWh</b><span>${l} · ≈ ${esc(C[k].eur)} € · ${C[k].nuit_pct} % la nuit</span></div>` : `<div class="kpi"><b>–</b><span>${l}</span></div>`;
  const ETATS = { ok: 'À température', chauffe: 'Chauffe', panne: 'Ne chauffe pas', coupe: 'Hors tension', arret: 'Arrêté', inconnu: '?' };
  const pre = E.chauffage.prechauffage;
  return bandeau('bleu', 'Piloter la maison', 'Chauffage', { droite: `<span class="droite"><b>${E.chauffage.puissance} W</b>en ce moment</span>` }) +
  `<div class="grille" style="grid-template-columns:minmax(0,330px) minmax(0,1fr);align-items:start" id="g-chauffage">
   <section class="poele"><div class="ligne">${ic('flamme', 26, '#7A4E24')}<div><h2>Poêles à granulés</h2><div class="sous">Hoben. État lu sur leurs prises, non pilotables</div></div></div>
    <div class="info">${poeles.map(p => `<div class="ligne" style="justify-content:space-between;padding:4px 0"><a href="#/piece/${esc(p.id)}" style="color:inherit">${esc(p.nom)}</a><span class="pil${p.poele.etat === 'on' ? '' : ' gris'}">${esc(p.poele.texte)}</span></div>`).join('')}</div>
    <div class="petit" style="color:var(--poele-doux)">Remplir et nettoyer tous les deux jours, poêle froid.</div>
    <div class="boutons"><a class="bouton poele" href="#/guide/nettoyer">Nettoyage pas à pas</a><a class="bouton" href="#/guide/poeles">Notice</a></div></section>
   <section class="carte" style="border-top:5px solid var(--radiateur)"><div class="ligne" style="justify-content:space-between;flex-wrap:wrap"><h2 style="color:#234A75;margin:0">Radiateurs électriques</h2>
    <button class="bouton" data-a='${attrJ({ type: 'chauffage_tout', confirmer: 'Passer tous les radiateurs en hors-gel ?' })}'>Tout passer en hors-gel</button></div>
    <div class="grille g3" style="margin:12px 0">${kpi('Aujourd’hui', 'jour')}${kpi('7 derniers jours', 'semaine')}${kpi('Ce mois-ci', 'mois')}</div>
    ${C ? `<p class="doux petit">Estimation : heures creuses ${esc(C.tarifs.hc)} €/kWh (${esc(C.tarifs.plages.join(', '))}), heures pleines ${esc(C.tarifs.hp)} €/kWh.</p>` : ''}
    ${pre === null ? '' : `<p class="ligne petit" style="margin:8px 0">${ic('horloge', 18, '#3A6EA5')}<b>Préchauffage heures creuses : ${pre ? 'activé' : 'désactivé'}</b></p>`}
    <div style="overflow-x:auto"><table class="convs"><thead><tr><th>Pièce</th><th>État</th><th>Mode</th><th>Temp.</th><th>Puissance</th><th>Aujourd’hui</th></tr></thead><tbody>
    ${convs.map(p => `<tr><td><a href="#/convecteur/${esc(p.id)}"><b>${esc(p.nom)}</b> ›</a></td><td><span class="etat e-${p.convecteur.diag}">${ETATS[p.convecteur.diag]}</span></td>
      <td>${esc(p.convecteur.mode_libelle)}</td><td>${esc(p.t || '–')}°</td><td>${esc(p.convecteur.w_txt)}</td><td>${C && C.pieces[p.id] ? esc(C.pieces[p.id]) + ' kWh' : '–'}</td></tr>`).join('')}
    </tbody></table></div></section></div>
    <style>@media (max-width:899px){#g-chauffage{grid-template-columns:minmax(0,1fr)!important}}</style>`;
}

async function vueConvecteur(id) {
  const p = S.etat.pieces.find(x => x.id === id && x.convecteur);
  if (!p) return bandeau('bleu', 'Chauffage', 'Convecteur inconnu', { retour: '#/chauffage' });
  const cle = `${id}:${S.moisConv || ''}`;
  if (!S.conv[cle] || Date.now() - S.conv[cle]._t > 300000) {
    try { S.conv[cle] = await api(`/api/convecteur?id=${encodeURIComponent(id)}${S.moisConv ? '&mois=' + S.moisConv : ''}`); S.conv[cle]._t = Date.now(); } catch (e) { /* hors ligne */ }
  }
  const D = S.conv[cle], c = p.convecteur;
  const sous = c.diag === 'panne' ? `<span style="display:block;font-size:15px;font-weight:700;color:#FFD0B5;margin-top:4px">Ne chauffe pas</span>` : '';
  let h = bandeau('bleu', 'Chauffage', `Convecteur · ${esc(p.nom)}${sous}`, { retour: `#/piece/${esc(id)}` });
  const constantes = [['Pièce', p.nom], ['Modèle', c.modele || 'À renseigner'], ['Mode fil pilote', c.mode_libelle], ['Puissance', c.w_txt], ['Température de la pièce', (p.t || '–') + ' °C']];
  h += `<div class="grille g2" style="align-items:start"><div class="col"><div class="carte"><h2>Constantes</h2>
    ${constantes.map(([l, v]) => `<div class="ligne" style="justify-content:space-between;padding:6px 0;border-top:1px solid var(--trait2)"><span class="doux">${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>
    ${carteChauffage(p).replace(/<a href="#\/convecteur[^>]*>.*?<\/a>/, '')}
    <div class="encadre-bleu"><b>Sélecteur du convecteur :</b> il doit être sur la position pilotée (souvent « Auto » ou « Prog », selon le modèle), sinon le portail ne commande rien. Si quelqu’un l’a forcé, remettez-le en position pilotée, surtout avant de partir.</div></div>
    <div class="col">${D ? courbe(D.courbe, c.w) + calendrier(D.mois) : '<div class="carte doux">Historique indisponible pour le moment.</div>'}</div></div>`;
  return h;
}
function courbe(v, maintenant) {
  if (!v || !v.length) return '<div class="carte doux">Pas d’historique de puissance.</div>';
  const W = 600, H = 120, mx = Math.max(100, ...v);
  const pts = v.map((y, i) => `${(i * W / (v.length - 1)).toFixed(1)},${(H - 6 - y * (H - 12) / mx).toFixed(1)}`).join(' ');
  return `<div class="carte"><div class="ligne" style="justify-content:space-between"><h2 style="margin:0">Puissance sur 24 h</h2><span><b style="font-size:26px">${Math.round(maintenant || 0)} W</b> <span class="doux">maintenant</span></span></div>
    <svg class="courbe" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Puissance du convecteur sur 24 heures"><polyline points="${pts}" fill="none" stroke="#C8691C" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>
    <div class="ligne doux petit" style="justify-content:space-between"><span>il y a 24 h</span><span>maintenant</span></div></div>`;
}
function calendrier(m) {
  const cases = [];
  for (let i = 0; i < m.premier_jour; i++) cases.push('<span></span>');
  m.jours.forEach((v, i) => {
    const a = v && m.max ? Math.min(1, v / m.max) : 0;
    cases.push(`<span class="j" style="background:${v == null ? 'var(--fond)' : `rgba(58,110,165,${(0.12 + a * 0.6).toFixed(2)})`};color:${a > .6 ? '#fff' : 'inherit'}"><b>${i + 1}</b>${v == null ? '' : String(v).replace('.', ',')}</span>`);
  });
  return `<div class="carte"><div class="ligne" style="justify-content:space-between"><button class="bouton" data-mois="${esc(m.precedent)}" aria-label="Mois précédent">‹</button>
    <div style="text-align:center"><b>${esc(m.titre)}</b><div class="doux petit">${esc(m.total)} kWh sur le mois</div></div>
    ${m.suivant ? `<button class="bouton" data-mois="${esc(m.suivant)}" aria-label="Mois suivant">›</button>` : '<span style="width:44px"></span>'}</div>
    <div class="calendrier" style="margin-top:10px">${['L', 'M', 'M', 'J', 'V', 'S', 'D'].map(j => `<span class="doux gras">${j}</span>`).join('')}${cases.join('')}</div>
    <p class="doux petit" style="margin-top:8px">kWh consommés par jour.</p></div>`;
}

// ------------------------------------------------------------------ lumières
function vueLumieres() {
  const E = S.etat, avec = E.pieces.filter(p => p.lampes.length);
  const n = avec.filter(p => p.lumiere.etat === 'on').length;
  return bandeau('bleu', 'Piloter la maison', 'Lumières', {
    droite: `<span class="droite"><span class="pilule-b">${n ? `Allumées dans ${n} pièce${n > 1 ? 's' : ''}` : 'Tout est éteint'}</span></span>` }) +
    (n ? `<div><button class="bouton sombre" data-a='${attrJ({ type: 'lumieres_maison', valeur: 'off' })}'>Tout éteindre dans la maison</button></div>` : '') +
    `<div class="grille g3">${avec.map(p => {
      const on = p.lumiere.etat === 'on';
      return `<div class="carte" style="${on ? 'background:var(--lum-tint);box-shadow:inset 0 4px 0 var(--lum)' : ''}"><div class="ligne"><a href="#/piece/${esc(p.id)}" style="flex:1;color:inherit;text-decoration:none"><b style="font-size:17px">${esc(p.nom)} ›</b><div class="petit" style="color:${on ? 'var(--lum-ink)' : 'var(--doux)'}">${esc(p.lumiere.texte)}</div></a>
        <button class="inter" aria-label="${esc(p.nom)}" aria-pressed="${on}" data-a='${attrJ({ type: 'lumieres_piece', piece: p.id, valeur: on ? 'off' : 'on' })}'></button></div>
        ${p.lampes.length > 1 || p.lampes.some(l => l.ko) ? `<div class="boutons" style="margin-top:10px">${p.lampes.map(l => l.ko
          ? `<span class="chip" style="background:var(--warn-tint);color:var(--warn)">${esc(l.nom)} : ne répond pas</span>`
          : `<button class="chip" style="border:0;min-height:36px;${l.on ? 'background:#FFF3C4;color:var(--lum-ink)' : ''}" data-a='${attrJ({ type: 'lampe', piece: p.id, lampe: l.id, valeur: l.on ? 'off' : 'on' })}'>${esc(l.nom)}</button>`).join('')}</div>` : ''}</div>`;
    }).join('')}</div>`;
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

// ------------------------------------------------------------------ séjour (téléphone)
function vueSejour() {
  return bandeau('violet', 'S’informer', 'Votre séjour') +
    `<a class="hub violet" href="#/meteo">${ic('meteo', 40, '#A3376F')}<span style="flex:1"><b>Météo</b><span class="doux">${esc(S.etat.exterieur.condition || '')} ${S.etat.exterieur.t ? esc(S.etat.exterieur.t) + ' °C' : ''}</span></span>›</a>
     <a class="hub jaune" href="#/guide">${ic('guide', 40, '#8A6A00')}<span style="flex:1"><b>Guide de la maison</b><span class="doux">Poêles, électricité, dépannage, contacts</span></span>›</a>
     <a class="hub plein" href="#/arrivee">${ic('arrivee', 36)}<span style="flex:1"><b>J’arrive</b>Mettre la maison en route</span>›</a>
     <a class="hub sombre" href="#/depart">${ic('depart', 36)}<span style="flex:1"><b>Je pars</b>Fermer la maison</span>›</a>`;
}

// ------------------------------------------------------------------ arrivée
async function vueArrivee() {
  const A = S.etat.arrivee, G = S.guide || await chargerGuide();
  const coches = new Set(local.get('arrivee'));
  const reste = A.mise_en_route.some(x => x.etat === 'attente' || x.etat === 'echec');
  const contacts = (G && G.contacts) || [];
  return bandeau('violet', 'Arriver', 'Bienvenue aux Alberts', { retour: matchMedia('(max-width:899px)').matches ? '#/sejour' : null }) +
  `<div class="grille" style="grid-template-columns:minmax(0,1fr) minmax(0,360px);align-items:start" id="g-arr"><div class="col">
    <div class="carte"><div class="ligne" style="flex-wrap:wrap;align-items:flex-start"><div style="flex:1;min-width:220px"><h2 style="margin:0">Mettre la maison en route</h2><p class="doux">La maison a pu être préparée à distance. Ce bouton termine ce qui reste.</p></div>
      ${reste ? `<button class="bouton violet" data-a='${attrJ({ type: 'mise_en_route' })}'>Terminer la mise en route</button>` : '<span class="pil">Tout est en route</span>'}</div>
      <div class="boutons" style="margin-top:10px">${A.mise_en_route.map(x => `<span class="ligne" style="gap:8px;background:var(--fond);border-radius:8px;padding:8px 12px">${x.etat === 'ok' ? '<span class="rond ok">✓</span>' : `<span class="rond ${x.etat}">${x.etat === 'echec' ? '!' : ''}</span>`}<span><b>${esc(x.t)}</b><br><span class="doux petit">${esc(x.x)}</span></span></span>`).join('')}</div></div>
    <h2 style="font-size:20px">À faire en arrivant</h2><div class="carte">${A.etapes.map((e, i) => `<div class="coche"><input type="checkbox" id="ar${i}" data-coche="arrivee|${i}" ${coches.has(String(i)) ? 'checked' : ''}><label for="ar${i}"><b>${esc(e.t)}</b><br><span class="doux">${esc(e.x || '')}</span></label>${e.lien ? `<a class="bouton" href="${esc(e.lien)}">${esc(e.bouton || 'Ouvrir')}</a>` : ''}</div>`).join('')}</div></div>
    <div class="col"><div class="carte"><h2>Pas de WiFi en arrivant ?</h2><p class="doux">Ce portail passe par le WiFi de la maison. S’il est éteint, appelez le propriétaire : il le rallume à distance.</p></div>
    ${contacts.length ? `<div class="carte"><h2>En cas de besoin</h2>${contacts.map(c => { const n = String(c.tel).replace(/[^0-9+]/g, ''); return `<div class="ligne" style="justify-content:space-between;padding:8px 0;border-top:1px solid var(--trait2)"><span>${esc(c.nom)}</span>${n ? `<a href="tel:${esc(n)}">${esc(c.tel)}</a>` : '<span class="doux">à renseigner</span>'}</div>`; }).join('')}</div>` : ''}</div></div>
    <style>@media (max-width:899px){#g-arr{grid-template-columns:minmax(0,1fr)!important}}</style>`;
}

// ------------------------------------------------------------------ départ
const COUL = { poele: ['var(--poele-tint)', 'var(--poele)', 'var(--poele-ink)'], radiateur: ['var(--radiateur-tint)', 'var(--radiateur)', '#234A75'],
  lumiere: ['#FFF9E3', '#8A6A00', 'var(--lum-ink)'], maison: ['#EEF1F3', '#56656F', 'var(--encre)'] };
function vueDepart() {
  const D = S.etat.depart, F = S.etat.fermeture;
  if (F.phase === 'compte' || F.phase === 'coupure') return ecranCompte(F);
  const coches = new Set(local.get('depart'));
  const groupes = {};
  D.gestes.forEach(g => { groupes[g.couleur] = { titre: g.groupe, items: [] }; });
  const titres = { radiateur: 'Radiateurs électriques', lumiere: 'Eau chaude et lumières', maison: 'Maison', poele: 'Poêles à granulés' };
  D.auto.forEach(a => { (groupes[a.groupe] = groupes[a.groupe] || { titre: titres[a.groupe], items: [] }).items.push({ auto: a }); });
  D.gestes.forEach(g => g.gestes.forEach((x, i) => groupes[g.couleur].items.push({ geste: x, cle: `${g.couleur}${i}` })));
  const total = Object.values(groupes).reduce((n, g) => n + g.items.length, 0);
  const faits = Object.values(groupes).reduce((n, g) => n + g.items.filter(x => x.auto ? x.auto.ok : coches.has(x.cle)).length, 0);
  const ordre = ['poele', 'radiateur', 'lumiere', 'maison'].filter(k => groupes[k]);
  const bloc = k => { const [f, b, t] = COUL[k] || COUL.maison, g = groupes[k];
    return `<section class="bloc-dep" style="background:${f};border-color:${b}"><h2 style="font-size:19px;color:${t};margin-bottom:4px">${esc(g.titre)}</h2>${g.items.map(x => x.auto
      ? `<div class="coche"><span class="etat-auto ${x.auto.ok ? 'ok' : 'ko'}">${x.auto.ok ? '✓' : '!'}</span><div style="flex:1"><b>${esc(x.auto.t)}</b><br><span class="doux petit">${esc(x.auto.x)}</span></div>${x.auto.action ? `<button class="bouton sombre" data-a='${attrJ(x.auto.action)}'>${esc(x.auto.action.libelle)}</button>` : ''}</div>`
      : `<div class="coche"><input type="checkbox" id="d${x.cle}" data-coche="depart|${x.cle}" ${coches.has(x.cle) ? 'checked' : ''}><label for="d${x.cle}"><b>${esc(x.geste.t)}</b>${x.geste.x ? `<br><span class="doux petit">${esc(x.geste.x)}</span>` : ''}</label></div>`).join('')}</section>`; };
  return bandeau('violet', 'Partir', 'Avant de partir', { retour: matchMedia('(max-width:899px)').matches ? '#/sejour' : null,
    droite: `<span class="droite">${faits} sur ${total} faits<br><span style="opacity:.85;font-weight:600">Ne coupez ni l’électricité ni l’eau.</span></span>` }) +
    `<div class="ligne"><span class="progres"><span style="width:${Math.round(100 * faits / total)}%"></span></span></div>
    <div class="grille g2" style="align-items:start"><div class="col">${ordre.slice(0, 2).map(bloc).join('')}</div><div class="col">${ordre.slice(2).map(bloc).join('')}
    <div class="carte" style="border-top:5px solid var(--encre)"><h2>Fermer la maison</h2><p class="doux" style="margin-bottom:10px">Dernière étape, juste avant de sortir. Une confirmation vous sera demandée, puis vous aurez ${Math.round(D.delai_s / 60)} minutes pour annuler.</p>
    <button class="bouton sombre large" data-fermer>Fermer la maison…</button></div></div></div>`;
}
function dialogueFermeture() {
  const D = S.etat.depart, coches = new Set(local.get('depart'));
  const manquants = [];
  D.gestes.forEach(g => g.gestes.forEach((x, i) => { if (!coches.has(`${g.couleur}${i}`)) manquants.push(x.t.toLowerCase()); }));
  const min = Math.round(D.delai_s / 60);
  const c = $('#calque');
  c.innerHTML = `<div class="dialogue" role="dialog" aria-modal="true" aria-labelledby="t-ferm"><div class="boite">
    <span class="doux petit gras">Étape 1 sur 2</span><h2 id="t-ferm" style="font-size:26px">Fermer la maison ?</h2>
    ${manquants.length ? `<div class="important"><b>${manquants.length} point${manquants.length > 1 ? 's ne sont' : ' n’est'} pas coché${manquants.length > 1 ? 's' : ''} :</b> ${esc(manquants.slice(0, 6).join(', '))}${manquants.length > 6 ? '…' : ''}</div>` : ''}
    <div><b>La maison va :</b><ul style="margin:6px 0 0;padding-left:20px;line-height:1.6"><li>passer les radiateurs en hors-gel, arrêter l’eau chaude et éteindre les lumières, tout de suite ;</li>
    <li>couper le boîtier de l’eau chaude et le WiFi dans ${min} minutes ;</li><li>laisser la console des poêles alimentée.</li></ul></div>
    <div class="encadre-bleu" style="border-color:var(--warn);background:var(--warn-tint);color:var(--warn-ink)">Une fois le WiFi coupé, ce portail ne sera plus accessible. Pour rallumer, il faudra appeler le propriétaire.</div>
    <label class="coche" style="border:0;font-weight:700"><input type="checkbox" id="pars"> Je pars maintenant, tout le monde est prêt</label>
    <div class="boutons" style="justify-content:flex-end"><button class="bouton" id="annuler" style="border-width:2px;border-color:var(--encre)">Annuler</button><button class="bouton violet" id="ferme" disabled>Fermer la maison</button></div>
    <p class="doux petit" style="text-align:right">Le bouton s’active une fois la case cochée.</p></div></div>`;
  const fermer = () => { c.innerHTML = ''; };
  c.querySelector('#annuler').onclick = fermer;
  c.querySelector('.dialogue').onclick = e => { if (e.target.classList.contains('dialogue')) fermer(); };
  c.querySelector('#pars').onchange = e => { c.querySelector('#ferme').disabled = !e.target.checked; };
  c.querySelector('#ferme').onclick = async () => {
    if (!c.querySelector('#pars').checked) return;
    fermer();
    await agir({ type: 'fermeture', valeur: 'demarrer', confirme: true });
    location.hash = '#/depart';
  };
  c.querySelector('#annuler').focus();
}
function ecranCompte(F) {
  const r = F.reste || 0, mm = Math.floor(r / 60), ss = String(r % 60).padStart(2, '0');
  return bandeau('violet', 'Partir', 'Fermeture en cours') + `<div class="carte" style="max-width:560px;margin:0 auto;text-align:center">
    <span class="doux petit gras">Étape 2 sur 2</span><div class="compte" role="timer" aria-live="polite">${F.phase === 'coupure' ? '…' : `${mm}:${ss}`}</div>
    <p><b>Radiateurs, eau chaude et lumières : arrêtés.</b></p><p class="doux" style="margin-bottom:14px">${F.phase === 'coupure' ? 'Coupure du WiFi en cours. Bon retour !' : `Boîtier de l’eau chaude et WiFi : coupés dans ${mm} min ${ss}.`}</p>
    ${F.phase === 'compte' ? `<button class="bouton violet large" data-a='${attrJ({ type: 'fermeture', valeur: 'annuler' })}'>Annuler la fermeture</button><p class="doux petit" style="margin-top:8px">Annuler rallume l’eau chaude et garde le WiFi.</p>` : ''}</div>`;
}

// ------------------------------------------------------------------ guide
function toutesFiches(G) { return (G?.themes || []).flatMap(t => (t.fiches || []).map(f => Object.assign({ theme: t.titre, couleur: t.couleur }, f))); }
async function vueGuide(id) {
  const G = await chargerGuide();
  if (!G) return bandeau('jaune', 'Guide', 'Guide de la maison') + '<div class="carte doux">Guide indisponible.</div>';
  const tel = matchMedia('(max-width:899px)').matches;
  const fiches = toutesFiches(G);
  const f = fiches.find(x => x.id === id) || (!tel ? fiches[0] : null);
  let h = bandeau('jaune', f && tel ? f.theme : 'Guide', f && tel ? esc(f.titre) : esc(G.titre || 'Guide de la maison'), { retour: f && tel ? '#/guide' : (tel ? '#/sejour' : null) });
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
  setInterval(() => { if (!document.hidden) rafraichir(); }, 5000);
  setInterval(() => {                                   // compte à rebours de fermeture affiché à la seconde
    const F = S.etat?.fermeture;
    if (F && F.phase === 'compte' && F.reste > 0 && route().r === 'depart') { F.reste--; rendre(false); }
  }, 1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) rafraichir(); });
})();
