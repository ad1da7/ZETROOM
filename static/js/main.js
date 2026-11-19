document.addEventListener("DOMContentLoaded", () => {
    // 1. Живой поиск в лобби активных комнат
    const liveSearchInput = document.getElementById("live-room-search") || document.querySelector('input[name="q"]');
    const roomCards = document.querySelectorAll(".room-card");

    if (liveSearchInput && roomCards.length > 0) {
        liveSearchInput.addEventListener("input", (event) => {
            const query = event.target.value.toLowerCase().trim();

            roomCards.forEach((card) => {
                const titleEl = card.querySelector(".room-title");
                const roomName = (card.getAttribute("data-room-name") || (titleEl ? titleEl.textContent : "")).toLowerCase();

                if (roomName.includes(query)) {
                    card.style.display = "flex";
                } else {
                    card.style.display = "none";
                }
            });
        });
    }

    // 2. Предпросмотр аватарки в личном кабинете
    const avatarInput = document.querySelector('input[type="file"][name="avatar"]') || document.getElementById("id_avatar");
    const avatarPreviewContainer = document.getElementById("avatar-preview-wrapper");

    if (avatarInput && avatarPreviewContainer) {
        avatarInput.addEventListener("change", (event) => {
            const file = event.target.files[0];
            if (!file) return;
            if (!file.type.startsWith("image/")) {
                alert("Пожалуйста, выберите файл изображения (JPG, PNG, WEBP).");
                avatarInput.value = "";
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                let imgElement = document.getElementById("avatar-preview-img");
                if (!imgElement) {
                    avatarPreviewContainer.innerHTML = "";
                    imgElement = document.createElement("img");
                    imgElement.id = "avatar-preview-img";
                    imgElement.alt = "Предпросмотр аватара";
                    imgElement.className = "avatar-large";
                    avatarPreviewContainer.appendChild(imgElement);
                }
                imgElement.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    // 3. Модальное окно создания комнаты на главной странице
    const openCreateBtn = document.getElementById("openCreateModalBtn") || document.querySelector("button.btn-create[type='button']");
    const createModal = document.getElementById("createRoomModal") || document.querySelector(".modal-overlay");
    const closeCreateBtn = document.getElementById("closeCreateModalBtn") || document.querySelector(".modal-close");

    if (openCreateBtn && createModal) {
        openCreateBtn.addEventListener("click", (e) => {
            e.preventDefault();
            createModal.style.display = "flex";
        });
    }

    if (closeCreateBtn && createModal) {
        closeCreateBtn.addEventListener("click", () => {
            createModal.style.display = "none";
        });
    }

    if (createModal) {
        createModal.addEventListener("click", (e) => {
            if (e.target === createModal) {
                createModal.style.display = "none";
            }
        });
    }
});
