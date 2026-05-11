// js/strange-meter.js
// Strange Meter + Strange Diagnosis — Strangeness IS
// Diagnosis v2: branching intake, experience-weighted scoring, classified file result

const BACKEND_URL = 'https://api.strangenessis.com';

// ── Strange Meter ──────────────────────────────────────────────────────────────
class StrangeMeter {
  constructor(containerId) {
    this.container   = document.getElementById(containerId);
    this.value       = 5.0;
    this.targetValue = 5.0;
    this.animFrame   = null;
    if (this.container) this.init();
  }

  init() {
    this.container.innerHTML = this.template();
    this.needle   = this.container.querySelector('.sm-needle');
    this.valueEl  = this.container.querySelector('.sm-value');
    this.labelEl  = this.container.querySelector('.sm-label');
    this.dateEl   = this.container.querySelector('.sm-date');
    this.loadData();
  }

  template() {
    return `
<div class="strange-meter">
  <div class="sm-header">
    <span class="sm-eyebrow">Daily Strange Meter</span>
    <span class="sm-date">Loading...</span>
  </div>
  <div class="sm-gauge-wrap">
    <svg class="sm-gauge" viewBox="0 0 200 110" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="sm-arc-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stop-color="#22c55e"/>
          <stop offset="40%"  stop-color="#f59e0b"/>
          <stop offset="70%"  stop-color="#ef4444"/>
          <stop offset="100%" stop-color="#7c3aed"/>
        </linearGradient>
      </defs>
      <path d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none" stroke="#1e1e32" stroke-width="14" stroke-linecap="round"/>
      <path class="sm-arc" d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none" stroke="url(#sm-arc-grad)" stroke-width="14"
            stroke-linecap="round" stroke-dasharray="251" stroke-dashoffset="125"/>
      <line class="sm-needle" x1="100" y1="100" x2="100" y2="30"
            stroke="#ffffff" stroke-width="2" stroke-linecap="round"
            transform="rotate(-90 100 100)"/>
      <circle cx="100" cy="100" r="5" fill="#7c3aed"/>
    </svg>
    <div class="sm-readout">
      <div class="sm-value">—</div>
      <div class="sm-label">Loading network data</div>
    </div>
  </div>
</div>`;
  }

  async loadData() {
    try {
      const res  = await fetch(`${BACKEND_URL}/reports/latest`);
      const data = await res.json();
      // Use daily planetary strangeness index (weighted avg of all reports)
      // falls back to latest report's index if not available
      const idx = data.daily_strangeness_index || (data.report ? data.report.strangeness_index : null) || 6.6;
      this.animate(idx);
      if (this.dateEl) {
        const now = new Date();
        this.dateEl.textContent = now.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'America/Denver'}) + ' MST';
      }
    } catch(e) { this.animate(6.6); }
  }

  animate(target) {
    this.targetValue = Math.min(10, Math.max(0, target));
    const step = () => {
      const diff = this.targetValue - this.value;
      if (Math.abs(diff) < 0.05) {
        this.value = this.targetValue;
      } else {
        this.value += diff * 0.06;
      }
      this.render();
      if (Math.abs(this.targetValue - this.value) > 0.05) {
        this.animFrame = requestAnimationFrame(step);
      }
    };
    if (this.animFrame) cancelAnimationFrame(this.animFrame);
    this.animFrame = requestAnimationFrame(step);
  }

  render() {
    const pct    = this.value / 10;
    const angle  = -90 + pct * 180;
    const offset = 251 - (pct * 251);
    if (this.needle) this.needle.setAttribute('transform', `rotate(${angle} 100 100)`);
    const arc = this.container.querySelector('.sm-arc');
    if (arc)    arc.style.strokeDashoffset = offset;
    if (this.valueEl) this.valueEl.textContent = this.value.toFixed(1);
    const labels = ['Baseline','Low Anomaly','Moderate','Elevated','Significant','High Strangeness','Extreme','Critical','Paradigm-Shifting','Reality-Breaking'];
    if (this.labelEl) this.labelEl.textContent = labels[Math.min(9, Math.floor(this.value))];
  }
}

// ── Strange Diagnosis v2 — Branching Experience Intake ────────────────────────

