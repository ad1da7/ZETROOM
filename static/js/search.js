const searchInput = document.getElementById('search-input');
const roomsGrid = document.getElementById('rooms-grid');
const cards = document.querySelectorAll('.room-card');

if (searchInput && roomsGrid) {
    document.getElementById('search-form').onsubmit = (e) => e.preventDefault();

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();

        cards.forEach(card => {
            const name = card.getAttribute('data-name');
            if (name.includes(query)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });
}