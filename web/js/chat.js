/**
 * web/js/chat.js
 * AI 채팅 UI 이벤트, 백엔드 통신, 사이드바 대화 기록을 담당합니다.
 */

let currentConversationId = null; // 현재 활성화된 대화방 ID

document.addEventListener("DOMContentLoaded", () => {
	const btnSend = document.getElementById("btn-send");
	const chatInput = document.getElementById("chat-input");
	const btnNewChat = document.getElementById("btn-new-chat");

	btnSend.addEventListener("click", sendMessage);
	chatInput.addEventListener("keypress", (e) => {
		if (e.key === "Enter") sendMessage();
	});
	btnNewChat.addEventListener("click", startNewChat);

	// 페이지 로드 시 사이드바 목록 불러오기
	loadConversationList();
});

/**
 * 1. 메시지 전송 및 AI 응답 처리
 */
async function sendMessage() {
	const inputEl = document.getElementById("chat-input");
	const message = inputEl.value.trim();

	if (!message) return;

	appendMessage("user", message);
	inputEl.value = "";

	const loadingId = appendLoading();

	try {
		const bodyData = { message: message };
		// 기존 대화방이 있다면 ID를 함께 전송
		if (currentConversationId) {
			bodyData.conversation_id = currentConversationId;
		}

		const response = await window.API.apiFetch("/api/chat", {
			method: "POST",
			body: JSON.stringify(bodyData),
		});

		removeLoading(loadingId);

		if (response.status === "success") {
			appendMessage("ai", response.reply);

			// 첫 질문이어서 새 방이 파진 경우 ID 갱신 및 사이드바 업데이트
			if (!currentConversationId) {
				currentConversationId = response.conversation_id;
				loadConversationList();
			}
		}
	} catch (error) {
		removeLoading(loadingId);
		appendMessage("ai", `❌ 오류가 발생했습니다: ${error.message}`);
	}
}

/**
 * 2. 사이드바 대화 목록 불러오기
 */
async function loadConversationList() {
	const listEl = document.getElementById("conversation-list");
	const response = await window.API.apiFetch("/api/conversations");
	if (response.status === "success") {
		listEl.innerHTML = response.data
			.map((conv) => {
				// 현재 활성화된 방이면 배경색 다르게 처리
				const isActive = conv.id === currentConversationId;
				const bgStyle = isActive ? "background-color: var(--hover-color); font-weight: bold;" : "";

				return `
            <li style="padding: 0.8rem; cursor: pointer; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; ${bgStyle}" 
                onclick="loadConversationDetail('${conv.id}')">
                <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;">
                    <i class="fa-regular fa-message" style="margin-right: 0.5rem;"></i>
                    ${conv.title || "새 대화"}
                </div>
                <div>
                    <button onclick="editTitle('${conv.id}', '${conv.title}', event)" style="background:none; border:none; color:var(--text-muted); cursor:pointer; padding:4px;" title="수정">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button onclick="deleteConversation('${conv.id}', event)" style="background:none; border:none; color:#ff4d4f; cursor:pointer; padding:4px;" title="삭제">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </li>
        `;
			})
			.join("");
	}
}

async function editTitle(convId, oldTitle, event) {
	event.stopPropagation();
	const newTitle = prompt("새로운 제목을 입력하세요:", oldTitle);
	if (!newTitle || newTitle.trim() === oldTitle) return;

	try {
		await window.API.apiFetch(`/api/conversations/${convId}`, {
			method: "PUT",
			body: JSON.stringify({ title: newTitle.trim() }),
		});
		loadConversationList();
	} catch (error) {
		alert("제목 수정 실패");
	}
}

/**
 * [신규] 사이드바 대화방 삭제
 */
