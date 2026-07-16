// TAK12 Courses – Affiliate landing page interactions
// Converted from Claude Design "TAK12 Affiliate.dc.html" (DCLogic) to vanilla JS.

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    initCtaTracking();
    initHeroMotion();
    initFAQ();
    initQuiz();
    initCampaignCarousel();
  });

  // ---------- PostHog helper ----------
  function track(event, props) {
    try {
      if (window.posthog && typeof window.posthog.capture === 'function') {
        window.posthog.capture(event, props || {});
      }
    } catch (e) { /* analytics must never break the page */ }
  }

  // ---------- Affiliate CTA click tracking ----------
  function getCtaPosition(element) {
    var container = element.closest('nav, header, section, footer');
    if (!container) return 'unknown';
    if (container.id) return container.id;
    return (container.className || '').split(/\s+/)[0] || container.tagName.toLowerCase();
  }

  function getAffiliateIntent(destinationUrl) {
    if (destinationUrl.indexOf('bang-gia-chung-chi') !== -1) return 'certification';
    if (destinationUrl.indexOf('bang-gia-vao-6') !== -1) return 'exam_grade_6';
    if (destinationUrl.indexOf('bang-gia-vao-10') !== -1) return 'exam_grade_10';
    if (destinationUrl.indexOf('bang-gia-vao-dh') !== -1) return 'exam_university';
    if (destinationUrl.indexOf('bang-gia-hoc-tot') !== -1) return 'school_support';
    if (destinationUrl.indexOf('bang-gia') !== -1) return 'all_courses';
    return 'free_account';
  }

  function initCtaTracking() {
    var ctas = document.querySelectorAll('[data-cta]');
    for (var j = 0; j < ctas.length; j++) {
      ctas[j].addEventListener('click', function () {
        var destinationUrl = this.href || '';
        track('affiliate_cta_click', {
          source_page: window.location.pathname,
          cta_id: this.getAttribute('data-cta'),
          position: getCtaPosition(this),
          intent: this.getAttribute('data-intent') || getAffiliateIntent(destinationUrl),
          destination_url: destinationUrl
        });
      });
    }
  }

  // ---------- Hero mouse motion ----------
  function initHeroMotion() {
    var hero = document.querySelector('[data-hero-motion]');
    if (!hero) return;

    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var canHover = window.matchMedia && window.matchMedia('(hover: hover)').matches;
    if (reduceMotion || !canHover) return;

    var bounds = null;
    var targetX = 0;
    var targetY = 0;
    var currentX = 0;
    var currentY = 0;
    var raf = null;

    function readBounds() {
      bounds = hero.getBoundingClientRect();
    }

    function setVars(x, y) {
      hero.style.setProperty('--hero-x', x.toFixed(4));
      hero.style.setProperty('--hero-y', y.toFixed(4));
      hero.style.setProperty('--hero-glow-x', ((x + 1) * 50).toFixed(2) + '%');
      hero.style.setProperty('--hero-glow-y', ((y + 1) * 50).toFixed(2) + '%');
      hero.style.setProperty('--hero-tilt-x', (-y * 4).toFixed(3) + 'deg');
      hero.style.setProperty('--hero-tilt-y', (x * 5).toFixed(3) + 'deg');
    }

    function tick() {
      currentX += (targetX - currentX) * 0.12;
      currentY += (targetY - currentY) * 0.12;
      setVars(currentX, currentY);

      if (Math.abs(targetX - currentX) > 0.001 || Math.abs(targetY - currentY) > 0.001) {
        raf = window.requestAnimationFrame(tick);
      } else {
        raf = null;
      }
    }

    function startTick() {
      if (!raf) raf = window.requestAnimationFrame(tick);
    }

    hero.addEventListener('pointerenter', readBounds);
    hero.addEventListener('pointermove', function (event) {
      if (!bounds) readBounds();
      targetX = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
      targetY = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
      targetX = Math.max(-1, Math.min(1, targetX));
      targetY = Math.max(-1, Math.min(1, targetY));
      startTick();
    });
    hero.addEventListener('pointerleave', function () {
      targetX = 0;
      targetY = 0;
      startTick();
    });
    window.addEventListener('resize', readBounds);
  }

  // ---------- Campaign carousel ----------
  // Each .campaign-slide reads its own data-end-date="dd/mm/yyyy" off itself
  // and fills in its countdown and displayed end date (attachCountdown).
  // Editors only ever need to touch that one attribute per slide (plus the
  // plain-text copy in the HTML). Once a slide's end date fully passes it
  // hides itself; the carousel (initCampaignCarousel) reacts by dropping it
  // from rotation, collapsing to a plain static banner once only one slide
  // is left, and hiding entirely once none are. On a slide's own end-date
  // calendar day it switches to a live, ticking HH:MM:SS countdown for a
  // stronger urgency (FOMO) effect.
  var MS_PER_DAY = 1000 * 60 * 60 * 24;

  function attachCountdown(slide, onExpire) {
    var endDateStr = slide.getAttribute('data-end-date');
    if (!endDateStr) return;

    var parts = endDateStr.split('/').map(function (n) { return parseInt(n, 10); });
    var day = parts[0], month = parts[1], year = parts[2];
    if (!day || !month || !year) return;

    var endDate = new Date(year, month - 1, day, 23, 59, 59);

    var daysBlock = slide.querySelector('[data-campaign-days-block]');
    var timerBlock = slide.querySelector('[data-campaign-timer-block]');
    var daysEl = slide.querySelector('[data-campaign-days]');
    var hEl = slide.querySelector('[data-timer-h]');
    var mEl = slide.querySelector('[data-timer-m]');
    var sEl = slide.querySelector('[data-timer-s]');
    var dateEl = slide.querySelector('[data-campaign-end-date]');
    if (dateEl) dateEl.textContent = day + '/' + month + '/' + year;

    var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
    var timerHandle = null;

    function tick() {
      var now = new Date();
      var msLeft = endDate - now;

      if (msLeft <= 0) {
        if (timerHandle) clearInterval(timerHandle);
        slide.classList.add('hidden');
        onExpire(slide);
        return;
      }

      var todayOnly = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      var endDateOnly = new Date(year, month - 1, day);
      var calendarDaysLeft = Math.round((endDateOnly - todayOnly) / MS_PER_DAY);

      if (calendarDaysLeft <= 0) {
        if (daysBlock) daysBlock.classList.add('hidden');
        if (timerBlock) timerBlock.classList.remove('hidden');
        var totalSeconds = Math.floor(msLeft / 1000);
        if (hEl) hEl.textContent = pad(Math.floor(totalSeconds / 3600));
        if (mEl) mEl.textContent = pad(Math.floor((totalSeconds % 3600) / 60));
        if (sEl) sEl.textContent = pad(totalSeconds % 60);
        if (!timerHandle) timerHandle = setInterval(tick, 1000);
      } else {
        if (timerBlock) timerBlock.classList.add('hidden');
        if (daysBlock) daysBlock.classList.remove('hidden');
        if (daysEl) daysEl.textContent = calendarDaysLeft;
        if (timerHandle) { clearInterval(timerHandle); timerHandle = null; }
      }
    }

    tick();
  }

  function initCampaignCarousel() {
    var carousel = document.querySelector('[data-campaign-carousel]');
    if (!carousel) return;

    var viewport = carousel.querySelector('.campaign-viewport');
    var track = carousel.querySelector('[data-campaign-track]');
    var dotsWrap = carousel.querySelector('[data-campaign-dots]');
    var allSlides = Array.prototype.slice.call(carousel.querySelectorAll('.campaign-slide'));
    if (!allSlides.length) return;

    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var activeSlides = [];
    var current = 0;
    var autoplayHandle = null;
    var AUTOPLAY_MS = 6000;

    function setSlideAttrs(slide, active) {
      slide.setAttribute('aria-hidden', active ? 'false' : 'true');
      var focusables = slide.querySelectorAll('a, button, [tabindex]');
      for (var i = 0; i < focusables.length; i++) {
        focusables[i].tabIndex = active ? 0 : -1;
      }
    }

    function renderDots() {
      if (!dotsWrap) return;
      dotsWrap.innerHTML = '';
      activeSlides.forEach(function (slide, idx) {
        var dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'campaign-dot';
        dot.setAttribute('aria-label', 'Chương trình ' + (idx + 1) + ' / ' + activeSlides.length);
        dot.addEventListener('click', function () { goTo(idx); resetAutoplay(); });
        dotsWrap.appendChild(dot);
      });
    }

    function goTo(index, immediate) {
      if (!activeSlides.length) return;
      current = ((index % activeSlides.length) + activeSlides.length) % activeSlides.length;

      allSlides.forEach(function (slide) {
        setSlideAttrs(slide, activeSlides[current] === slide);
      });

      if (track) {
        track.style.transition = (reduceMotion || immediate) ? 'none' : '';
        track.style.transform = 'translateX(-' + (current * 100) + '%)';
      }

      if (dotsWrap) {
        var dots = dotsWrap.querySelectorAll('.campaign-dot');
        for (var d = 0; d < dots.length; d++) {
          dots[d].setAttribute('aria-current', d === current ? 'true' : 'false');
        }
      }
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    function stopAutoplay() {
      if (autoplayHandle) { clearInterval(autoplayHandle); autoplayHandle = null; }
    }

    function startAutoplay() {
      stopAutoplay();
      if (reduceMotion || activeSlides.length <= 1) return;
      if (document.hidden) return;
      autoplayHandle = setInterval(next, AUTOPLAY_MS);
    }

    function resetAutoplay() {
      if (activeSlides.length > 1) startAutoplay();
    }

    function refresh() {
      activeSlides = allSlides.filter(function (slide) { return !slide.classList.contains('hidden'); });

      if (!activeSlides.length) {
        carousel.classList.add('hidden');
        stopAutoplay();
        return;
      }

      var multi = activeSlides.length > 1;
      if (dotsWrap) dotsWrap.classList.toggle('hidden', !multi);

      renderDots();
      goTo(Math.min(current, activeSlides.length - 1), true);
      startAutoplay();
    }

    allSlides.forEach(function (slide) {
      attachCountdown(slide, refresh);
    });

    carousel.addEventListener('mouseenter', stopAutoplay);
    carousel.addEventListener('mouseleave', resetAutoplay);
    carousel.addEventListener('focusin', stopAutoplay);
    carousel.addEventListener('focusout', resetAutoplay);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopAutoplay(); else resetAutoplay();
    });

    if (viewport) {
      var touchStartX = 0, touchStartY = 0, touching = false;
      viewport.addEventListener('touchstart', function (e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touching = true;
        stopAutoplay();
      }, { passive: true });
      viewport.addEventListener('touchend', function (e) {
        if (!touching) return;
        touching = false;
        var dx = e.changedTouches[0].clientX - touchStartX;
        var dy = e.changedTouches[0].clientY - touchStartY;
        if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) {
          if (dx < 0) next(); else prev();
        }
        resetAutoplay();
      }, { passive: true });
    }

    refresh();
  }

  // ---------- FAQ accordion ----------
  function initFAQ() {
    var items = document.querySelectorAll('.faq-item');
    for (var i = 0; i < items.length; i++) {
      (function (item, idx) {
        var btn = item.querySelector('.faq-q');
        var icon = item.querySelector('.q-icon');
        var answer = item.querySelector('.faq-a');
        if (!btn) return;

        // Accessibility wiring so screen readers and AI agents can parse state.
        if (answer) {
          var answerId = 'faq-a-' + idx;
          answer.id = answerId;
          answer.setAttribute('role', 'region');
          btn.setAttribute('aria-controls', answerId);
        }
        btn.setAttribute('aria-expanded', 'false');

        btn.addEventListener('click', function () {
          var open = item.classList.toggle('open');
          btn.setAttribute('aria-expanded', open ? 'true' : 'false');
          if (icon) icon.textContent = open ? '−' : '+';
        });
      })(items[i], i);
    }
  }

  // ---------- Quiz ----------
  function initQuiz() {
    var intro = document.getElementById('quiz-intro');
    var active = document.getElementById('quiz-active');
    var result = document.getElementById('quiz-result');
    if (!intro || !active || !result) return;

    var stepLabel = document.getElementById('quiz-step-label');
    var progressFill = document.getElementById('quiz-progress-fill');
    var questionEl = document.getElementById('quiz-question');
    var optionsEl = document.getElementById('quiz-options');
    var resTag = document.getElementById('quiz-result-tag');
    var resName = document.getElementById('quiz-result-name');
    var resDesc = document.getElementById('quiz-result-desc');
    var resLink = document.getElementById('quiz-result-link');

    var BASE = 'https://tak12.com/info/';
    var REF = '?ref=njg2odn';
    var URLS = {
      cert: BASE + 'bang-gia-chung-chi' + REF,
      exam6: BASE + 'bang-gia-vao-6' + REF,
      exam10: BASE + 'bang-gia-vao-10' + REF,
      examdh: BASE + 'bang-gia-vao-dh' + REF,
      hoctot: BASE + 'bang-gia-hoc-tot' + REF
    };

    var questions = [
      {
        q: 'Con bạn đang học lớp mấy?',
        opts: [
          { label: 'Lớp 1–5 (Tiểu học)', value: 'primary' },
          { label: 'Lớp 6–9 (THCS)', value: 'secondary' },
          { label: 'Lớp 10–12 (THPT)', value: 'highschool' }
        ]
      },
      {
        q: 'Mục tiêu chính của con là gì?',
        opts: [
          { label: 'Lấy chứng chỉ tiếng Anh quốc tế', value: 'cert' },
          { label: 'Chuẩn bị cho kỳ thi tuyển sinh / tốt nghiệp', value: 'exam' },
          { label: 'Nâng cao điểm số và học lực', value: 'support' }
        ]
      },
      {
        q: 'Con cần cải thiện môn nào nhất?',
        opts: [
          { label: 'Tiếng Anh', value: 'english' },
          { label: 'Toán', value: 'math' },
          { label: 'Cả Toán và Tiếng Anh', value: 'both' }
        ]
      }
    ];

    var step = 0;
    var answers = [];

    function getResult() {
      var grade = answers[0], goal = answers[1], subject = answers[2];
      if (goal === 'cert') {
        if (grade === 'primary') return { tag: 'Chứng chỉ Anh', name: 'TOEFL Primary', desc: 'Khóa luyện thi TOEFL Primary dành cho học sinh tiểu học, tập trung nghe và đọc hiểu với bài tập AI cá nhân hóa.', url: URLS.cert };
        if (grade === 'secondary') return { tag: 'Chứng chỉ Anh', name: 'Luyện thi Cambridge (KET/PET)', desc: 'Chuẩn bị bài bản cho kỳ thi Cambridge KET và PET với đề mô phỏng và hướng dẫn 4 kỹ năng.', url: URLS.cert };
        return { tag: 'Chứng chỉ Anh', name: 'Luyện thi IELTS', desc: 'Chiến lược bài bản cho 4 kỹ năng IELTS với AI phân tích điểm yếu và gợi ý lộ trình cải thiện.', url: URLS.cert };
      }
      if (goal === 'exam') {
        if (grade === 'primary') return { tag: 'Ôn thi', name: 'Ôn thi vào Lớp 6', desc: 'Lộ trình ôn tập toàn diện cho kỳ thi tuyển sinh lớp 6 với đề thi thử và AI điều chỉnh độ khó.', url: URLS.exam6 };
        if (grade === 'secondary') return { tag: 'Ôn thi', name: 'Ôn thi vào Lớp 10', desc: 'Chuẩn bị kỹ lưỡng cho kỳ thi tuyển sinh THPT với 200+ đề thi thử và phân tích chi tiết.', url: URLS.exam10 };
        return { tag: 'Ôn thi', name: 'Ôn thi Tốt nghiệp THPT', desc: 'Ôn luyện trọng tâm cho kỳ thi tốt nghiệp THPT quốc gia, tập trung vào dạng bài thường gặp.', url: URLS.examdh };
      }
      if (subject === 'math') return { tag: 'Học thêm', name: 'Toán Lớp 2–12', desc: 'Hỗ trợ học Toán theo chương trình SGK mới với bài tập AI thích ứng theo trình độ.', url: URLS.hoctot };
      if (subject === 'english') return { tag: 'Học thêm', name: 'Tiếng Anh Lớp 3–12', desc: 'Nâng cao ngữ pháp, đọc hiểu và kỹ năng giao tiếp tiếng Anh cho mọi cấp lớp.', url: URLS.hoctot };
      return { tag: 'Học thêm', name: 'Toán & Tiếng Anh Lớp 2–12', desc: 'Gói học thêm cả Toán và Tiếng Anh, tiết kiệm hơn khi đăng ký cùng lúc.', url: URLS.hoctot };
    }

    function show(el) {
      intro.classList.add('hidden');
      active.classList.add('hidden');
      result.classList.add('hidden');
      el.classList.remove('hidden');
    }

    function renderStep() {
      var q = questions[step];
      if (stepLabel) stepLabel.textContent = 'Câu ' + (step + 1) + '/3';
      if (progressFill) progressFill.style.width = ((step + 1) / 3 * 100) + '%';
      if (questionEl) questionEl.textContent = q.q;
      optionsEl.innerHTML = '';
      q.opts.forEach(function (opt) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'quiz-option';
        btn.innerHTML = '<span class="radio"></span><span class="label"></span>';
        btn.querySelector('.label').textContent = opt.label;
        btn.addEventListener('click', function () { choose(opt.value); });
        optionsEl.appendChild(btn);
      });
    }

    function choose(value) {
      answers[step] = value;
      if (step >= questions.length - 1) {
        finish();
      } else {
        step += 1;
        renderStep();
      }
    }

    function finish() {
      var r = getResult();
      if (resTag) resTag.textContent = r.tag;
      if (resName) resName.textContent = r.name;
      if (resDesc) resDesc.textContent = r.desc;
      if (resLink && r.url) resLink.href = r.url;
      show(result);
      track('quiz_completed', { result: r.name, answers: answers.join(',') });
    }

    function start() {
      step = 0;
      answers = [];
      renderStep();
      show(active);
      track('quiz_started', {});
    }

    function reset() {
      step = 0;
      answers = [];
      show(intro);
    }

    var startBtn = document.getElementById('quiz-start');
    var resetBtn = document.getElementById('quiz-reset');
    if (startBtn) startBtn.addEventListener('click', start);
    if (resetBtn) resetBtn.addEventListener('click', reset);
  }
})();
