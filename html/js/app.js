/**
 * AUDIOHUB — CENTRAL LOGIC (v2.5 — Clean Light & Black Gold)
 */

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value ?? '';
    return div.innerHTML;
}

// 1. TỰ ĐỘNG NHÚNG CÁC MODALS
async function loadComponents() {
    const components = ['about.html', 'donate.html', 'clist.html'];
    const injector = document.getElementById('modals-injector');
    if (!injector) return;

    const results = await Promise.all(
        components.map(async (file) => {
            try {
                const res = await fetch(`/html/components/${file}`);
                return await res.text();
            } catch (error) {
                console.error(`Lỗi khi load component ${file}:`, error);
                return '';
            }
        })
    );
    injector.insertAdjacentHTML('beforeend', results.join(''));
}

document.addEventListener('DOMContentLoaded', loadComponents);

// 2. HỆ THỐNG MODAL (Mở / Đóng)
function openModal(id) {
    const modal = document.getElementById(id);
    if(modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        const content = modal.querySelector('.modal-content');
        if (content) {
            content.classList.remove('animate-modal-in');
            void content.offsetWidth;
            content.classList.add('animate-modal-in');
        }
        if(id === 'modal-clist') renderCList();
    }
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if(modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal-overlay')) {
        closeModal(event.target.id);
    }
};

// 3. C-LIST PERSISTENCE VỚI LOCALSTORAGE
let cListMemory = [];

function loadCListFromStorage() {
    try {
        const saved = localStorage.getItem('audiohub-clist');
        if (saved) {
            cListMemory = JSON.parse(saved);
        }
    } catch (e) {
        console.warn('Lỗi đọc C-List từ localStorage:', e);
        cListMemory = [];
    }
}

function saveCListToStorage() {
    try {
        localStorage.setItem('audiohub-clist', JSON.stringify(cListMemory));
    } catch (e) {
        console.warn('Lỗi lưu C-List vào localStorage:', e);
    }
}

loadCListFromStorage();

function updateCListCount() {
    const badge = document.getElementById('clist-count');
    if (!badge) return;
    badge.innerText = cListMemory.length;
    badge.classList.add('scale-125');
    setTimeout(() => badge.classList.remove('scale-125'), 200);
}

function addToCList(itemJsonBase64) {
    const item = JSON.parse(decodeURIComponent(escape(atob(itemJsonBase64))));
    if (!cListMemory.find(i => i.id === item.id)) {
        cListMemory.push(item);
        saveCListToStorage();
        updateCListCount();
    }
}

function removeFromCList(id) {
    cListMemory = cListMemory.filter(i => i.id !== id);
    saveCListToStorage();
    updateCListCount();
    renderCList();
}

function clearCList() {
    cListMemory = [];
    saveCListToStorage();
    updateCListCount();
    renderCList();
}

function renderCList() {
    const container = document.getElementById('clist-items');
    if(!container) return;

    if (cListMemory.length === 0) {
        container.innerHTML = `<div class="text-center text-[var(--text-sub)] py-12 text-xs italic">C-List đang trống. Hãy tìm kiếm ở ngoài để thêm thiết bị so sánh.</div>`;
        return;
    }

    container.innerHTML = cListMemory.map(item => `
        <div class="bg-[var(--surface-alt)] p-3.5 border border-[var(--b-color)] rounded-xl flex justify-between items-center group transition-colors hover:border-[var(--primary)]">
            <div>
                <div class="text-[10px] text-[var(--primary)] font-bold uppercase tracking-wider mb-0.5">${escapeHtml(item.category || '')}</div>
                <div class="font-bold text-sm text-[var(--text-heading)]">${escapeHtml(item.model_name)}</div>
                <div class="text-xs text-[var(--text-sub)]">${escapeHtml(item.brand || '')}</div>
            </div>
            <button onclick="removeFromCList(${item.id})" class="text-red-500 hover:text-red-400 p-2 opacity-60 hover:opacity-100 transition-opacity" title="Xóa khỏi danh sách">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        </div>
    `).join('');
}

// 4. TÌM KIẾM SẢN PHẨM AUTOCOMPLETE (DEBOUNCE 250ms)
const searchInput = document.getElementById('searchInput');
const searchDropdown = document.getElementById('searchDropdown');
let searchTimeout;
const vndFormatter = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' });

if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchTimeout);
        
        if(query.length < 2) {
            searchDropdown.classList.add('hidden');
            return;
        }

        searchTimeout = setTimeout(async () => {
            try {
                const res = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}`);
                const result = await res.json();
                
                if(result.status === "success" && result.data.length > 0) {
                    searchDropdown.innerHTML = result.data.map(item => {
                        const encodedItem = btoa(unescape(encodeURIComponent(JSON.stringify(item))));
                        return `
                            <li class="p-3.5 border-b border-[var(--b-color)] hover:bg-[var(--surface-alt)] cursor-pointer flex justify-between items-center transition-colors text-xs"
                                onclick="addToCList('${encodedItem}'); document.getElementById('searchInput').value=''; document.getElementById('searchDropdown').classList.add('hidden');">
                                <div>
                                    <div class="font-bold text-[var(--text-heading)]">${escapeHtml(item.model_name)}</div>
                                    <div class="text-[11px] text-[var(--text-sub)] mt-0.5">${escapeHtml(item.brand)} · <span class="text-[var(--primary)] font-bold">${vndFormatter.format(item.price_vnd)}</span></div>
                                </div>
                                <span class="text-[10px] px-3 py-1 btn-secondary !rounded-full font-bold">+ Thêm</span>
                            </li>
                        `;
                    }).join('');
                    searchDropdown.classList.remove('hidden');
                } else {
                    searchDropdown.innerHTML = `<li class="p-4 text-xs text-[var(--text-sub)] italic">Không tìm thấy thiết bị nào khớp với "${escapeHtml(query)}".</li>`;
                    searchDropdown.classList.remove('hidden');
                }
            } catch(err) {
                console.error("Lỗi gọi API tìm kiếm:", err);
            }
        }, 250);
    });

    document.addEventListener('click', (e) => {
        if(!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            searchDropdown.classList.add('hidden');
        }
    });
}

// 5. C-LIST RUN COMPARISON
window.runCList = function() {
    if (cListMemory.length === 0) {
        alert("⚠️ Danh sách C-List của bạn đang trống! Hãy tìm kiếm và thêm sản phẩm trước.");
        return;
    }

    const soundSelect = document.getElementById('sound1');
    if (soundSelect && !soundSelect.value) {
        alert("⚠️ Vui lòng chọn ít nhất 1 gu âm học (Favorite Sound Signature) ở bảng điều khiển trước!");
        closeModal('modal-clist');
        soundSelect.focus();
        soundSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
    }

    closeModal('modal-clist');

    if (typeof extractAndSearch === "function") {
        extractAndSearch();
    }

    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    updateCListCount();
});
