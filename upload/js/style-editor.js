// js/style-editor.js
// Visual Style Editor for Strangeness IS
// Drop this script on any page to get a floating editor panel
// Only loads when ?edit=1 is in the URL (safe for production)

(function () {
  // Only activate when ?edit=1 or #edit is in URL
  if (!location.search.includes('edit=1') && !location.hash.includes('edit')) return;

  // ── CSS ──────────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #si-editor {
      position: fixed;
      top: 80px;
      right: 0;
      width: 320px;
      max-height: calc(100vh - 100px);
      background: #0d0022;
      border: 1px solid rgba(124,58,237,.4);
      border-right: none;
      border-radius: 10px 0 0 10px;
      z-index: 99999;
      display: flex;
      flex-direction: column;
      box-shadow: -4px 0 30px rgba(124,58,237,.2);
      font-family: 'Cinzel', serif;
      transition: transform .3s ease;
    }
    #si-editor.collapsed { transform: translateX(290px); }
    #si-editor-toggle {
      position: absolute;
      left: -36px;
      top: 50%;
      transform: translateY(-50%);
      width: 36px;
      height: 80px;
      background: #0d0022;
      border: 1px solid rgba(124,58,237,.4);
      border-right: none;
      border-radius: 8px 0 0 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #c084fc;
      font-size: 18px;
      writing-mode: vertical-rl;
      letter-spacing: .1em;
      font-family: 'Cinzel', serif;
      font-size: .55rem;
      padding: 8px 4px;
    }
    #si-editor-toggle:hover { background: #160030; }
    #si-editor-header {
      padding: .75rem 1rem;
      border-bottom: 1px solid rgba(124,58,237,.2);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }
    #si-editor-title {
      font-family: 'Cinzel', serif;
      font-size: .7rem;
      letter-spacing: .16em;
      color: #c084fc;
    }
    #si-editor-page {
      font-size: .58rem;
      color: #9080b0;
      font-family: 'Share Tech Mono', monospace;
    }
    #si-editor-body {
      flex: 1;
      overflow-y: auto;
      padding: .75rem;
    }
    #si-editor-body::-webkit-scrollbar { width: 3px; }
    #si-editor-body::-webkit-scrollbar-thumb { background: rgba(124,58,237,.3); }

    /* Selected element highlight */
    .si-selected {
      outline: 2px solid #7c3aed !important;
      outline-offset: 2px !important;
    }
    .si-hover {
      outline: 1px dashed rgba(124,58,237,.5) !important;
      outline-offset: 2px !important;
      cursor: crosshair !important;
    }

    /* Editor controls */
    .si-section {
      margin-bottom: .75rem;
      background: rgba(124,58,237,.06);
      border: 1px solid rgba(124,58,237,.15);
      border-radius: 6px;
      overflow: hidden;
    }
    .si-section-title {
      font-family: 'Cinzel', serif;
      font-size: .58rem;
      letter-spacing: .14em;
      color: #9080b0;
      padding: .4rem .65rem;
      background: rgba(124,58,237,.1);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
    }
    .si-section-body {
      padding: .5rem .65rem;
    }
    .si-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .5rem;
      margin-bottom: .4rem;
    }
    .si-label {
      font-family: 'Share Tech Mono', monospace;
      font-size: .6rem;
      color: #9080b0;
      white-space: nowrap;
      min-width: 70px;
    }
    .si-input {
      background: #07070f;
      border: 1px solid rgba(124,58,237,.2);
      border-radius: 4px;
      color: #e8e0ff;
      font-family: 'Share Tech Mono', monospace;
      font-size: .72rem;
      padding: .25rem .5rem;
      outline: none;
      transition: border-color .2s;
      flex: 1;
    }
    .si-input:focus { border-color: #7c3aed; }
    .si-color { width: 36px; height: 26px; padding: 2px; cursor: pointer; flex-shrink: 0; }
    .si-select {
      background: #07070f;
      border: 1px solid rgba(124,58,237,.2);
      border-radius: 4px;
      color: #e8e0ff;
      font-family: 'Share Tech Mono', monospace;
      font-size: .68rem;
      padding: .25rem .4rem;
      outline: none;
      flex: 1;
    }
    .si-select option { background: #0d0022; }
    .si-slider {
      flex: 1;
      accent-color: #7c3aed;
      cursor: pointer;
    }
    .si-val {
      font-family: 'Share Tech Mono', monospace;
      font-size: .62rem;
      color: #c084fc;
      min-width: 35px;
      text-align: right;
    }
    .si-btn {
      font-family: 'Cinzel', serif;
      font-size: .58rem;
      letter-spacing: .1em;
      padding: .35rem .75rem;
      border-radius: 4px;
      cursor: pointer;
      border: none;
      transition: all .2s;
    }
    .si-btn-purple { background: #7c3aed; color: #fff; }
    .si-btn-purple:hover { background: #a855f7; }
    .si-btn-outline { background: transparent; color: #c084fc; border: 1px solid rgba(124,58,237,.35); }
    .si-btn-outline:hover { background: rgba(124,58,237,.1); }
    .si-btn-red { background: transparent; color: #ef4444; border: 1px solid rgba(239,68,68,.3); }
    .si-btn-gold { background: transparent; color: #f0c060; border: 1px solid rgba(212,168,67,.35); }
    .si-btn-gold:hover { background: rgba(212,168,67,.08); }

    .si-selector-display {
      background: #07070f;
      border: 1px solid rgba(124,58,237,.2);
      border-radius: 4px;
      padding: .35rem .6rem;
      font-family: 'Share Tech Mono', monospace;
      font-size: .65rem;
      color: #c084fc;
      word-break: break-all;
      min-height: 28px;
      margin-bottom: .5rem;
    }
    .si-mode-bar {
      display: flex;
      gap: .35rem;
      margin-bottom: .5rem;
    }
    .si-pick-btn {
      flex: 1;
      padding: .35rem .5rem;
      border-radius: 4px;
      font-family: 'Cinzel', serif;
      font-size: .55rem;
      letter-spacing: .1em;
      cursor: pointer;
      border: none;
      background: rgba(124,58,237,.1);
      color: #9080b0;
      transition: all .2s;
    }
    .si-pick-btn.active { background: #7c3aed; color: #fff; }
    .si-css-out {
      background: #000;
      border: 1px solid rgba(124,58,237,.15);
      border-radius: 4px;
      padding: .5rem;
      font-family: 'Share Tech Mono', monospace;
      font-size: .62rem;
      color: #22c55e;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre;
      margin-top: .5rem;
    }
    .si-saved-list {
      max-height: 150px;
      overflow-y: auto;
    }
    .si-saved-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: .3rem .5rem;
      border-bottom: 1px solid rgba(124,58,237,.1);
      font-family: 'Share Tech Mono', monospace;
      font-size: .62rem;
      color: #9080b0;
      gap: .4rem;
    }
    .si-saved-item:last-child { border-bottom: none; }
    .si-toast {
      position: fixed;
      bottom: 5rem;
      right: .75rem;
      background: #22c55e;
      color: #fff;
      font-family: 'Cinzel', serif;
      font-size: .6rem;
      letter-spacing: .1em;
      padding: .5rem 1rem;
      border-radius: 4px;
      z-index: 100000;
      opacity: 0;
      transition: opacity .3s;
      pointer-events: none;
    }
  `;
  document.head.appendChild(style);

  // ── State ─────────────────────────────────────────────────────
  let selectedEl = null;
  let pickMode   = false;
  let collapsed  = false;
  let savedStyles = JSON.parse(localStorage.getItem('si_styles') || '[]');
  let customStyleEl = null;

  // ── Build editor UI ───────────────────────────────────────────
  const editor = document.createElement('div');
  editor.id = 'si-editor';
  editor.innerHTML = `
    <div id="si-editor-toggle">✏️ STYLE</div>
    <div id="si-editor-header">
      <span id="si-editor-title">Style Editor</span>
      <span id="si-editor-page">${document.title.slice(0,20)}</span>
    </div>
    <div id="si-editor-body">

      <!-- Pick mode -->
      <div class="si-section">
        <div class="si-section-title">1. Select Element</div>
        <div class="si-section-body">
          <div class="si-mode-bar">
            <button class="si-pick-btn" id="si-pick-btn" onclick="siTogglePick()">🎯 Click to pick</button>
            <button class="si-pick-btn" onclick="siClearSelection()">✕ Clear</button>
          </div>
          <div class="si-selector-display" id="si-selector">Nothing selected — click Pick then click any element</div>
          <div class="si-row" style="margin-top:.4rem">
            <span class="si-label">Or type selector</span>
            <input class="si-input" id="si-manual-sel" placeholder=".hero-title, h1, etc" onchange="siManualSelect(this.value)"/>
          </div>
        </div>
      </div>

      <!-- Typography -->
      <div class="si-section" id="si-typography">
        <div class="si-section-title" onclick="siToggleSection('typo')">Typography <span>▾</span></div>
        <div class="si-section-body" id="si-typo-body">
          <div class="si-row">
            <span class="si-label">Font size</span>
            <input class="si-slider" type="range" id="si-font-size" min="8" max="96" value="16" oninput="siApply('fontSize', this.value+'px'); document.getElementById('si-fs-val').textContent=this.value+'px'"/>
            <span class="si-val" id="si-fs-val">16px</span>
          </div>
          <div class="si-row">
            <span class="si-label">Font weight</span>
            <select class="si-select" id="si-font-weight" onchange="siApply('fontWeight', this.value)">
              <option value="300">Light 300</option>
              <option value="400" selected>Regular 400</option>
              <option value="600">Semi 600</option>
              <option value="700">Bold 700</option>
              <option value="900">Black 900</option>
            </select>
          </div>
          <div class="si-row">
            <span class="si-label">Font family</span>
            <select class="si-select" id="si-font-family" onchange="siApply('fontFamily', this.value)">
              <option value="'Cinzel', serif">Cinzel</option>
              <option value="'Cinzel Decorative', serif">Cinzel Decorative</option>
              <option value="'Crimson Pro', Georgia, serif">Crimson Pro</option>
              <option value="'Share Tech Mono', monospace">Share Tech Mono</option>
            </select>
          </div>
          <div class="si-row">
            <span class="si-label">Letter spacing</span>
            <input class="si-slider" type="range" id="si-letter-spacing" min="0" max="30" value="0" step="1" oninput="siApply('letterSpacing', this.value*0.01+'em'); document.getElementById('si-ls-val').textContent=(this.value*0.01).toFixed(2)+'em'"/>
            <span class="si-val" id="si-ls-val">0em</span>
          </div>
          <div class="si-row">
            <span class="si-label">Line height</span>
            <input class="si-slider" type="range" id="si-line-height" min="10" max="30" value="16" step="1" oninput="siApply('lineHeight', this.value*0.1); document.getElementById('si-lh-val').textContent=(this.value*0.1).toFixed(1)"/>
            <span class="si-val" id="si-lh-val">1.6</span>
          </div>
          <div class="si-row">
            <span class="si-label">Text align</span>
            <select class="si-select" onchange="siApply('textAlign', this.value)">
              <option value="left">Left</option>
              <option value="center">Center</option>
              <option value="right">Right</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Colors -->
      <div class="si-section">
        <div class="si-section-title" onclick="siToggleSection('color')">Color <span>▾</span></div>
        <div class="si-section-body" id="si-color-body">
          <div class="si-row">
            <span class="si-label">Text color</span>
            <input class="si-color" type="color" id="si-color" value="#e8e0ff" oninput="siApply('color', this.value)"/>
            <input class="si-input" id="si-color-hex" value="#e8e0ff" onchange="siApply('color', this.value); document.getElementById('si-color').value=this.value" style="flex:.6"/>
          </div>
          <div class="si-row">
            <span class="si-label">Background</span>
            <input class="si-color" type="color" id="si-bg" value="#07070f" oninput="siApply('backgroundColor', this.value)"/>
            <input class="si-input" id="si-bg-hex" value="#07070f" onchange="siApply('backgroundColor', this.value); document.getElementById('si-bg').value=this.value" style="flex:.6"/>
          </div>
          <div class="si-row">
            <span class="si-label">Opacity</span>
            <input class="si-slider" type="range" id="si-opacity" min="0" max="100" value="100" oninput="siApply('opacity', this.value/100); document.getElementById('si-op-val').textContent=this.value+'%'"/>
            <span class="si-val" id="si-op-val">100%</span>
          </div>
          <!-- Quick color presets -->
          <div style="display:flex;gap:.3rem;flex-wrap:wrap;margin-top:.35rem">
            <span class="si-label" style="width:100%;margin-bottom:.2rem">Brand colors</span>
            ${['#7c3aed','#a855f7','#c084fc','#d4a843','#f0c060','#e8e0ff','#07070f','#2dd4bf','#22c55e','#ef4444'].map(c=>
              `<div onclick="siApply('color','${c}');document.getElementById('si-color').value='${c}';document.getElementById('si-color-hex').value='${c}'" style="width:22px;height:22px;background:${c};border-radius:3px;cursor:pointer;border:1px solid rgba(255,255,255,.2)" title="${c}"></div>`
            ).join('')}
          </div>
        </div>
      </div>

      <!-- Spacing -->
      <div class="si-section">
        <div class="si-section-title" onclick="siToggleSection('spacing')">Spacing <span>▾</span></div>
        <div class="si-section-body" id="si-spacing-body">
          <div class="si-row"><span class="si-label">Padding top</span><input class="si-slider" type="range" min="0" max="200" value="0" oninput="siApply('paddingTop', this.value+'px'); document.getElementById('si-pt-v').textContent=this.value+'px'"/><span class="si-val" id="si-pt-v">0px</span></div>
          <div class="si-row"><span class="si-label">Padding btm</span><input class="si-slider" type="range" min="0" max="200" value="0" oninput="siApply('paddingBottom', this.value+'px'); document.getElementById('si-pb-v').textContent=this.value+'px'"/><span class="si-val" id="si-pb-v">0px</span></div>
          <div class="si-row"><span class="si-label">Margin top</span><input class="si-slider" type="range" min="-100" max="200" value="0" oninput="siApply('marginTop', this.value+'px'); document.getElementById('si-mt-v').textContent=this.value+'px'"/><span class="si-val" id="si-mt-v">0px</span></div>
          <div class="si-row"><span class="si-label">Margin btm</span><input class="si-slider" type="range" min="-100" max="200" value="0" oninput="siApply('marginBottom', this.value+'px'); document.getElementById('si-mb-v').textContent=this.value+'px'"/><span class="si-val" id="si-mb-v">0px</span></div>
        </div>
      </div>

      <!-- Position & Size -->
      <div class="si-section">
        <div class="si-section-title" onclick="siToggleSection('pos')">Position & Size <span>▾</span></div>
        <div class="si-section-body" id="si-pos-body">
          <div class="si-row">
            <span class="si-label">Width</span>
            <input class="si-input" id="si-width" placeholder="auto, 100%, 400px" onchange="siApply('width', this.value)"/>
          </div>
          <div class="si-row">
            <span class="si-label">Max-width</span>
            <input class="si-input" placeholder="none, 1200px..." onchange="siApply('maxWidth', this.value)"/>
          </div>
          <div class="si-row">
            <span class="si-label">Display</span>
            <select class="si-select" onchange="siApply('display', this.value)">
              <option value="">—</option>
              <option value="block">block</option>
              <option value="flex">flex</option>
              <option value="grid">grid</option>
              <option value="none">none (hide)</option>
              <option value="inline-block">inline-block</option>
            </select>
          </div>
          <div class="si-row">
            <span class="si-label">Flex align</span>
            <select class="si-select" onchange="siApply('alignItems', this.value)">
              <option value="">—</option>
              <option value="center">center</option>
              <option value="flex-start">start</option>
              <option value="flex-end">end</option>
            </select>
          </div>
          <div class="si-row">
            <span class="si-label">Justify</span>
            <select class="si-select" onchange="siApply('justifyContent', this.value)">
              <option value="">—</option>
              <option value="center">center</option>
              <option value="space-between">space-between</option>
              <option value="flex-start">start</option>
              <option value="flex-end">end</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Border & Shadow -->
      <div class="si-section">
        <div class="si-section-title" onclick="siToggleSection('border')">Border & Shadow <span>▾</span></div>
        <div class="si-section-body" id="si-border-body">
          <div class="si-row">
            <span class="si-label">Border radius</span>
            <input class="si-slider" type="range" min="0" max="50" value="0" oninput="siApply('borderRadius', this.value+'px'); document.getElementById('si-br-v').textContent=this.value+'px'"/>
            <span class="si-val" id="si-br-v">0px</span>
          </div>
          <div class="si-row">
            <span class="si-label">Border</span>
            <input class="si-input" placeholder="1px solid #7c3aed" onchange="siApply('border', this.value)"/>
          </div>
          <div class="si-row">
            <span class="si-label">Box shadow</span>
            <input class="si-input" placeholder="0 0 20px rgba(124,58,237,.4)" onchange="siApply('boxShadow', this.value)"/>
          </div>
          <div class="si-row">
            <span class="si-label">Text shadow</span>
            <input class="si-input" placeholder="0 0 20px #7c3aed" onchange="siApply('textShadow', this.value)"/>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="si-section">
        <div class="si-section-title">Actions</div>
        <div class="si-section-body">
          <div class="si-row" style="flex-wrap:wrap;gap:.35rem">
            <button class="si-btn si-btn-gold" onclick="siReadCurrent()">↺ Read current</button>
            <button class="si-btn si-btn-outline" onclick="siCopyCSS()">Copy CSS</button>
            <button class="si-btn si-btn-purple" onclick="siSaveStyle()">Save style</button>
            <button class="si-btn si-btn-red" onclick="siResetEl()">Reset element</button>
          </div>
          <div class="si-css-out" id="si-css-out"></div>
        </div>
      </div>

      <!-- Saved styles -->
      <div class="si-section">
        <div class="si-section-title" onclick="siToggleSection('saved')">Saved Styles <span id="si-saved-count"></span></div>
        <div class="si-section-body" id="si-saved-body">
          <div class="si-saved-list" id="si-saved-list"></div>
          <div class="si-row" style="margin-top:.4rem">
            <button class="si-btn si-btn-purple" style="flex:1" onclick="siExportCSS()">Export all as CSS</button>
            <button class="si-btn si-btn-red" onclick="siClearAll()">Clear all</button>
          </div>
        </div>
      </div>

    </div>
  `;
  document.body.appendChild(editor);

  // Toast
  const toastEl = document.createElement('div');
  toastEl.className = 'si-toast';
  toastEl.id = 'si-toast';
  document.body.appendChild(toastEl);

  function siToast(msg) {
    toastEl.textContent = msg;
    toastEl.style.opacity = '1';
    setTimeout(() => toastEl.style.opacity = '0', 2000);
  }

  // ── Toggle panel ──────────────────────────────────────────────
  document.getElementById('si-editor-toggle').onclick = () => {
    collapsed = !collapsed;
    editor.classList.toggle('collapsed', collapsed);
  };

  // ── Pick mode ─────────────────────────────────────────────────
  window.siTogglePick = function () {
    pickMode = !pickMode;
    document.getElementById('si-pick-btn').classList.toggle('active', pickMode);
    document.body.style.cursor = pickMode ? 'crosshair' : '';
    siToast(pickMode ? 'Click any element to select it' : 'Pick mode off');
  };

  document.addEventListener('mouseover', e => {
    if (!pickMode) return;
    if (editor.contains(e.target)) return;
    document.querySelectorAll('.si-hover').forEach(el => el.classList.remove('si-hover'));
    e.target.classList.add('si-hover');
  });

  document.addEventListener('click', e => {
    if (!pickMode) return;
    if (editor.contains(e.target)) return;
    e.preventDefault(); e.stopPropagation();
    document.querySelectorAll('.si-hover').forEach(el => el.classList.remove('si-hover'));
    selectElement(e.target);
    pickMode = false;
    document.getElementById('si-pick-btn').classList.remove('active');
    document.body.style.cursor = '';
  }, true);

  function selectElement(el) {
    if (selectedEl) selectedEl.classList.remove('si-selected');
    selectedEl = el;
    el.classList.add('si-selected');
    // Build selector
    const sel = buildSelector(el);
    document.getElementById('si-selector').textContent = sel;
    siReadCurrent();
    siToast('Element selected: ' + el.tagName.toLowerCase());
  }

  function buildSelector(el) {
    let sel = el.tagName.toLowerCase();
    if (el.id) return '#' + el.id;
    if (el.className && typeof el.className === 'string') {
      const classes = el.className.split(' ')
        .filter(c => c && !['si-selected','si-hover'].includes(c))
        .slice(0, 2);
      if (classes.length) sel += '.' + classes.join('.');
    }
    return sel;
  }

  window.siManualSelect = function (sel) {
    try {
      const el = document.querySelector(sel);
      if (el) { selectElement(el); siToast('Selected: ' + sel); }
      else siToast('No element found for: ' + sel);
    } catch (e) { siToast('Invalid selector'); }
  };

  window.siClearSelection = function () {
    if (selectedEl) selectedEl.classList.remove('si-selected');
    selectedEl = null;
    document.getElementById('si-selector').textContent = 'Nothing selected';
    document.getElementById('si-css-out').textContent = '';
  };

  // ── Apply style ───────────────────────────────────────────────
  window.siApply = function (prop, val) {
    if (!selectedEl) { siToast('Select an element first!'); return; }
    selectedEl.style[prop] = val;
    siUpdateCSSOut();
  };

  window.siReadCurrent = function () {
    if (!selectedEl) return;
    const cs = getComputedStyle(selectedEl);
    // Update sliders/inputs to reflect current values
    const fs = parseFloat(cs.fontSize) || 16;
    document.getElementById('si-font-size').value = Math.min(96, fs);
    document.getElementById('si-fs-val').textContent = Math.round(fs) + 'px';

    const color = cs.color;
    const bgColor = cs.backgroundColor;
    document.getElementById('si-color').value = rgbToHex(color) || '#e8e0ff';
    document.getElementById('si-color-hex').value = rgbToHex(color) || '#e8e0ff';
    document.getElementById('si-bg').value = rgbToHex(bgColor) || '#07070f';
    document.getElementById('si-bg-hex').value = rgbToHex(bgColor) || '#07070f';

    const fw = cs.fontWeight;
    document.getElementById('si-font-weight').value = fw;

    siUpdateCSSOut();
  };

  function siUpdateCSSOut() {
    if (!selectedEl) return;
    const inline = selectedEl.style.cssText;
    const sel = document.getElementById('si-selector').textContent;
    document.getElementById('si-css-out').textContent = inline
      ? `${sel} {\n  ${inline.split(';').filter(Boolean).join(';\n  ')};\n}`
      : '(no inline styles yet)';
  }

  // ── Save / Export ─────────────────────────────────────────────
  window.siSaveStyle = function () {
    if (!selectedEl) { siToast('Select an element first!'); return; }
    const sel  = document.getElementById('si-selector').textContent;
    const css  = selectedEl.style.cssText;
    if (!css) { siToast('No styles to save'); return; }
    const entry = { sel, css, page: document.title, ts: Date.now() };
    savedStyles = savedStyles.filter(s => s.sel !== sel); // overwrite if same selector
    savedStyles.push(entry);
    localStorage.setItem('si_styles', JSON.stringify(savedStyles));
    siRenderSaved();
    siApplyAllSaved();
    siToast('Style saved!');
  };

  window.siResetEl = function () {
    if (!selectedEl) return;
    selectedEl.style.cssText = '';
    siUpdateCSSOut();
    siToast('Element reset');
  };

  window.siCopyCSS = function () {
    const css = document.getElementById('si-css-out').textContent;
    navigator.clipboard.writeText(css).then(() => siToast('CSS copied to clipboard!'));
  };

  window.siExportCSS = function () {
    const all = savedStyles.map(s => `/* ${s.page} */\n${s.sel} {\n  ${s.css.split(';').filter(Boolean).join(';\n  ')};\n}`).join('\n\n');
    navigator.clipboard.writeText(all).then(() => siToast('All CSS copied!'));
    // Also create downloadable file
    const blob = new Blob([all], {type:'text/css'});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'strangenessis-custom.css'; a.click();
    URL.revokeObjectURL(url);
  };

  window.siClearAll = function () {
    if (!confirm('Clear all saved styles?')) return;
    savedStyles = [];
    localStorage.removeItem('si_styles');
    siRenderSaved();
    siToast('All saved styles cleared');
  };

  function siRenderSaved() {
    const listEl = document.getElementById('si-saved-list');
    document.getElementById('si-saved-count').textContent = `(${savedStyles.length})`;
    if (!savedStyles.length) { listEl.innerHTML = '<div style="color:#9080b0;font-size:.65rem;font-family:\'Share Tech Mono\',monospace;padding:.3rem .5rem">No saved styles</div>'; return; }
    listEl.innerHTML = savedStyles.map((s, i) => `
      <div class="si-saved-item">
        <span style="color:#c084fc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">${s.sel}</span>
        <button class="si-btn si-btn-outline" onclick="siApplySaved(${i})" style="padding:.2rem .5rem;font-size:.52rem">Apply</button>
        <button class="si-btn si-btn-red" onclick="siDeleteSaved(${i})" style="padding:.2rem .5rem;font-size:.52rem">✕</button>
      </div>`).join('');
  }

  window.siApplySaved = function (i) {
    const s = savedStyles[i];
    const el = document.querySelector(s.sel);
    if (el) { el.style.cssText = s.css; siToast('Applied: ' + s.sel); }
    else siToast('Element not found: ' + s.sel);
  };

  window.siDeleteSaved = function (i) {
    savedStyles.splice(i, 1);
    localStorage.setItem('si_styles', JSON.stringify(savedStyles));
    siRenderSaved();
  };

  function siApplyAllSaved() {
    savedStyles.forEach(s => {
      try {
        const els = document.querySelectorAll(s.sel);
        els.forEach(el => { el.style.cssText = s.css; });
      } catch {}
    });
  }

  // ── Section toggles ───────────────────────────────────────────
  window.siToggleSection = function (id) {
    const body = document.getElementById(`si-${id}-body`);
    if (body) body.style.display = body.style.display === 'none' ? 'block' : 'none';
  };

  // ── Utilities ─────────────────────────────────────────────────
  function rgbToHex(rgb) {
    if (!rgb || rgb === 'rgba(0, 0, 0, 0)') return null;
    const m = rgb.match(/\d+/g);
    if (!m || m.length < 3) return null;
    return '#' + [m[0],m[1],m[2]].map(x => parseInt(x).toString(16).padStart(2,'0')).join('');
  }

  // ── Init ──────────────────────────────────────────────────────
  siRenderSaved();
  siApplyAllSaved(); // re-apply any previously saved styles on page load

  // Custom stylesheet for persisted styles
  customStyleEl = document.createElement('style');
  customStyleEl.id = 'si-custom-styles';
  document.head.appendChild(customStyleEl);

  console.log('🔮 Strangeness IS Style Editor loaded. URL: add ?edit=1 to any page.');
})();