async function deleteConversation(convId, event) {
	// 부모 요소(li)의 onclick 이벤트(대화 불러오기)가 실행되는 것을 차단
	event.stopPropagation();

	if (!confirm("이 대화 기록을 정말 삭제하시겠습니까?")) return;

	try {
		const response = await window.API.apiFetch(`/api/conversations/${convId}`, {
			method: "DELETE",
		});

		if (response.status === "success") {
			// 삭제한 방이 현재 열려있는 방이라면 채팅창 초기화
			if (currentConversationId === convId) {
				startNewChat();
			}
			// 목록 새로고침
			loadConversationList();
		}
	} catch (error) {
		alert("삭제 실패: " + error.message);
	}
}

/**
 * 3. 과거 대화 내역 불러와서 채팅창에 뿌리기
 */
async function loadConversationDetail(convId) {
	currentConversationId = convId;
	loadConversationList();

	const chatContainer = document.getElementById("chat-messages");
	chatContainer.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> 대화 불러오는 중...</div>';

	try {
		const response = await window.API.apiFetch(`/api/conversations/${convId}`);
		if (response.status === "success") {
			chatContainer.innerHTML = ""; // 초기화
			const messages = response.data.messages;

			messages.forEach((msg) => {
				appendMessage(msg.role, msg.content);
			});
		}
	} catch (error) {
		chatContainer.innerHTML = `<div class="message ai-message">❌ 대화 내역을 불러오지 못했습니다.</div>`;
	}
}

/**
 * 4. 새 대화 시작하기 (초기화)
 */
function startNewChat() {
	currentConversationId = null;
	const chatContainer = document.getElementById("chat-messages");
	chatContainer.innerHTML = `
        <div class="message ai-message">
            안녕하세요! 새로운 대화를 시작합니다. 무엇을 분석해 드릴까요?
        </div>
    `;
}

// --- 아래 UI 관련 공통 함수 (appendMessage, appendLoading, removeLoading)는 기존과 동일합니다 ---
function appendMessage(sender, text) {
	const chatContainer = document.getElementById("chat-messages");
	const msgDiv = document.createElement("div");
	msgDiv.className = `message ${sender === "ai" ? "ai-message" : "user-message"}`;

	// 줄바꿈 문자를 <br>로 변환하여 출력
	msgDiv.innerHTML = text.replace(/\n/g, "<br>");
	chatContainer.appendChild(msgDiv);
	chatContainer.scrollTop = chatContainer.scrollHeight;
}

let loadingInterval;

function appendLoading() {
	const chatContainer = document.getElementById("chat-messages");
	const loadingDiv = document.createElement("div");
	const id = "loading-" + Date.now();
	loadingDiv.id = id;
	loadingDiv.className = "message ai-message";
	chatContainer.appendChild(loadingDiv);

	const loadingPhrases = ["AI가 시장 데이터를 분석 중입니다...", "과거 투자 기록과 수익률을 대조 중입니다...", "답변을 정교하게 작성 중입니다..."];
	let phraseIndex = 0;

	// 즉시 첫 문구 렌더링
	loadingDiv.innerHTML = `<i class="fa-solid fa-ellipsis fa-fade"></i> ${loadingPhrases[phraseIndex]}`;
	chatContainer.scrollTop = chatContainer.scrollHeight;

	// 1.5초마다 문구 변경 및 스크롤 고정
	loadingInterval = setInterval(() => {
		phraseIndex = (phraseIndex + 1) % loadingPhrases.length;
		loadingDiv.innerHTML = `<i class="fa-solid fa-ellipsis fa-fade"></i> ${loadingPhrases[phraseIndex]}`;
		chatContainer.scrollTop = chatContainer.scrollHeight;
	}, 1500);

	return id;
}

function removeLoading(id) {
	if (loadingInterval) clearInterval(loadingInterval);
	const loadingDiv = document.getElementById(id);
	if (loadingDiv) loadingDiv.remove();
}

function scrollToBottom() {
	const chatContainer = document.getElementById("chat-messages");
	setTimeout(() => {
		chatContainer.scrollTop = chatContainer.scrollHeight;
	}, 50);
}
