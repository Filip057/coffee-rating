<script type="module">
import { api, ApiError } from '/static/js/api.js';
import Config from '/static/js/config.js';

const form = document.getElementById('createGroupForm');
const nameInput = document.getElementById('groupName');
const descriptionInput = document.getElementById('groupDescription');
const privateCheckbox = document.getElementById('privateGroup');

const errorBox = document.getElementById('groupFormError');
const nameError = document.getElementById('groupNameError');
const submitBtn = document.getElementById('createGroupBtn');

// Checkbox toggle
privateCheckbox.addEventListener('click', () => {
    const box = privateCheckbox.querySelector('.checkbox');
    const checked = box.classList.toggle('checked');
    privateCheckbox.setAttribute('aria-checked', checked);
});

privateCheckbox.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        privateCheckbox.click();
    }
});

function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.add('visible');
    }

function setLoading(loading) {
    submitBtn.classList.toggle('btn-loading', loading);
    submitBtn.disabled = loading;
    }

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    errorBox.classList.remove('visible');
    nameError.classList.remove('visible');
    nameInput.classList.remove('input-error');

    const name = nameInput.value.trim();
    const description = descriptionInput.value.trim();
    const isPrivate = privateCheckbox
        .querySelector('.checkbox')
        .classList.contains('checked');

    if (!name) {
        nameInput.classList.add('input-error');
        nameError.textContent = 'Zadejte název skupiny';
        nameError.classList.add('visible');
        return;
    }

    setLoading(true);

    try {
        const group = await api.groups.create({
            name,
            description,
            is_private: isPrivate
        });

        // Přesměrování na detail skupiny
        window.location.href = Config.ROUTES.GROUP_DETAIL(group.id);

    } catch (error) {
        setLoading(false);

        if (error instanceof ApiError) {
            if (error.status === 400) {
                showError(error.message || 'Neplatná data');
            } else if (error.status === 401) {
                showError('Přihlášení vypršelo');
            } else {
                showError('Nepodařilo se vytvořit skupinu');
            }
        } else {
            showError('Neočekávaná chyba');
            console.error(error);
        }
    }
});
</script>