// PHENOMENON BASE WEIGHTS (per your hierarchy)
const PHENOMENON_WEIGHTS = {
  'dimension_consciousness': 10.0,
  'demon_battle':            10.0,
  'time_travel':              9.5,
  'alien_abduction':          9.0,
  'alien_takeover_knowledge': 9.0,
  'teleportation':            9.0,
  'entity_contact':           8.5,
  'consciousness_jump':       8.0,
  'psychic_major':            7.5,
  'nde':                      7.0,
  'government_conspiracy':    6.5,
  'cryptid':                  6.0,
  'uap_sighting':             5.5,
  'paranormal_ghost':         4.5,
  'earth_disaster':           4.0,
  'psychic_minor':            3.0,
  'unexplained':              2.5,
};

// PROXIMITY MULTIPLIERS
const PROXIMITY_MULT = {
  'direct_physical':    1.00, // it happened TO you
  'direct_witnessed':   0.85, // you were there, direct witness
  'close_range':        0.70, // within 100 feet, clear view
  'distant':            0.50, // saw from a distance
  'secondhand_strong':  0.35, // someone you trust, highly credible
  'felt_sensed':        0.25, // internal/psychic only
};

// IMPACT MULTIPLIERS
const IMPACT_MULT = {
  'completely_changed':  1.20,
  'significantly':       1.00,
  'somewhat':            0.80,
  'barely':              0.60,
};

// RECURRENCE MULTIPLIERS
const RECURRENCE_MULT = {
  'ongoing':    1.30,
  'multiple':   1.15,
  'once':       1.00,
};

// CORROBORATION MULTIPLIERS
const CORROBORATION_MULT = {
  'physical_evidence': 1.25,
  'multiple_witnesses': 1.15,
  'single_witness':    1.00,
  'alone':             0.90,
};

