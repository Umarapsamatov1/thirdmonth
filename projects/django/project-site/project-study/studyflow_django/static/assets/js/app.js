
const StudyFlow = (() => {
  const translations = {
    uz: {
      nav_home: "Asosiy", nav_courses: "Kurslar", nav_languages: "Tillar", nav_about: "Biz haqimizda", nav_contact: "Aloqa",
      nav_login: "Kirish", nav_register: "Ro‘yxatdan o‘tish", nav_dashboard: "Kabinet", nav_logout: "Chiqish",
      footer_text: "Bilim olishni sodda, chiroyli va natijador qiladigan zamonaviy o‘quv platformasi.",
      footer_pages: "Sahifalar", footer_account: "Hisob", footer_help: "Yordam", footer_rights: "Barcha huquqlar himoyalangan.",
      hero_eyebrow: "Yangi avlod ta’lim platformasi", hero_title_1: "Kelajagingizni", hero_title_2: "bilim bilan quring",
      hero_desc: "Til, dasturlash va zamonaviy kasblarni qisqa darslar, amaliy topshiriqlar va individual rivojlanish yo‘li orqali o‘rganing.",
      hero_courses: "Kurslarni ko‘rish", hero_start: "Bepul boshlash",
      stats_title: "O‘qishni aqlli, qulay va natijador qilamiz", stats_desc: "StudyFlow sizga aniq reja, amaliy mashqlar va kundalik progress orqali maqsadingizga tezroq yetishga yordam beradi.",
      lang_saved: "Sayt tili saqlandi", register_success: "Ro‘yxatdan muvaffaqiyatli o‘tdingiz!", login_success: "Xush kelibsiz!", login_error: "Email yoki parol noto‘g‘ri.",
      email_opening: "Email ilovasi ochilmoqda...", form_required: "Barcha majburiy maydonlarni to‘ldiring.", password_mismatch: "Parollar mos kelmadi.", email_exists: "Bu email bilan foydalanuvchi mavjud.", logout_done: "Hisobdan chiqildi."
    },
    ru: {
      nav_home: "Главная", nav_courses: "Курсы", nav_languages: "Языки", nav_about: "О нас", nav_contact: "Контакты",
      nav_login: "Войти", nav_register: "Регистрация", nav_dashboard: "Кабинет", nav_logout: "Выйти",
      footer_text: "Современная учебная платформа, которая делает обучение понятным, красивым и результативным.",
      footer_pages: "Страницы", footer_account: "Аккаунт", footer_help: "Помощь", footer_rights: "Все права защищены.",
      hero_eyebrow: "Образовательная платформа нового поколения", hero_title_1: "Стройте будущее", hero_title_2: "с помощью знаний",
      hero_desc: "Изучайте языки, программирование и современные профессии через короткие уроки, практику и персональный план развития.",
      hero_courses: "Смотреть курсы", hero_start: "Начать бесплатно",
      stats_title: "Делаем обучение умным, удобным и результативным", stats_desc: "StudyFlow помогает быстрее достигать целей благодаря четкому плану, практике и ежедневному прогрессу.",
      lang_saved: "Язык сайта сохранён", register_success: "Регистрация прошла успешно!", login_success: "Добро пожаловать!", login_error: "Неверный email или пароль.",
      email_opening: "Открываем почтовое приложение...", form_required: "Заполните все обязательные поля.", password_mismatch: "Пароли не совпадают.", email_exists: "Пользователь с таким email уже существует.", logout_done: "Вы вышли из аккаунта."
    },
    en: {
      nav_home: "Home", nav_courses: "Courses", nav_languages: "Languages", nav_about: "About", nav_contact: "Contact",
      nav_login: "Login", nav_register: "Register", nav_dashboard: "Dashboard", nav_logout: "Logout",
      footer_text: "A modern learning platform that makes education clear, beautiful, and effective.",
      footer_pages: "Pages", footer_account: "Account", footer_help: "Help", footer_rights: "All rights reserved.",
      hero_eyebrow: "Next-generation learning platform", hero_title_1: "Build your future", hero_title_2: "with knowledge",
      hero_desc: "Learn languages, programming, and modern careers through short lessons, practical tasks, and a personalized growth path.",
      hero_courses: "Explore courses", hero_start: "Start free",
      stats_title: "Learning made smarter, easier, and more effective", stats_desc: "StudyFlow helps you reach your goals faster with a clear plan, practical exercises, and daily progress.",
      lang_saved: "Site language saved", register_success: "Registration successful!", login_success: "Welcome back!", login_error: "Incorrect email or password.",
      email_opening: "Opening your email app...", form_required: "Please fill in all required fields.", password_mismatch: "Passwords do not match.", email_exists: "An account with this email already exists.", logout_done: "You have been logged out."
    }
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const getLang = () => localStorage.getItem('studyflow_lang') || 'uz';
  const t = (key) => translations[getLang()]?.[key] || translations.uz[key] || key;

  function toast(message) {
    const el = $('#toast');
    if (!el) return;
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
  }

  function applyLanguage(lang) {
    localStorage.setItem('studyflow_lang', lang);
    document.documentElement.lang = lang;
    $$('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      if (translations[lang]?.[key]) el.textContent = translations[lang][key];
    });
    $$('.lang-select').forEach(select => select.value = lang);
  }

  function initNavigation() {
    const toggle = $('.menu-toggle');
    const nav = $('.nav-links');
    toggle?.addEventListener('click', () => nav?.classList.toggle('open'));
    $$('.nav-link').forEach(link => link.addEventListener('click', () => nav?.classList.remove('open')));

    $$('.lang-select').forEach(select => select.addEventListener('change', e => {
      applyLanguage(e.target.value);
      toast(t('lang_saved'));
    }));

    const path = location.pathname.split('/').pop() || 'index.html';
    $$('.nav-link').forEach(link => {
      if (link.getAttribute('href') === path) link.classList.add('active');
    });
  }

  // Authentication is provided by Django sessions, never browser localStorage.
  function updateAuthUI() {
    const authenticated = document.body.dataset.authenticated === 'true';
    $$('[data-auth="guest"]').forEach(el => el.classList.toggle('hidden', authenticated));
    $$('[data-auth="user"]').forEach(el => el.classList.toggle('hidden', !authenticated));
    $$('[data-user-initial]').forEach(el => {
      const name = $('[data-user-name]')?.textContent?.trim() || 'T';
      el.textContent = name.charAt(0).toUpperCase();
    });
  }

  function initPasswordToggles() {
    $$('.password-toggle').forEach(btn => btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input');
      input.type = input.type === 'password' ? 'text' : 'password';
      btn.textContent = input.type === 'password' ? '👁' : '🙈';
    }));
  }

  function initContactForm() {
    const form = $('#contactForm');
    if (!form) return;
    form.addEventListener('submit', e => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      const status = $('#contactStatus');
      if (!data.name || !data.email || !data.message) {
        status.textContent = t('form_required'); status.className = 'form-status error'; return;
      }
      const subject = encodeURIComponent(data.subject || `StudyFlow: ${data.name}`);
      const body = encodeURIComponent(`Ism: ${data.name}\nEmail: ${data.email}\n\n${data.message}`);
      status.textContent = t('email_opening'); status.className = 'form-status ok';
      window.location.href = `mailto:hello@studyflow.uz?subject=${subject}&body=${body}`;
    });
  }

  // Newsletter forms submit normally to Django and preserve CSRF protection.

  function initCourseFilters() {
    const cards = $$('.course-card[data-category]');
    if (!cards.length) return;
    const buttons = $$('.filter-btn');
    const search = $('#courseSearch');
    let current = 'all';
    function run() {
      const q = (search?.value || '').toLowerCase().trim();
      cards.forEach(card => {
        const categoryMatch = current === 'all' || card.dataset.category === current;
        const textMatch = card.textContent.toLowerCase().includes(q);
        card.classList.toggle('hidden', !(categoryMatch && textMatch));
      });
    }
    buttons.forEach(btn => btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active'); current = btn.dataset.filter; run();
    }));
    search?.addEventListener('input', run);
  }

  function initLanguageCards() {
    $$('[data-set-lang]').forEach(btn => btn.addEventListener('click', () => {
      applyLanguage(btn.dataset.setLang); toast(t('lang_saved'));
    }));
  }

  function initYear() {
    $$('[data-year]').forEach(el => el.textContent = new Date().getFullYear());
  }

  function init() {
    applyLanguage(getLang());
    initNavigation(); updateAuthUI();
    initPasswordToggles(); initContactForm(); initCourseFilters(); initLanguageCards(); initYear();
  }

  return { init, toast };
})();

document.addEventListener('DOMContentLoaded', StudyFlow.init);
