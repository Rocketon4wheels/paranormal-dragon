// js/analytics.js
// Strangeness IS — GA4 + internal analytics
// Drop on every page. GA_ID auto-configured from meta tag or window.SI_GA_ID

(function () {
  const GA_ID = window.SI_GA_ID || document.querySelector('meta[name="ga-id"]')?.content || 'G-XXXXXXXXXX';
  const API   = window.SI_API  || 'https://api.strangenessis.com';

  // ── Load GA4 ─────────────────────────────────────────────────
  if (GA_ID && GA_ID !== 'G-XXXXXXXXXX') {
    const script = document.createElement('script');
    script.async = true;
    script.src   = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', GA_ID, {
      page_title:    document.title,
      page_location: location.href,
      // Privacy-friendly settings
      anonymize_ip:  true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });
  }

  // ── Internal page view tracking ───────────────────────────────
  function trackPageView() {
    try {
      fetch(`${API}/analytics/pageview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: location.pathname }),
      }).catch(() => {});
    } catch {}
  }

  // ── Internal event tracking ───────────────────────────────────
  window.siTrack = function (event, properties = {}) {
    // GA4
    if (window.gtag) {
      gtag('event', event, properties);
    }
    // Internal
    try {
      fetch(`${API}/analytics/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, properties }),
      }).catch(() => {});
    } catch {}
  };

  // ── Auto-track clicks on key elements ────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    trackPageView();

    // Track pricing button clicks
    document.querySelectorAll('.price-btn, [data-track]').forEach(btn => {
      btn.addEventListener('click', () => {
        const plan = btn.closest('[class*=price-card]')?.querySelector('.price-name')?.textContent || btn.dataset.track || 'unknown';
        siTrack('pricing_click', { plan, page: location.pathname });
      });
    });

    // Track Oracle opens
    document.querySelectorAll('a[href*="chatbot"]').forEach(a => {
      a.addEventListener('click', () => siTrack('oracle_link_click', { source: location.pathname }));
    });

    // Track sighting form starts
    const submitBtn = document.querySelector('[href*="submit"]');
    if (submitBtn) {
      submitBtn.addEventListener('click', () => siTrack('sighting_form_start'));
    }

    // Track scroll depth
    let maxScroll = 0;
    const scrollMilestones = new Set();
    window.addEventListener('scroll', () => {
      const pct = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
      if (pct > maxScroll) maxScroll = pct;
      [25, 50, 75, 90].forEach(m => {
        if (pct >= m && !scrollMilestones.has(m)) {
          scrollMilestones.add(m);
          siTrack('scroll_depth', { depth: m, page: location.pathname });
        }
      });
    }, { passive: true });

    // Track time on page
    const startTime = Date.now();
    window.addEventListener('beforeunload', () => {
      const seconds = Math.round((Date.now() - startTime) / 1000);
      if (seconds > 5) {
        navigator.sendBeacon(`${API}/analytics/event`, JSON.stringify({
          event: 'time_on_page',
          properties: { seconds, page: location.pathname },
        }));
      }
    });
  });

  // ── Member session restore ────────────────────────────────────
  window.SI_MEMBER = null;
  const token = localStorage.getItem('si_member_token');
  if (token) {
    fetch(`${API}/member/profile`, { headers: { 'X-Member-Token': token } })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.member) {
          window.SI_MEMBER = data.member;
          window.SI_MEMBER.token = token;
          document.dispatchEvent(new CustomEvent('si:member-loaded', { detail: data }));
        } else {
          localStorage.removeItem('si_member_token');
        }
      })
      .catch(() => {});
  }

  // ── Expose member-aware Oracle message counter ────────────────
  window.SI_FREE_LIMIT = 3;
  window.SI_IS_MEMBER  = () => !!(window.SI_MEMBER?.plan);
  window.SI_PLAN       = () => window.SI_MEMBER?.plan || 'free';
})();