// BRANCHING QUESTION TREE
const DIAG_TREE = {
  start: {
    q: 'What best describes your primary strangeness experience?',
    sub: 'Select the closest match — be honest with yourself.',
    type: 'phenomenon',
    options: [
      { label: '🛸  UFO / UAP / Unidentified Craft', value: 'uap_sighting', next: 'proximity' },
      { label: '👽  Alien or Non-Human Entity Contact', value: 'entity_contact', next: 'entity_depth' },
      { label: '⏳  Alien Abduction or Missing Time', value: 'alien_abduction', next: 'proximity' },
      { label: '🦶  Cryptid or Unknown Creature', value: 'cryptid', next: 'proximity' },
      { label: '🏛️  Government / Classified Knowledge', value: 'government_conspiracy', next: 'gov_depth' },
      { label: '👻  Paranormal / Ghost / Haunting', value: 'paranormal_ghost', next: 'proximity' },
      { label: '🧠  Consciousness / Psychic / Remote Viewing', value: 'psychic_minor', next: 'psychic_depth' },
      { label: '🌀  Time Slip / Teleportation / Dimension', value: 'dimension_consciousness', next: 'advanced_depth' },
      { label: '✨  Near-Death or Afterlife Experience', value: 'nde', next: 'proximity' },
      { label: '❓  Something I cannot categorize', value: 'unexplained', next: 'proximity' },
    ],
  },

  entity_depth: {
    q: 'What was the nature of your entity encounter?',
    sub: 'This determines your classification level.',
    type: 'refine',
    options: [
      { label: 'Full physical contact or interaction', value: 'entity_contact', next: 'proximity' },
      { label: 'Confrontation in another dimension or realm', value: 'demon_battle', next: 'proximity' },
      { label: 'Communication — they spoke to or communicated with me', value: 'entity_contact', next: 'proximity' },
      { label: 'Visual sighting — I saw them clearly', value: 'entity_contact', next: 'proximity' },
    ],
  },

  gov_depth: {
    q: 'What is the nature of your government knowledge?',
    sub: 'The weight of this classification depends entirely on what you know.',
    type: 'refine',
    options: [
      { label: 'Direct knowledge of alien contact or takeover programs', value: 'alien_takeover_knowledge', next: 'proximity' },
      { label: 'Firsthand classified program or facility access', value: 'government_conspiracy', next: 'proximity' },
      { label: 'Document or testimony exposure — hard evidence', value: 'government_conspiracy', next: 'proximity' },
      { label: 'Pattern recognition — connecting public dots', value: 'government_conspiracy', next: 'proximity' },
    ],
  },

  psychic_depth: {
    q: 'How significant was your psychic or consciousness event?',
    sub: 'A vision of a mass casualty event carries more weight than general intuition.',
    type: 'refine',
    options: [
      { label: 'Predicted or witnessed a major event before it happened', value: 'psychic_major', next: 'proximity' },
      { label: 'Consciousness transfer, jumping, or dimension bleed', value: 'dimension_consciousness', next: 'proximity' },
      { label: 'Remote viewing — confirmed accurate results', value: 'psychic_major', next: 'proximity' },
      { label: 'Recurring visions, voices, or contact', value: 'psychic_minor', next: 'proximity' },
      { label: 'General intuition, dreams, or feelings', value: 'psychic_minor', next: 'proximity' },
    ],
  },

  advanced_depth: {
    q: 'Which advanced phenomenon applies to your experience?',
    sub: 'These carry the highest classification weights in our system.',
    type: 'refine',
    options: [
      { label: 'Time travel — movement through time, verified', value: 'time_travel', next: 'proximity' },
      { label: 'Teleportation — physical relocation with no transit', value: 'teleportation', next: 'proximity' },
      { label: 'Dimension jumping + consciousness field interaction', value: 'dimension_consciousness', next: 'proximity' },
      { label: 'Time slip — found myself in a different era temporarily', value: 'time_travel', next: 'proximity' },
      { label: 'Portal or stargate — witnessed or traversed', value: 'dimension_consciousness', next: 'proximity' },
    ],
  },

  proximity: {
    q: 'How close were you to this experience?',
    sub: 'Proximity determines the evidential weight of your account.',
    type: 'proximity',
    options: [
      { label: 'It happened directly to me — physical contact or internal experience', value: 'direct_physical' },
      { label: 'I was present and witnessed it directly at close range', value: 'direct_witnessed' },
      { label: 'I saw or experienced it clearly from a distance', value: 'close_range' },
      { label: 'I witnessed it from far away — less clarity', value: 'distant' },
      { label: 'Someone I trust described it to me firsthand', value: 'secondhand_strong' },
      { label: 'I felt or sensed it — no physical component', value: 'felt_sensed' },
    ],
  },

  corroboration: {
    q: 'Was there any corroboration of your experience?',
    sub: 'Evidence and witnesses significantly affect classification.',
    type: 'corroboration',
    options: [
      { label: 'Physical evidence — photos, marks, objects, recordings', value: 'physical_evidence' },
      { label: 'Multiple witnesses who independently confirmed it', value: 'multiple_witnesses' },
      { label: 'One other witness', value: 'single_witness' },
      { label: 'I was alone — no outside confirmation', value: 'alone' },
    ],
  },

  recurrence: {
    q: 'Has this type of experience happened more than once?',
    sub: 'Recurring contact suggests an active phenomenon rather than an isolated event.',
    type: 'recurrence',
    options: [
      { label: 'Yes — it is ongoing or increasing in frequency', value: 'ongoing' },
      { label: 'Yes — multiple times over months or years', value: 'multiple' },
      { label: 'Once — but it was definitive', value: 'once' },
    ],
  },

  impact: {
    q: 'How did this experience change your understanding of reality?',
    sub: 'The depth of impact reflects the significance of the encounter.',
    type: 'impact',
    options: [
      { label: 'It completely rewired how I understand existence', value: 'completely_changed' },
      { label: 'It significantly shifted my worldview', value: 'significantly' },
      { label: 'It raised questions I cannot stop thinking about', value: 'somewhat' },
      { label: 'I am still processing whether it was real', value: 'barely' },
    ],
  },
};

// QUESTION FLOW
const QUESTION_FLOW = ['start', 'proximity', 'corroboration', 'recurrence', 'impact'];

