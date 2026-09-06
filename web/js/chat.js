/**
 * web/js/chat.js
 * AI 채팅 UI 이벤트, 백엔드 통신, 사이드바 대화 기록을 담당합니다.
 */

let currentConversationId = null;

document.addEventListener("DOMContentLoaded", () => {
	const btnSend = document.getElementById("btn-send");
	const chatInput = document.getElementById("chat-input");
	const btnNewChat = document.getElementById("btn-new-chat");

	btnSend.addEventListener("click", sendMessage);
	chatInput.addEventListener("keypress", (e) => {
		if (e.key === "Enter") sendMessage();
	});
	btnNewChat.addEventListener("click", startNewChat);

	loadConversationList();

	// ✨ DOM 변화 감지 (MutationObserver): 표(Table)나 이미지가 렌더링되면서 높이가 변할 때 스크롤 꼬임 방지
	const chatContainer = document.getElementById("chat-messages");
	const observer = new MutationObserver(scrollToBottom);
	observer.observe(chatContainer, { childList: true, subtree: true });
});

async function sendMessage() {
	const inputEl = document.getElementById("chat-input");
	const message = inputEl.value.trim();

	if (!message) return;

	appendMessage("user", message);
	inputEl.value = "";

	const loadingId = appendLoading();

	try {
		const bodyData = { message: message };
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

async function loadConversationList() {
	const listEl = document.getElementById("conversation-list");
	const response = await window.API.apiFetch("/api/conversations");
	if (response.status === "success") {
		listEl.innerHTML = response.data
			.map((conv) => {
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

async function deleteConversation(convId, event) {
	event.stopPropagation();
	if (!confirm("이 대화 기록을 정말 삭제하시겠습니까?")) return;

	try {
		const response = await window.API.apiFetch(`/api/conversations/${convId}`, {
			method: "DELETE",
		});

		if (response.status === "success") {
			if (currentConversationId === convId) {
				startNewChat();
			}
			loadConversationList();
		}
	} catch (error) {
		alert("삭제 실패: " + error.message);
	}
}

async function loadConversationDetail(convId) {
	currentConversationId = convId;
	loadConversationList();

	const chatContainer = document.getElementById("chat-messages");
	chatContainer.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> 대화 불러오는 중...</div>';

	try {
		const response = await window.API.apiFetch(`/api/conversations/${convId}`);
		if (response.status === "success") {
			chatContainer.innerHTML = "";
			const messages = response.data.messages;

			messages.forEach((msg) => {
				appendMessage(msg.role, msg.content);
			});
			scrollToBottom();
		}
	} catch (error) {
		chatContainer.innerHTML = `<div class="message ai-message">❌ 대화 내역을 불러오지 못했습니다.</div>`;
	}
}

function startNewChat() {
	currentConversationId = null;
	const chatContainer = document.getElementById("chat-messages");
	chatContainer.innerHTML = `
        <div class="message ai-message">
            안녕하세요! 새로운 대화를 시작합니다. 무엇을 분석해 드릴까요?
        </div>
    `;
	scrollToBottom();
	loadConversationList();
}

/**
 * ✨ 매우 단순한 마크다운 표 변환기 (LLM이 출력한 | 표를 HTML로 렌더링)
 */
function parseMarkdownTable(text) {
	if (!text.includes("|")) return text.replace(/\n/g, "<br>");

	const lines = text.split("\n");
	let html = "";
	let inTable = false;

	for (let line of lines) {
		if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
			if (!inTable) {
				html += "<table><tbody>";
				inTable = true;
			}
			// 구분선(|---|) 무시
			if (line.includes("---")) continue;

			const cells = line
				.split("|")
				.slice(1, -1)
				.map((c) => c.trim());
			html += "<tr>" + cells.map((c) => `<td>${c}</td>`).join("") + "</tr>";
		} else {
			if (inTable) {
				html += "</tbody></table><br>";
				inTable = false;
			}
			html += line + "<br>";
		}
	}
	if (inTable) html += "</tbody></table>";

	// 테이블 내의 첫 번째 줄(tr)의 td를 th로 강제 변경하여 헤더 효과 부여
	return html.replace(/<tr>(<td>.*?<\/td>)<\/tr>/i, (match) => {
		return match.replace(/<td/g, "<th").replace(/<\/td>/g, "</th>");
	});
}

function appendMessage(sender, text) {
	const chatContainer = document.getElementById("chat-messages");
	const msgDiv = document.createElement("div");
	msgDiv.className = `message ${sender === "ai" ? "ai-message" : "user-message"}`;

	// 마크다운 표 변환 적용
	msgDiv.innerHTML = parseMarkdownTable(text);
	chatContainer.appendChild(msgDiv);
	scrollToBottom();
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

	loadingDiv.innerHTML = `<i class="fa-solid fa-ellipsis fa-fade"></i> ${loadingPhrases[phraseIndex]}`;
	scrollToBottom();

	loadingInterval = setInterval(() => {
		phraseIndex = (phraseIndex + 1) % loadingPhrases.length;
		loadingDiv.innerHTML = `<i class="fa-solid fa-ellipsis fa-fade"></i> ${loadingPhrases[phraseIndex]}`;
	}, 1500);

	return id;
}

function removeLoading(id) {
	if (loadingInterval) clearInterval(loadingInterval);
	const loadingDiv = document.getElementById(id);
	if (loadingDiv) loadingDiv.remove();
}

/**
 * ✨ 확실하게 스크롤을 최하단으로 내리는 함수 (더블 체크 로직)
 */
function scrollToBottom() {
	const chatContainer = document.getElementById("chat-messages");
	if (!chatContainer) return;

	// 즉시 스크롤
	chatContainer.scrollTop = chatContainer.scrollHeight;

	// 브라우저 렌더링(리플로우) 완료 후 한 번 더 스크롤 (부드럽게)
	setTimeout(() => {
		chatContainer.scrollTo({
			top: chatContainer.scrollHeight,
			behavior: "smooth",
		});
	}, 100);
}
