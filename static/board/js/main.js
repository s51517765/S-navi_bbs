function submitComment(event, postId) {
    event.preventDefault();

    const form = document.getElementById(`comment-form-${postId}`);
    const formData = new FormData(form);
    const inputField = document.getElementById(`comment-input-${postId}`);

    fetch(`/post/${postId}/comment/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                const list = document.getElementById(`comment-list-${postId}`);

                // 名前・ID・ボタンを含める
                const newComment = `
                <div class="bg-white p-2 rounded mb-2 small shadow-sm">
                <div class="d-flex justify-content-between border-bottom mb-1 pb-1">
                    <strong class="text-info">${data.author_display_name}</strong>
                    <span class="text-muted" style="font-size: 0.7rem;">${data.created_at}</span>
                </div>
                <div class="text-dark mb-1">${data.content}</div>
                
                <!-- アイコンと数字の部分 -->
                <div class="mt-1 d-flex gap-2" style="font-size: 0.7rem;">
                    <button type="button" id="comment-good-btn-${data.comment_id}" 
                            onclick="sendCommentReaction(${data.comment_id}, 'good')" 
                            class="btn btn-link btn-sm text-decoration-none p-0 text-muted">
                        👍 <span id="comment-good-count-${data.comment_id}">0</span>
                    </button>
                    <button type="button" id="comment-bad-btn-${data.comment_id}" 
                            onclick="sendCommentReaction(${data.comment_id}, 'bad')" 
                            class="btn btn-link btn-sm text-decoration-none p-0 text-muted">
                        👎 <span id="comment-bad-count-${data.comment_id}">0</span>
                    </button>
                </div>
            </div>`;
                list.insertAdjacentHTML('beforeend', newComment);
                inputField.value = '';
            }
        });
}

// いいね(good,bad)処理
function sendPostReaction(postId, type) {
    fetch(`/post/${postId}/eval/${type}/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(response => {
            // もし自分自身の投稿などで 403 エラーが返ってきたら
            if (!response.ok) {
                if (response.status === 403) {
                    showToast("自分の投稿にはリアクションできません"); // トースト表示
                }
                // エラー時はここで処理を中断させる
                throw new Error('Action not allowed');
            }
            return response.json();
        })
        .then(data => {
            // ここに到達するのは「成功したとき」だけ
            document.getElementById(`post-good-count-${postId}`).innerText = data.good_count;
            document.getElementById(`post-bad-count-${postId}`).innerText = data.bad_count;

            // スコアと見た目の更新
            const scoreElement = document.getElementById(`post-score-${postId}`);
            if (scoreElement) {
                scoreElement.innerText = `合計: ${data.point} pt`;
            }
            updatePostButtonVisuals(postId, data.status, type, data.point);
        })
        .catch(error => {
            console.log("Reaction error:", error.message);
        });
}

// コメントに対するリアクション
function sendCommentReaction(commentId, type) {
    fetch(`/comment/${commentId}/reaction/${type}/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(response => {
            if (response.status === 403) {
                showToast("自分のコメントにはリアクションできません");
                throw new Error('Mine'); // ここで中断
            }
            return response.json();
        })
        .then(data => {
                // IDを使って要素を探す
                const goodSpan = document.getElementById(`comment-good-count-${commentId}`);
                const badSpan = document.getElementById(`comment-bad-count-${commentId}`);
                const goodBtn = document.getElementById(`comment-good-btn-${commentId}`);
                const badBtn = document.getElementById(`comment-bad-btn-${commentId}`);

                // 数字だけを更新
                if (goodSpan) goodSpan.innerText = data.good_count;
                if (badSpan) badSpan.innerText = data.bad_count;

                // 見た目のリセット（一旦両方をグレーにする）
                [goodBtn, badBtn].forEach(btn => {
                    if (btn) {
                        btn.classList.remove('text-primary', 'fw-bold');
                        btn.classList.add('text-muted');
                    }
                });

                // 選択された方に色をつける
                if (data.status === 'added' || data.status === 'switched') {
                    const targetBtn = (type === 'good') ? goodBtn : badBtn;
                    if (targetBtn) {
                        targetBtn.classList.replace('text-muted', 'text-primary');
                        targetBtn.classList.add('fw-bold');
                    }
                }
        });
}

function updatePostButtonVisuals(postId, status, type, point) {
    const gBtn = document.getElementById(`post-good-btn-${postId}`);
    const bBtn = document.getElementById(`post-bad-btn-${postId}`);
    const gIcon = document.getElementById(`post-good-icon-${postId}`);
    const bIcon = document.getElementById(`post-bad-icon-${postId}`);
    const sIcon = document.getElementById(`post-score-${postId}`);

    // いったんリセット（枠線のみ）
    gBtn.classList.replace('btn-success', 'btn-outline-success');
    gBtn.classList.remove('text-white');
    gIcon.classList.replace('bi-hand-thumbs-up-fill', 'bi-hand-thumbs-up');

    bBtn.classList.replace('btn-secondary', 'btn-outline-secondary');
    bBtn.classList.remove('text-white');
    bIcon.classList.replace('bi-hand-thumbs-down-fill', 'bi-hand-thumbs-down');

    // 追加・切り替えされた場合のみ塗りつぶす
    if (status === 'added' || status === 'switched') {
        if (type === 'good') {
            gBtn.classList.replace('btn-outline-success', 'btn-success');
            gBtn.classList.add('text-white');
            gIcon.classList.replace('bi-hand-thumbs-up', 'bi-hand-thumbs-up-fill');
        } else {
            bBtn.classList.replace('btn-outline-secondary', 'btn-secondary');
            bBtn.classList.add('text-white');
            bIcon.classList.replace('bi-hand-thumbs-down', 'bi-hand-thumbs-down-fill');
        }
    }
    // スコア表示のリセット（判定の前に追加）
    sIcon.classList.remove(
        'btn-success', 'btn-danger', 'btn-secondary',
        'btn-outline-secondary', 'btn-outline-success', 'btn-outline-danger',
        'bg-success', 'bg-danger', 'bg-white', 'bg-light',
        'text-white', 'text-dark', 'border'
    );
    if (point > 0) {
        sIcon.classList.replace('btn-outline-success', 'btn-success');
        sIcon.classList.add('bg-success', 'text-white');
    }
    else if (point < 0) {
        sIcon.classList.replace('btn-outline-secondary', 'btn-secondary');
        sIcon.classList.add('bg-secondary', 'text-white');
    }
    else {
        sIcon.classList.replace('btn-outline-danger', 'btn-danger');
        sIcon.classList.add('bg-light', 'text-dark', 'border');
    }

}

// ふわっとメッセージを出す共通関数（トースト）
function showToast(message) {
    const container = document.getElementById('toast-container');
    const id = Date.now(); // 重ならないようにIDを作成
    const html = `
    <div id="toast-${id}" class="toast align-items-center text-white bg-danger border-0" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    </div>`;

    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(`toast-${id}`);
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();

    // 消えたら要素を削除して軽くする
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// コメントの開閉
function toggleComments(postId) {
    const extraComments = document.querySelectorAll(`.extra-comment-${postId}`);
    const btn = document.getElementById(`show-more-btn-${postId}`);

    if (extraComments.length === 0) return;

    if (extraComments[0].classList.contains('d-none')) {
        // 表示する
        extraComments.forEach(el => {
            el.classList.remove('d-none');
            el.classList.add('animate-fade-in'); // ふわっと出すアニメーション
        });
        // 緑色を維持しつつアイコンとテキストを変更
        btn.innerHTML = '<i class="bi bi-dash-circle-fill me-1"></i> コメントをたたむ';
        btn.classList.replace('text-secondary', 'text-success');
    } else {
        // 隠す
        extraComments.forEach(el => el.classList.add('d-none'));
        btn.innerHTML = '<i class="bi bi-plus-circle-fill me-1"></i> コメントを表示';
        btn.classList.replace('text-secondary', 'text-success');
    }
}

let lastScrollY = window.scrollY;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    // 画面幅が 992px 未満（スマホ・タブレット）の時だけ実行
    if (window.innerWidth < 992) {
        if (window.scrollY > lastScrollY && window.scrollY > 50) {
            // 下にスクロール中：隠す
            navbar.style.transform = "translateY(-100%)";
        } else {
            // 上にスクロール中：出す
            navbar.style.transform = "translateY(0)";
        }
        navbar.style.transition = "transform 0.3s ease-in-out";
    } else {
        // PCサイズ（992px以上）の時は常に表示状態にする
        navbar.style.transform = "translateY(0)";
    }
    lastScrollY = window.scrollY;
});

// 画面サイズが途中で変わった（スマホを横にした等）時のためのリセット処理
window.addEventListener('resize', () => {
    if (window.innerWidth >= 992) {
        navbar.style.transform = "translateY(0)";
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // データの取得
    const scriptElement = document.getElementById('sub-region-data');
    if (!scriptElement) {
        console.warn("sub-region-data element not found.");
        return;
    }

    subRegionData = JSON.parse(scriptElement.textContent);
    // もし中身がまだ文字列なら、もう一度パースする
    if (typeof subRegionData === 'string') {
        subRegionData = JSON.parse(subRegionData);
    }

    // 要素の取得（必ずこの関数内で定義する）
    const regionSelect = document.getElementById('id_region');
    const subRegionSelect = document.getElementById('id_sub_region');

    // 要素が存在しない場合は処理を中断
    if (!regionSelect || !subRegionSelect) {
        console.warn("Form elements not found.");
        return;
    }

    // 3. イベントリスナーの設定
    regionSelect.addEventListener('change', function() {
        const selectedValue = this.value.trim();
        console.log("Selected Region:", selectedValue);
        console.log("Sub Region Data loaded:", subRegionData);
        subRegionSelect.innerHTML = '<option value="">選択の必要はありません</option>';
        subRegionSelect.disabled = true;

        console.log("Data Keys:", Object.keys(subRegionData));
        // キーの一つを取り出して長さを比較
        const firstKey = Object.keys(subRegionData)[0];

        if (selectedValue && subRegionData[selectedValue]) {
            const list = subRegionData[selectedValue];
            
            subRegionSelect.innerHTML = '<option value="">選択してください</option>';
            list.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item;
                opt.textContent = item;
                subRegionSelect.appendChild(opt);
            });
            subRegionSelect.disabled = false;
        }
    });
});