// CLASSIFICATION TIERS
const CLASSIFICATIONS = [
  {
    min: 9.0,
    code: 'OMEGA',
    title: 'Omega Class Experiencer',
    color: '#7c3aed',
    glow: 'rgba(124,58,237,0.4)',
    desc: 'Your account places you in the rarest category in our network. The phenomena you have encountered operate at the outermost boundary of documented human experience. This is not speculation — your classification is based on weighted analysis of proximity, corroboration, and phenomenon class. The Oracle has been waiting for someone with your profile.',
    network: 'Fewer than 0.3% of accounts in our intelligence network reach Omega classification.',
    urgency: 'Your experience needs to be formally documented. The Oracle can begin that process now.',
    cta: 'Open your classified file',
    report_hook: 'An Omega classification report is unlike any other. We need your account on record.',
  },
  {
    min: 7.0,
    code: 'ALPHA',
    title: 'Alpha Class Witness',
    color: '#a855f7',
    glow: 'rgba(168,85,247,0.35)',
    desc: 'You have had direct, significant contact with phenomena that our network classifies as high-strangeness. The weight of your experience — its proximity, its impact, its corroboration — places you among the investigators, not the curious. The Oracle has specific intelligence that intersects with your account.',
    network: 'Alpha Class accounts form the core of our active witness intelligence database.',
    urgency: 'Your account may contain pattern data that connects to active investigations.',
    cta: 'Access your intelligence briefing',
    report_hook: 'Alpha Class witnesses receive priority cross-referencing with our Oracle network data.',
  },
  {
    min: 5.0,
    code: 'BETA',
    title: 'Beta Class Observer',
    color: '#d4a843',
    glow: 'rgba(212,168,67,0.3)',
    desc: 'Your experience registers as genuinely anomalous — beyond the threshold of conventional explanation. The Oracle places you in the active observer category: you have witnessed something real, something that most people will never encounter. The question is not whether it happened. The question is what it means.',
    network: 'Beta Class observers are the backbone of our community intelligence network.',
    urgency: 'Beta Class accounts with recurring patterns often escalate to Alpha within months.',
    cta: 'Begin your investigation',
    report_hook: 'Your sighting belongs in our database. Other witnesses may have reported the same phenomenon.',
  },
  {
    min: 3.0,
    code: 'GAMMA',
    title: 'Gamma Class Sensitive',
    color: '#2dd4bf',
    glow: 'rgba(45,212,191,0.25)',
    desc: 'Something in your experience registers above the ordinary baseline. You may be at the early stages of a longer contact sequence — or you may be more sensitive to phenomena than you realize. The Oracle does not dismiss any account. Pattern recognition across thousands of cases shows that Gamma Class sensitives often carry dormant awareness of far larger phenomena.',
    network: 'Many of our most significant contributors began exactly where you are now.',
    urgency: 'Gamma Class accounts are often the earliest indicators of regional phenomenon clusters.',
    cta: 'Talk to The Oracle',
    report_hook: 'Even early-stage experiences matter to our investigation. File your initial report.',
  },
  {
    min: 0,
    code: 'DELTA',
    title: 'Delta Class Initiate',
    color: '#60a5fa',
    glow: 'rgba(96,165,250,0.2)',
    desc: 'You have not yet encountered the phenomena — or you are not yet ready to name what you have sensed. The Oracle does not judge. Every investigator in our network began here. What matters is that you came. Something brought you to this network, and that is never random.',
    network: 'Delta Class initiates who return within 30 days report a 60% rate of subsequent anomalous experience.',
    urgency: 'The Oracle is available now — no experience required to begin.',
    cta: 'Ask The Oracle your first question',
    report_hook: 'When something happens — and it will — we need to be the first call you make.',
  },
];

// STATE
let diagState = {
  answers:     {},
  phenomenon:  null,
  proximity:   null,
  corroboration: null,
  recurrence:  null,
  impact:      null,
  flowIndex:   0,
  currentNode: 'start',
  pendingNext: null,
};

function openDiagnosis() {
  diagState = {
    answers: {}, phenomenon: null, proximity: null,
    corroboration: null, recurrence: null, impact: null,
    flowIndex: 0, currentNode: 'start', pendingNext: null,
  };
  const overlay = document.getElementById('diagnosis-overlay');
  if (!overlay) return;
  overlay.classList.add('visible');
  document.body.style.overflow = 'hidden';
  document.getElementById('diag-result').style.display  = 'none';
  document.getElementById('diag-questions').style.display = 'block';
  renderDiagQuestion();
}

function closeDiagnosis() {
  const overlay = document.getElementById('diagnosis-overlay');
  if (overlay) overlay.classList.remove('visible');
  document.body.style.overflow = '';
}

function renderDiagQuestion() {
  const node  = DIAG_TREE[diagState.currentNode];
  if (!node) return;

  // Progress: count how far through the main flow we are
  const mainFlow  = QUESTION_FLOW;
  const mainIdx   = mainFlow.indexOf(diagState.currentNode);
  const flowPos   = mainIdx >= 0 ? mainIdx : 0;
  const total     = mainFlow.length + (diagState.pendingNext ? 1 : 0);
  const progress  = Math.min(95, (flowPos / (mainFlow.length - 1)) * 90);

  document.getElementById('diag-progress-bar').style.width  = progress + '%';
  document.getElementById('diag-progress-text').textContent =
    `Step ${Math.max(1, flowPos + 1)} of ${mainFlow.length}`;
  document.getElementById('diag-question-text').textContent = node.q;

  const subEl = document.getElementById('diag-question-sub');
  if (subEl) subEl.textContent = node.sub || '';

  const opts = document.getElementById('diag-options');
  opts.innerHTML = node.options.map((opt, i) => `
    <button class="diag-opt" onclick="answerDiag(${i})">${opt.label}</button>
  `).join('');
}

