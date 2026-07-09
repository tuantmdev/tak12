// TAK12 Courses – Affiliate landing page interactions
// Converted from Claude Design "TAK12 Affiliate.dc.html" (DCLogic) to vanilla JS.

(function () {
  'use strict';

  var COUPON = 'DSMANHTUAN';

  document.addEventListener('DOMContentLoaded', function () {
    initCopyButtons();
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

  // ---------- FAQ accordion ----------
  function initFAQ() {
    var items = document.querySelectorAll('.faq-item');
    for (var i = 0; i < items.length; i++) {
      (function (item) {
        var btn = item.querySelector('.faq-q');
        var icon = item.querySelector('.q-icon');
        if (!btn) return;
        btn.addEventListener('click', function () {
          var open = item.classList.toggle('open');
          if (icon) icon.textContent = open ? '−' : '+';
        });
      })(items[i]);
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
        if (grade === 'primary') return { tag: 'Chứng chỉ Anh', name: 'TOEFL Primary', desc: 'Khóa luyện thi TOEFL Primary dành cho học sinh tiểu học, tập trung nghe và đọc hiểu với bài tập AI cá nhân hóa.' };
        if (grade === 'secondary') return { tag: 'Chứng chỉ Anh', name: 'Luyện thi Cambridge (KET/PET)', desc: 'Chuẩn bị bài bản cho kỳ thi Cambridge KET và PET với đề mô phỏng và hướng dẫn 4 kỹ năng.' };
        return { tag: 'Chứng chỉ Anh', name: 'Luyện thi IELTS', desc: 'Chiến lược bài bản cho 4 kỹ năng IELTS với AI phân tích điểm yếu và gợi ý lộ trình cải thiện.' };
      }
      if (goal === 'exam') {
        if (grade === 'primary') return { tag: 'Ôn thi', name: 'Ôn thi vào Lớp 6', desc: 'Lộ trình ôn tập toàn diện cho kỳ thi tuyển sinh lớp 6 với đề thi thử và AI điều chỉnh độ khó.' };
        if (grade === 'secondary') return { tag: 'Ôn thi', name: 'Ôn thi vào Lớp 10', desc: 'Chuẩn bị kỹ lưỡng cho kỳ thi tuyển sinh THPT với 200+ đề thi thử và phân tích chi tiết.' };
        return { tag: 'Ôn thi', name: 'Ôn thi Tốt nghiệp THPT', desc: 'Ôn luyện trọng tâm cho kỳ thi tốt nghiệp THPT quốc gia, tập trung vào dạng bài thường gặp.' };
      }
      if (subject === 'math') return { tag: 'Học thêm', name: 'Toán Lớp 1–12', desc: 'Hỗ trợ học Toán theo chương trình SGK mới với bài tập AI thích ứng theo trình độ.' };
      if (subject === 'english') return { tag: 'Học thêm', name: 'Tiếng Anh Lớp 1–12', desc: 'Nâng cao ngữ pháp, đọc hiểu và kỹ năng giao tiếp tiếng Anh cho mọi cấp lớp.' };
      return { tag: 'Học thêm', name: 'Toán & Tiếng Anh Lớp 1–12', desc: 'Gói học thêm cả Toán và Tiếng Anh, tiết kiệm hơn khi đăng ký cùng lúc với mã DSMANHTUAN.' };
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
