// TAK12 Courses – Affiliate landing page interactions
// Converted from Claude Design "TAK12 Affiliate.dc.html" (DCLogic) to vanilla JS.

(function () {
  'use strict';

  var COUPON = 'DSMANHTUAN';

  document.addEventListener('DOMContentLoaded', function () {
    initCopyButtons();
    initHeroMotion();
    initFAQ();
    initQuiz();
  });

  // ---------- PostHog helper ----------
  function track(event, props) {
    try {
      if (window.posthog && typeof window.posthog.capture === 'function') {
        window.posthog.capture(event, props || {});
      }
    } catch (e) { /* analytics must never break the page */ }
  }

  // ---------- Copy coupon + toast ----------
  function initCopyButtons() {
    var toast = document.getElementById('toast');
    var toastTimer;

    function showToast() {
      if (!toast) return;
      toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 2500);
    }

    function copyCoupon(btn) {
      var restore = null;
      if (btn && btn.classList.contains('final-code') === false) {
        restore = btn.textContent;
        btn.textContent = 'Đã sao chép! ✓';
        setTimeout(function () { if (restore !== null) btn.textContent = restore; }, 2500);
      }
      var done = function () { showToast(); track('promo_code_copied', { code: COUPON }); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(COUPON).then(done, function () { fallbackCopy(COUPON); done(); });
      } else {
        fallbackCopy(COUPON);
        done();
      }
    }

    function fallbackCopy(text) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'absolute';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (e) { /* noop */ }
      document.body.removeChild(ta);
    }

    var buttons = document.querySelectorAll('[data-copy]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function () { copyCoupon(this); });
    }

    // CTA click tracking (course/final/quiz links to TAK12)
    var ctas = document.querySelectorAll('[data-cta]');
    for (var j = 0; j < ctas.length; j++) {
      ctas[j].addEventListener('click', function () {
        track('cta_click', { cta: this.getAttribute('data-cta') });
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
      return { tag: 'Học thêm', name: 'Toán & Tiếng Anh Lớp 2–12', desc: 'Gói học thêm cả Toán và Tiếng Anh, tiết kiệm hơn khi đăng ký cùng lúc với mã DSMANHTUAN.', url: URLS.hoctot };
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