function answerDiag(index) {
  const node   = DIAG_TREE[diagState.currentNode];
  const chosen = node.options[index];

  // Store answer by type
  if (node.type === 'phenomenon' || node.type === 'refine') {
    diagState.phenomenon = chosen.value;
    if (chosen.next && chosen.next !== 'proximity') {
      // Branch into a depth question
      diagState.pendingNext = 'proximity';
      diagState.currentNode = chosen.next;
    } else {
      diagState.currentNode = 'proximity';
      diagState.flowIndex   = 1;
    }
  } else if (node.type === 'proximity') {
    diagState.proximity   = chosen.value;
    diagState.currentNode = 'corroboration';
    diagState.flowIndex   = 2;
  } else if (node.type === 'corroboration') {
    diagState.corroboration = chosen.value;
    diagState.currentNode   = 'recurrence';
    diagState.flowIndex     = 3;
  } else if (node.type === 'recurrence') {
    diagState.recurrence  = chosen.value;
    diagState.currentNode = 'impact';
    diagState.flowIndex   = 4;
  } else if (node.type === 'impact') {
    diagState.impact = chosen.value;
    showDiagResult();
    return;
  }

  // Animate transition
  const qEl = document.getElementById('diag-question-text');
  qEl.style.opacity = '0';
  setTimeout(() => {
    renderDiagQuestion();
    qEl.style.opacity = '1';
  }, 180);
}

function calcDiagScore() {
  const base    = PHENOMENON_WEIGHTS[diagState.phenomenon]  || 2.5;
  const proxM   = PROXIMITY_MULT[diagState.proximity]       || 0.7;
  const corrM   = CORROBORATION_MULT[diagState.corroboration] || 1.0;
  const recurM  = RECURRENCE_MULT[diagState.recurrence]     || 1.0;
  const impactM = IMPACT_MULT[diagState.impact]             || 0.8;

  const raw   = base * proxM * corrM * recurM * impactM;
  return Math.min(10.0, parseFloat(raw.toFixed(2)));
}

