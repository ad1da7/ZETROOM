/* --- ПОДКЛЮЧЕНИЕ ШРИФТОВ --- */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

@font-face {
    font-family: 'Pricedown';
    src: url('https://fonts.cdnfonts.com/css/pricedown') format('woff2');
    font-weight: normal;
    font-style: normal;
}

/* --- ГЛОБАЛЬНЫЕ СТИЛИ --- */
body, html {
    font-family: 'Montserrat', sans-serif !important;
}

/* Все заголовки, кнопки и акцентные элементы становятся Pricedown */
h1, h2, h3, h4, h5, h6,
.brand-logo,
.auth-header h1,
.hero-title,
.room-title,
.section-label,
.btn-submit,
.btn-leave,
.btn-share,
.btn-copy,
.sync-badge,
.message-author,
.nav-btn {
    font-family: 'Pricedown', 'Impact', sans-serif !important;
    font-weight: normal !important;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* Чтобы все инпуты (поля ввода) тоже были Montserrat */
input, textarea, select, button {
    font-family: 'Montserrat', sans-serif !important;
}