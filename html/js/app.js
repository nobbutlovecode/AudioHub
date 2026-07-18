/**
 * AUDIOHUB - CENTRAL LOGIC (ENTERPRISE PATTERN)
 */

// --- 1. TỰ ĐỘNG NHÚNG CÁC COMPONENTS (MODALS) ---
async function loadComponents() {
    const components = ['about.html', 'donate.html', 'clist.html'];
    const injector = document.getElementById('modals-injector');
    
    for (let file of components) {
        try {
            const res = await fetch(`/html/components/${file}`);
            const html = await res.text();
            injector.insertAdjacentHTML('beforeend', html);
        } catch (error) {
            console.error(`Lỗi khi load component ${file}:`, error);
        }
    }
}

// Khởi chạy khi DOM tải xong
document.addEventListener('DOMContentLoaded', loadComponents);

// --- 2. HỆ THỐNG MODAL (Mở / Đóng) ---
function openModal(id) {
    const modal = document.getElementById(id);
    if(modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        const content = modal.querySelector('.modal-content');
        if (content) {
            content.classList.remove('animate-modal-in');
            void content.offsetWidth; // force reflow để animation chạy lại mỗi lần mở
            content.classList.add('animate-modal-in');
        }
        if(id === 'modal-clist') renderCList(); // Cập nhật list trước khi mở
    }
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if(modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

// Đóng khi click ngoài viền
window.onclick = function(event) {
    if (event.target.classList.contains('modal-overlay')) {
        closeModal(event.target.id);
    }
}

// --- 3. HỆ THỐNG IN-MEMORY C-LIST (VERSUS STYLE) ---
// (Theme Cyan/Gold + độ sáng màu được quản lý tập trung trong index.html)
// Biến này lưu trên RAM trình duyệt. Reset web = mất trắng.
let cListMemory = []; 

function updateCListCount() {
    const badge = document.getElementById('clist-count');
    badge.innerText = cListMemory.length;
    
    // Hiệu ứng "Pulse" khi thêm đồ
    badge.classList.add('scale-150');
    setTimeout(() => badge.classList.remove('scale-150'), 200);
}

function addToCList(itemJsonBase64) {
    // Giải mã data an toàn
    const item = JSON.parse(decodeURIComponent(escape(atob(itemJsonBase64))));
    
    // Check trùng lặp
    if (!cListMemory.find(i => i.id === item.id)) {
        cListMemory.push(item);
        updateCListCount();
    }
}

function removeFromCList(id) {
    cListMemory = cListMemory.filter(i => i.id !== id);
    updateCListCount();
    renderCList();
}

function renderCList() {
    const container = document.getElementById('clist-items');
    if(!container) return;

    if (cListMemory.length === 0) {
        container.innerHTML = `<div class="text-center text-[var(--text-sub)] mt-12 italic">Your list is empty. Search above to add devices.</div>`;
        return;
    }

    container.innerHTML = cListMemory.map(item => `
        <div class="bg-[var(--bg-body)] p-3 border border-[var(--b-color)] rounded-lg flex justify-between items-center group transition-colors hover:border-[var(--primary)]">
            <div>
                <div class="text-[10px] text-[var(--primary)] font-bold uppercase mb-0.5">${item.category}</div>
                <div class="font-bold text-sm text-[var(--text-main)]">${item.model_name}</div>
                <div class="text-xs text-[var(--text-sub)]">${item.brand}</div>
            </div>
            <button onclick="removeFromCList(${item.id})" class="text-red-500 hover:text-red-400 p-2 opacity-50 hover:opacity-100 transition-all">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        </div>
    `).join('');
}

// --- 5. TÌM KIẾM (AUTOCOMPLETE API) ---
const searchInput = document.getElementById('searchInput');
const searchDropdown = document.getElementById('searchDropdown');
let searchTimeout;

if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchTimeout);
        
        if(query.length < 2) {
            searchDropdown.classList.add('hidden');
            return;
        }

        // Debounce 300ms
        searchTimeout = setTimeout(async () => {
            try {
                // Đảm bảo API này đã có trên Backend FastAPI
                const res = await fetch(`/api/v1/search?q=${query}`);
                const result = await res.json();
                
                if(result.status === "success" && result.data.length > 0) {
                    searchDropdown.innerHTML = result.data.map(item => {
                        // Mã hóa an toàn tránh lỗi dấu ngoặc kép HTML
                        const encodedItem = btoa(unescape(encodeURIComponent(JSON.stringify(item))));
                        return `
                            <li class="p-4 border-b border-[var(--b-color)] hover:bg-[#1A1A1A] cursor-pointer flex justify-between items-center transition-colors"
                                onclick="addToCList('${encodedItem}'); document.getElementById('searchInput').value=''; document.getElementById('searchDropdown').classList.add('hidden');">
                                <div>
                                    <div class="font-bold text-[var(--text-main)]">${item.model_name}</div>
                                    <div class="text-xs text-[var(--text-sub)] font-normal mt-0.5">by ${item.brand} • <span style="color:var(--primary)">${new Intl.NumberFormat('vi-VN', {style: 'currency', currency: 'VND'}).format(item.price_vnd)}</span></div>
                                </div>
                                <span class="text-[10px] px-2 py-1 bg-[var(--b-color)] text-[var(--primary)] rounded font-bold transition-transform hover:scale-105">+ ADD C-LIST</span>
                            </li>
                        `;
                    }).join('');
                    searchDropdown.classList.remove('hidden');
                } else {
                    searchDropdown.innerHTML = `<li class="p-4 text-sm text-[var(--text-sub)] italic">No devices found matching "${query}".</li>`;
                    searchDropdown.classList.remove('hidden');
                }
            } catch(err) {
                console.error("Lỗi gọi API tìm kiếm:", err);
            }
        }, 300);
    });

    // Ẩn search khi click ra ngoài
    document.addEventListener('click', (e) => {
        if(!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            searchDropdown.classList.add('hidden');
        }
    });
}

// =================================================================
// TÍNH NĂNG C-LIST: RUN COMPARISON ALGORITHM
// Sử dụng window. để đảm bảo hàm là Global (Toàn cục), độc lập với
// việc #searchInput có tồn tại hay không.
// =================================================================
window.runCList = function() {
    // 1. Kiểm tra xem C-List có đang trống không?
    if (cListMemory.length === 0) {
        alert("⚠️ C-List của bạn đang trống! Hãy dùng thanh Tìm kiếm ở ngoài để thêm sản phẩm vào trước nhé.");
        return;
    }

    // 2. Đóng Modal C-List lại
    closeModal('modal-clist');

    // 3. Gọi lại hàm extractAndSearch (đã định nghĩa trong index.html) để chạy MCDM Engine
    if (typeof extractAndSearch === "function") {
        extractAndSearch();
    } else {
        console.error("Không tìm thấy hàm extractAndSearch()");
        return;
    }

    // 4. Cuộn màn hình mượt mà xuống khu vực Bảng Kết quả
    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};