/**
 * 애플리케이션 공통 초기화 및 UI 이벤트 로직
 */

document.addEventListener("DOMContentLoaded", () => {
	initThemeToggle();
	// 추후 데이터 로드 및 차트 초기화 함수 호출 위치
});

/**
 * 다크모드 토글 초기화
 */
function initThemeToggle() {
	const btnTheme = document.getElementById("btn-theme");
	const icon = btnTheme.querySelector("i");

	// 로컬 스토리지에서 저장된 테마 확인
	const savedTheme = localStorage.getItem("theme");
	if (savedTheme === "dark") {
		document.body.classList.add("dark-mode");
		icon.classList.replace("fa-moon", "fa-sun");
	}

	// 토글 버튼 클릭 이벤트
	btnTheme.addEventListener("click", () => {
		document.body.classList.toggle("dark-mode");
		const isDark = document.body.classList.contains("dark-mode");

		// 아이콘 변경 및 스토리지 저장
		if (isDark) {
			icon.classList.replace("fa-moon", "fa-sun");
			localStorage.setItem("theme", "dark");
		} else {
			icon.classList.replace("fa-sun", "fa-moon");
			localStorage.setItem("theme", "light");
		}
	});
}
