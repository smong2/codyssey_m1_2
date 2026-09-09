/**
 * 백엔드 통신 공통 모듈
 */

// 개발(Local) 및 운영(Vercel 등) 환경에 따른 API URL 설정
// 추후 Vercel 환경변수로 주입받거나, 현재 호스트 기반으로 분기할 수 있습니다.
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
	? "http://localhost:8090" 
	: "https://codyssey-m1-2-fimf.onrender.com";

/**
 * 공통 fetch 래퍼 함수
 * @param {string} endpoint - API 엔드포인트 (예: '/api/data')
 * @param {object} options - fetch 옵션 (method, headers, body 등)
 */
async function apiFetch(endpoint, options = {}) {
	const url = `${API_BASE_URL}${endpoint}`;

	// 기본 헤더 설정 (JSON)
	const defaultHeaders = {
		"Content-Type": "application/json",
	};

	const config = {
		...options,
		headers: {
			...defaultHeaders,
			...options.headers,
		},
	};

	try {
		const response = await fetch(url, config);

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail || `서버 오류: ${response.status}`);
		}

		return await response.json();
	} catch (error) {
		console.error(`[API Error] ${endpoint}:`, error);
		throw error;
	}
}

// 전역 객체로 노출하여 다른 JS 파일에서 사용
window.API = {
	apiFetch,
	API_BASE_URL,
};
