// js/strange-meter.js
// Daily Strange Meter — pulls strangeness index from latest report
// and animates a gauge on any page that includes it.
// Also powers the Strange Diagnosis button and modal.

const BACKEND_URL = 'https://api.strangenessis.com';

// ── Strange Meter ─────────────────────────────────────────────────────────────
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
      <!-- Background arc -->
      <path d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none" stroke="#1e1e32" stroke-width="14" stroke-linecap="round"/>
      <!-- Colored arc -->
      <path class="sm-arc" d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none" stroke="url(#sm-arc-grad)" stroke-width="14"
            stroke-linecap="round" stroke-dasharray="251" stroke-dashoffset="125"/>
      <!-- Tick marks -->
      <line x1="20"  y1="100" x2="28"  y2="100" stroke="#4a4060" stroke-width="2"/>
      <line x1="100" y1="20"  x2="100" y2="30"  stroke="#4a4060" stroke-width="2"/>
      <line x1="180" y1="100" x2="172" y2="100" stroke="#4a4060" stroke-width="2"/>
      <text x="16"  y="116" fill="#4a4060" font-size="9" text-anchor="middle">0</text>
      <text x="100" y="18"  fill="#4a4060" font-size="9" text-anchor="middle">5</text>
      <text x="184" y="116" fill="#4a4060" font-size="9" text-anchor="middle">10</text>
      <!-- Needle -->
      <line class="sm-needle" x1="100" y1="100" x2="100" y2="28"
            stroke="#e8e0ff" stroke-width="2.5" stroke-linecap="round"
            transform-origin="100 100" transform="rotate(0)"/>
      <!-- Center dot -->
      <circle cx="100" cy="100" r="6" fill="#7c3aed"/>
      <circle cx="100" cy="100" r="3" fill="#c084fc"/>
    </svg>
    <div class="sm-readout">
      <span class="sm-value">—</span>
      <span class="sm-unit">/10</span>
    </div>
  </div>
  <div class="sm-label">Calibrating...</div>
</div>`;
  }

  async loadData() {
    try {
      const res  = await fetch(`${BACKEND_URL}/reports/latest`);
      const data = await res.json();
      const report = data.report;

      if (report) {
        this.targetValue = parseFloat(report.strangeness_index) || 5;
        this.dateEl.textContent  = report.date_label || 'Today';
        this.animateTo(this.targetValue);
      } else {
        // No reports yet — show a default value with subtle animation
        this.targetValue = 6.6;
        this.dateEl.textContent = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        this.animateTo(this.targetValue);
      }
    } catch {
      this.targetValue = 6.6;
      this.dateEl.textContent = 'Today';
      this.animateTo(this.targetValue);
    }
  }

  animateTo(target) {
    const start     = this.value;
    const duration  = 2200;
    const startTime = performance.now();

    // Add geiger-counter jitter
    const jitterInterval = setInterval(() => {
      const jitter = (Math.random() - 0.5) * 0.4;
      this.render(this.value + jitter);
    }, 80);

    const tick = (now) => {
      const elapsed  = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      this.value     = start + (target - start) * eased;
      this.render(this.value);
      if (progress < 1) {
        this.animFrame = requestAnimationFrame(tick);
      } else {
        clearInterval(jitterInterval);
        this.value = target;
        this.render(target);
        this.setLabel(target);
        // Pulse the needle at final value
        this.pulseFinal();
      }
    };
    requestAnimationFrame(tick);
  }

  render(val) {
    // Needle: -90deg = 0, 0deg = 5, +90deg = 10
    const angle   = (val / 10) * 180 - 90;
    const offset  = 251 - (val / 10) * 251;
    const needle  = this.container.querySelector('.sm-needle');
    const arc     = this.container.querySelector('.sm-arc');
    const valueEl = this.container.querySelector('.sm-value');
    if (needle) needle.setAttribute('transform', `rotate(${angle})`);
    if (arc)    arc.style.strokeDashoffset = Math.max(0, offset);
    if (valueEl) valueEl.textContent = Math.max(0, Math.min(10, val)).toFixed(1);
  }

  setLabel(val) {
    const labels = [
      [0,  2,  'Mundane — nothing to see here'],
      [2,  4,  'Slightly strange — stay alert'],
      [4,  6,  'Elevated strangeness — eyes open'],
      [6,  8,  'High strangeness — something\'s out there'],
      [8,  9,  'Critical — veil is thinning'],
      [9,  10, 'MAXIMUM STRANGENESS — they are here'],
    ];
    const label = labels.find(([min, max]) => val >= min && val < max);
    const labelEl = this.container.querySelector('.sm-label');
    if (labelEl && label) labelEl.textContent = label[2];
  }

  pulseFinal() {
    const needle = this.container.querySelector('.sm-needle');
    if (!needle) return;
    let count = 0;
    const pulse = setInterval(() => {
      const jitter = (Math.random() - 0.5) * 0.6;
      this.render(this.value + jitter);
      if (++count > 6) {
        clearInterval(pulse);
        this.render(this.value);
      }
    }, 120);
  }
}


// ── Strange Diagnosis Modal ───────────────────────────────────────────────────
const DIAGNOSIS_QUESTIONS = [
  {
    q: 'Have you ever witnessed something you could not explain?',
    options: ['Yes — and it changed me', 'Yes — but I dismissed it', 'I\'m not sure', 'No — not yet'],
  },
  {
    q: 'How would you describe your relationship with the unknown?',
    options: ['I actively seek it', 'It finds me', 'I\'m cautiously curious', 'I prefer explanations'],
  },
  {
    q: 'When you look up at the night sky, what do you feel?',
    options: ['We are not alone — I know it', 'Wonder and unease', 'Curiosity', 'Just stars'],
  },
];

const DIAGNOSIS_TYPES = [
  { type: 'Class 5 Experiencer',   desc: 'The veil has already been lifted for you. You have seen beyond the ordinary world and cannot unsee it. The Oracle has much to discuss with you.', color: '#7c3aed', threshold: 10 },
  { type: 'Active Investigator',   desc: 'You seek the truth with purpose. Your instincts are sharp and your mind is open. The Oracle recognizes a kindred spirit.', color: '#a855f7', threshold: 7 },
  { type: 'Awakening Believer',    desc: 'Something has stirred within you — a knowing that cannot be explained. You stand at the threshold. The Oracle awaits your first step.', color: '#d4a843', threshold: 4 },
  { type: 'Dormant Observer',      desc: 'You sense something is there but hold back. The Oracle sees potential in you. One encounter is all it takes.', color: '#2dd4bf', threshold: 0 },
];

let diagAnswers  = [];
let diagQuestion = 0;

function openDiagnosis() {
  diagAnswers  = [];
  diagQuestion = 0;
  document.getElementById('diagnosis-overlay').classList.add('visible');
  document.body.style.overflow = 'hidden';
  renderDiagQuestion();
}

function closeDiagnosis() {
  document.getElementById('diagnosis-overlay').classList.remove('visible');
  document.body.style.overflow = '';
  // Reset
  setTimeout(() => {
    diagAnswers  = [];
    diagQuestion = 0;
    document.getElementById('diag-result').style.display  = 'none';
    document.getElementById('diag-questions').style.display = 'block';
    renderDiagQuestion();
  }, 400);
}

function renderDiagQuestion() {
  const q     = DIAGNOSIS_QUESTIONS[diagQuestion];
  const total = DIAGNOSIS_QUESTIONS.length;

  document.getElementById('diag-progress-text').textContent = `${diagQuestion + 1} of ${total}`;
  document.getElementById('diag-progress-bar').style.width  = `${((diagQuestion) / total) * 100}%`;
  document.getElementById('diag-question-text').textContent = q.q;

  const opts = document.getElementById('diag-options');
  opts.innerHTML = q.options.map((opt, i) => `
    <button class="diag-opt" onclick="answerDiag(${i})">${opt}</button>
  `).join('');
}

function answerDiag(index) {
  diagAnswers.push(index);
  diagQuestion++;

  if (diagQuestion >= DIAGNOSIS_QUESTIONS.length) {
    showDiagResult();
  } else {
    // Animate transition
    const qEl = document.getElementById('diag-question-text');
    qEl.style.opacity = '0';
    setTimeout(() => {
      renderDiagQuestion();
      qEl.style.opacity = '1';
    }, 200);
  }
}

function showDiagResult() {
  const score     = diagAnswers.reduce((sum, a) => sum + (3 - a), 0);
  const maxScore  = DIAGNOSIS_QUESTIONS.length * 3;
  const pct       = score / maxScore;
  const threshold = pct * 12;
  const diagnosis = DIAGNOSIS_TYPES.find(d => threshold >= d.threshold) || DIAGNOSIS_TYPES[3];

  // Oracle insight — unique hook per diagnosis type
  const ORACLE_HOOKS = {
    'Class 5 Experiencer': {
      hook:    'The Oracle has been expecting you.',
      insight: 'Your profile matches 3 active case files in our intelligence network. The Oracle can cross-reference your experience against classified UAP reports, government disclosure timelines, and 847 other Class 5 accounts.',
      cta:     'Access your case file',
      urgency: 'Class 5 Experiencers qualify for priority Oracle access.',
    },
    'Active Investigator': {
      hook:    'The Oracle recognizes a trained mind.',
      insight: 'Investigators like you have uncovered 4 of our last 10 breakthrough reports. The Oracle can brief you daily on developments that match your investigative profile — government disclosure, UAP patterns, and source intelligence.',
      cta:     'Start your investigation',
      urgency: 'Join 200+ investigators already inside.',
    },
    'Awakening Believer': {
      hook:    'You stand at the threshold.',
      insight: 'Something brought you here. The Oracle can help you understand what that is — your answers suggest a pattern that connects to 3 active phenomena in our current intelligence files.',
      cta:     'Step through the threshold',
      urgency: 'The Oracle is available now.',
    },
    'Dormant Observer': {
      hook:    'The Oracle sees what you have not yet seen in yourself.',
      insight: 'Most Dormant Observers have their first real encounter within 6 months of awakening. The Oracle tracks the phenomena most likely to intersect with your profile — and will brief you when it happens.',
      cta:     'Begin your watch',
      urgency: 'Free access — 3 conversations to start.',
    },
  };

  const hook = ORACLE_HOOKS[diagnosis.type] || ORACLE_HOOKS['Dormant Observer'];
  const isMember = !!(localStorage.getItem('si_member_token'));
  const freeLeft = Math.max(0, 3 - parseInt(localStorage.getItem('si_free_chats') || '0'));

  document.getElementById('diag-questions').style.display = 'none';
  const result = document.getElementById('diag-result');
  result.style.display = 'block';

  result.innerHTML = `
    <div class="diag-result-inner">

      <!-- Diagnosis -->
      <div class="diag-sigil">🔮</div>
      <div class="diag-type-label">Your strangeness diagnosis</div>
      <div class="diag-type" style="color:${diagnosis.color}">${diagnosis.type}</div>
      <div class="diag-desc">${diagnosis.desc}</div>

      <!-- Divider -->
      <div style="border-top:1px solid rgba(124,58,237,.2);margin:1.25rem 0;"></div>

      <!-- Soft sell — Oracle hook -->
      <div style="text-align:left;padding:.1rem .25rem">
        <div style="font-family:'Cinzel',serif;font-size:.72rem;letter-spacing:.14em;color:#d4a843;margin-bottom:.5rem">${hook.hook}</div>
        <div style="font-size:.92rem;color:#9080b0;line-height:1.7;margin-bottom:1rem">${hook.insight}</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:rgba(124,58,237,.6);margin-bottom:1rem">${hook.urgency}</div>
      </div>

      <!-- CTA -->
      <div class="diag-actions" style="flex-direction:column;gap:.6rem">
        ${isMember ? `
          <a href="chatbot.html" class="diag-btn-primary" onclick="closeDiagnosis()">
            🔮 Open The Oracle — ${hook.cta}
          </a>
        ` : `
          <a href="chatbot.html" class="diag-btn-primary" onclick="closeDiagnosis(); if(window.siTrack) siTrack('diag_oracle_click',{type:'${diagnosis.type}'})">
            🔮 ${hook.cta} — ${freeLeft > 0 ? freeLeft + ' free conversations' : 'Join The Oracle'}
          </a>
          ${freeLeft > 0 ? `
            <div style="font-family:'Cinzel',serif;font-size:.58rem;letter-spacing:.1em;color:#9080b0;text-align:center">No account needed to start</div>
          ` : `
            <button class="diag-btn-secondary" onclick="closeDiagnosis(); setTimeout(()=>{ if(window.openPricingModal) openPricingModal('oracle'); else window.location.href='member.html?plan=oracle'; },300)">
              Join The Oracle — $9/mo
            </button>
            <div style="font-family:'Cinzel',serif;font-size:.58rem;letter-spacing:.1em;color:#9080b0;text-align:center">Already a member? <a href="member.html" onclick="closeDiagnosis()" style="color:#c084fc">Sign in →</a></div>
          `}
        `}
        <button class="diag-btn-secondary" onclick="closeDiagnosis()" style="opacity:.6;font-size:.75rem;padding:.4rem">Maybe later</button>
      </div>

    </div>
  `;

  // Track in analytics
  if (window.siTrack) siTrack('diagnosis_complete', { type: diagnosis.type, score: ${threshold.toFixed(1)} });
}

// ── Init on DOM ready ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Init all strange meters on the page
  document.querySelectorAll('[data-strange-meter]').forEach(el => {
    new StrangeMeter(el.id);
  });

  // Diagnosis modal close on overlay click
  const overlay = document.getElementById('diagnosis-overlay');
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeDiagnosis();
    });
  }

  // Escape key closes modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDiagnosis();
  });
});