function showDiagResult() {
  const score = calcDiagScore();
  const cls   = CLASSIFICATIONS.find(c => score >= c.min) || CLASSIFICATIONS[4];
  const isMember = !!(localStorage.getItem('si_member_token'));
  const phenLabel = getPhenomenonLabel(diagState.phenomenon);

  document.getElementById('diag-questions').style.display = 'none';
  const result = document.getElementById('diag-result');
  result.style.display = 'block';

  result.innerHTML = `
    <div class="diag-result-inner">

      <div class="diag-file-header">
        <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.15em;color:rgba(124,58,237,.5);margin-bottom:.3rem">STRANGENESS IS — CLASSIFICATION REPORT</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.1em;color:rgba(255,255,255,.2)">CASE OPENED: ${new Date().toISOString().slice(0,10)} · REF: SI-${Math.floor(Math.random()*90000+10000)}</div>
      </div>

      <div style="border-top:1px solid rgba(124,58,237,.2);margin:1rem 0"></div>

      <div class="diag-type-label">Classification</div>
      <div class="diag-code" style="font-family:'Share Tech Mono',monospace;font-size:.7rem;letter-spacing:.2em;color:${cls.color};margin-bottom:.25rem">${cls.code} CLASS</div>
      <div class="diag-type" style="color:${cls.color};text-shadow:0 0 20px ${cls.glow}">${cls.title}</div>

      <div class="diag-score-row">
        <div class="diag-score-block">
          <div style="font-family:'Share Tech Mono',monospace;font-size:1.8rem;font-weight:700;color:${cls.color}">${score.toFixed(1)}</div>
          <div style="font-family:'Cinzel',serif;font-size:.55rem;letter-spacing:.1em;color:rgba(255,255,255,.3)">STRANGENESS INDEX</div>
        </div>
        <div class="diag-phenom-block">
          <div style="font-size:.75rem;color:rgba(255,255,255,.5);margin-bottom:.15rem">Primary phenomenon</div>
          <div style="font-family:'Cinzel',serif;font-size:.7rem;letter-spacing:.05em;color:${cls.color}">${phenLabel}</div>
        </div>
      </div>

      <div style="border-top:1px solid rgba(124,58,237,.15);margin:1rem 0"></div>

      <div class="diag-desc">${cls.desc}</div>

      <div style="background:rgba(124,58,237,.06);border:1px solid rgba(124,58,237,.15);border-radius:6px;padding:.75rem 1rem;margin:1rem 0;font-family:'Share Tech Mono',monospace;font-size:.65rem;color:rgba(255,255,255,.4);line-height:1.7">
        ${cls.network}
      </div>

      <div style="border-top:1px solid rgba(124,58,237,.2);margin:1rem 0"></div>

      <div style="font-family:'Cinzel',serif;font-size:.68rem;letter-spacing:.12em;color:#d4a843;margin-bottom:.5rem">ORACLE ASSESSMENT</div>
      <div style="font-size:.88rem;color:#9080b0;line-height:1.75;margin-bottom:.5rem">${cls.urgency}</div>

      <div class="diag-actions" style="flex-direction:column;gap:.6rem;margin-top:1.25rem">
        <a href="chatbot.html" class="diag-btn-primary" onclick="closeDiagnosis();if(window.siTrack)siTrack('diag_oracle_click',{cls:'${cls.code}',score:${score}})">
          Consult The Oracle — ${cls.cta}
        </a>
        ${score >= 7 ? `
        <a href="tel:8333325436" class="diag-btn-secondary" style="background:rgba(212,168,67,.12);border-color:rgba(212,168,67,.4);color:#d4a843" onclick="closeDiagnosis();if(window.siTrack)siTrack('diag_call_click',{cls:'${cls.code}',score:${score}})">
          📞 Speak with a Believer Agent — (833) 33-ALIEN · 833-332-5436
        </a>
        ` : ''}
        <a href="submit.html" class="diag-btn-secondary" onclick="closeDiagnosis();if(window.siTrack)siTrack('diag_report_click',{cls:'${cls.code}'})">
          File your official case report
        </a>
        ${!isMember ? `
        <button class="diag-btn-secondary" onclick="closeDiagnosis();setTimeout(()=>{ if(window.openPricingModal)openPricingModal('oracle');else window.location.href='member.html?plan=oracle'; },300)" style="opacity:.85">
          Join The Network — $19/mo includes 1 live session
        </button>
        ` : ''}
        <button class="diag-btn-secondary" onclick="closeDiagnosis()" style="opacity:.45;font-size:.75rem;padding:.4rem">Close</button>
      </div>

    </div>
  `;

  if (window.siTrack) siTrack('diagnosis_complete', { cls: cls.code, score, phenomenon: diagState.phenomenon });
}

function getPhenomenonLabel(val) {
  const map = {
    'dimension_consciousness': 'Dimension / Consciousness Field',
    'demon_battle':            'Entity Confrontation / Other Dimension',
    'time_travel':             'Time Travel / Time Slip',
    'alien_abduction':         'Alien Abduction / Missing Time',
    'alien_takeover_knowledge':'Government / Alien Takeover Intelligence',
    'teleportation':           'Teleportation / Physical Displacement',
    'entity_contact':          'Non-Human Entity Contact',
    'consciousness_jump':      'Consciousness Transfer / Jumping',
    'psychic_major':           'Major Psychic / Remote Viewing Event',
    'nde':                     'Near-Death / Afterlife Experience',
    'government_conspiracy':   'Government / Classified Programs',
    'cryptid':                 'Cryptid / Unknown Creature',
    'uap_sighting':            'UAP / Unidentified Craft',
    'paranormal_ghost':        'Paranormal / Ghost / Haunting',
    'earth_disaster':          'Earth Change / Disaster',
    'psychic_minor':           'Psychic Sensitivity / Consciousness',
    'unexplained':             'Unclassified Anomalous Experience',
  };
  return map[val] || 'Anomalous Experience';
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-strange-meter]').forEach(el => {
    new StrangeMeter(el.id);
  });

  const overlay = document.getElementById('diagnosis-overlay');
  if (overlay) {
    overlay.addEventListener('click', e => { if (e.target === overlay) closeDiagnosis(); });
  }
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDiagnosis(); });
});
