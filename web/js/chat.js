/**
 * web/js/chat.js
 * AI 채팅 UI 이벤트 및 백엔드 통신을 담당합니다.
 */

document.addEventListener("DOMContentLoaded", () => {
	const btnSend = document.getElementById("btn-send");
	const chatInput = document.getElementById("chat-input");

	// 전송 버튼 클릭 이벤트
	btnSend.addEventListener("click", sendMessage);

	// 엔터키 입력 이벤트
	chatInput.addEventListener("keypress", (e) => {
		if (e.key === "Enter") {
			sendMessage();
		}
	});
});

/**
 * 메시지 전송 및 AI 응답 처리
 */
async function sendMessage() {
	const inputEl = document.getElementById("chat-input");
	const message = inputEl.value.trim();

	if (!message) return;

	// 1. 사용자 메시지 화면에 추가
	appendMessage("user", message);
	inputEl.value = ""; // 입력창 비우기

	// 2. 대기 중(로딩) 말풍선 추가
	const loadingId = appendLoading();

	try {
		// 3. 백엔드 AI 채팅 엔드포인트 호출 (/api/chat)
		const response = await window.API.apiFetch("/api/chat", {
			method: "POST",
			body: JSON.stringify({ message: message }),
		});

		// 4. 로딩 말풍선 제거 및 AI 실제 응답 추가
		removeLoading(loadingId);

		if (response.status === "success") {
			appendMessage("ai", response.reply);
		}
	} catch (error) {
		removeLoading(loadingId);
		appendMessage("ai", `❌ 오류가 발생했습니다: ${error.message}`);
	}
}

/**
 * 채팅창에 말풍선 DOM을 생성하여 덧붙입니다.
 * @param {string} sender - 'user' 또는 'ai'
 * @param {string} text - 출력할 메시지
 */
function appendMessage(sender, text) {
	const chatContainer = document.getElementById("chat-messages");
	const msgDiv = document.createElement("div");

	// style.css에 정의된 클래스 적용
	msgDiv.className = `message ${sender === "ai" ? "ai-message" : "user-message"}`;
	msgDiv.textContent = text;

	chatContainer.appendChild(msgDiv);

	// 새로운 메시지가 추가되면 스크롤을 맨 아래로 이동
	chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * 로딩 애니메이션 말풍선을 추가합니다.
 * @returns {string} 생성된 로딩 엘리먼트의 고유 ID
 */
function appendLoading() {
	const chatContainer = document.getElementById("chat-messages");
	const loadingDiv = document.createElement("div");
	const id = "loading-" + Date.now();

	loadingDiv.id = id;
	loadingDiv.className = "message ai-message";
	loadingDiv.innerHTML = '<i class="fa-solid fa-ellipsis fa-fade"></i> AI가 분석 중입니다...';

	chatContainer.appendChild(loadingDiv);
	chatContainer.scrollTop = chatContainer.scrollHeight;

	return id;
}

/**
 * 로딩 애니메이션 말풍선을 제거합니다.
 */
function removeLoading(id) {
	const loadingDiv = document.getElementById(id);
	if (loadingDiv) {
		loadingDiv.remove();
	}
}
