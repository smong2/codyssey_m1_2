/**
 * web/js/data.js
 * 주가 데이터 조회, 통계 요약, 차트 렌더링을 담당합니다.
 */

let stockChartInstance = null; // 차트 인스턴스 전역 관리 (업데이트 시 기존 차트 파괴 용도)

document.addEventListener("DOMContentLoaded", () => {
	fetchAndRenderData();
});

/**
 * 백엔드에서 주가 데이터를 가져와 화면에 렌더링합니다.
 */
async function fetchAndRenderData() {
	const summaryContainer = document.getElementById("summary-stats");
	summaryContainer.innerHTML = '<p><i class="fa-solid fa-spinner fa-spin"></i> 데이터를 불러오는 중입니다...</p>';

	try {
		// api.js의 apiFetch를 사용해 최근 100일치 데이터 조회
		const response = await window.API.apiFetch("/api/data?limit=100");

		if (response.status === "success" && response.data.length > 0) {
			// 차트를 그리기 위해 날짜 오름차순(과거 -> 최신)으로 배열 뒤집기
			const stockData = response.data.reverse();

			renderSummary(stockData);
			renderChart(stockData);
		} else {
			summaryContainer.innerHTML = "<p>조회된 주가 데이터가 없습니다.</p>";
		}
	} catch (error) {
		summaryContainer.innerHTML = `<p style="color: #ff4d4f;">❌ 데이터 로딩 실패: ${error.message}</p>`;
	}
}

/**
 * 데이터 요약 통계를 계산하고 화면에 출력합니다.
 */
function renderSummary(data) {
	const container = document.getElementById("summary-stats");

	const count = data.length;
	const startDate = data[0].date;
	const endDate = data[count - 1].date;

	// 종가(value) 배열 추출
	const prices = data.map((item) => item.value);
	const currentPrice = prices[count - 1];
	const previousPrice = prices[count - 2] || currentPrice;

	const maxPrice = Math.max(...prices);
	const minPrice = Math.min(...prices);
	const avgPrice = (prices.reduce((a, b) => a + b, 0) / count).toFixed(0);

	// 추세 계산
	const diff = currentPrice - previousPrice;
	const trendText = diff > 0 ? "▲ 상승" : diff < 0 ? "▼ 하락" : "- 유지";
	const trendColor = diff > 0 ? "#ff4d4f" : diff < 0 ? "#1890ff" : "var(--text-main)"; // 한국식 붉은색 상승/푸른색 하락

	// 요약 HTML 생성
	container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
            <div class="stat-box" style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                <div style="font-size: 0.9rem; color: var(--text-muted);">최근 종가 (${endDate})</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: ${trendColor};">
                    ${currentPrice.toLocaleString()}원 <span style="font-size: 1rem;">${trendText}</span>
                </div>
            </div>
            <div class="stat-box" style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                <div style="font-size: 0.9rem; color: var(--text-muted);">조회 기간 (${count}일)</div>
                <div style="font-size: 1.1rem; font-weight: bold;">${startDate} <br>~ ${endDate}</div>
            </div>
            <div class="stat-box" style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                <div style="font-size: 0.9rem; color: var(--text-muted);">최고 / 최저 (원)</div>
                <div style="font-size: 1.1rem; font-weight: bold; color: #ff4d4f;">${maxPrice.toLocaleString()}</div>
                <div style="font-size: 1.1rem; font-weight: bold; color: #1890ff;">${minPrice.toLocaleString()}</div>
            </div>
        </div>
    `;
}

/**
 * Chart.js를 이용해 주가 추세선을 그립니다.
 */
function renderChart(data) {
	const ctx = document.getElementById("stockChart").getContext("2d");

	const labels = data.map((item) => item.date);
	const prices = data.map((item) => item.value);

	// 기존 차트가 있다면 파괴 후 다시 그림 (중복 렌더링 방지)
	if (stockChartInstance) {
		stockChartInstance.destroy();
	}

	stockChartInstance = new Chart(ctx, {
		type: "line",
		data: {
			labels: labels,
			datasets: [
				{
					label: "삼성전자 종가 (원)",
					data: prices,
					borderColor: "#0056b3",
					backgroundColor: "rgba(0, 86, 179, 0.1)",
					borderWidth: 2,
					pointRadius: 1, // 데이터 포인트 크기 축소
					pointHoverRadius: 5,
					fill: true,
					tension: 0.1, // 선의 곡률
				},
			],
		},
		options: {
			responsive: true,
			maintainAspectRatio: false, // 컨테이너 크기에 맞게 조절
			plugins: {
				legend: { display: false },
				tooltip: {
					callbacks: {
						label: function (context) {
							return context.parsed.y.toLocaleString() + "원";
						},
					},
				},
			},
			scales: {
				x: {
					ticks: {
						maxTicksLimit: 10, // X축 라벨 개수 제한
						color: getComputedStyle(document.body).getPropertyValue("--text-muted"),
					},
					grid: { color: "rgba(0,0,0,0.05)" },
				},
				y: {
					ticks: {
						color: getComputedStyle(document.body).getPropertyValue("--text-muted"),
					},
					grid: { color: "rgba(0,0,0,0.05)" },
				},
			},
		},
	});
}

/**
 * 포트폴리오 목록 조회 및 렌더링
 */
async function fetchPortfolio() {
	const tbody = document.getElementById("portfolio-list");
	tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem; text-align:center;">데이터를 불러오는 중...</td></tr>';

	try {
		const response = await window.API.apiFetch("/api/portfolio");
		if (response.status === "success") {
			renderPortfolio(response.data);
		}
	} catch (error) {
		tbody.innerHTML = `<tr><td colspan="5" style="padding:1rem; text-align:center; color: #ff4d4f;">❌ 로딩 실패</td></tr>`;
	}
}

function renderPortfolio(data) {
	const tbody = document.getElementById("portfolio-list");
	if (data.length === 0) {
		tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem; text-align:center; color: var(--text-muted);">투자 기록이 없습니다.</td></tr>';
		return;
	}

	tbody.innerHTML = data
		.map((item) => {
			const total = item.price * item.quantity;
			return `
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 0.8rem 0;">${item.date}</td>
                <td>${item.price.toLocaleString()}원</td>
                <td>${item.quantity.toLocaleString()}주</td>
                <td>${total.toLocaleString()}원</td>
                <td>
                    <button onclick="deletePortfolioItem('${item.id}')" style="background:#ff4d4f; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">삭제</button>
                </td>
            </tr>
        `;
		})
		.join("");
}

/**
 * 포트폴리오 새 기록 추가 (POST)
 */
async function addPortfolioItem() {
	const date = document.getElementById("port-date").value;
	const price = document.getElementById("port-price").value;
	const quantity = document.getElementById("port-qty").value;

	if (!date || !price || !quantity) {
		alert("날짜, 단가, 수량을 모두 입력해주세요.");
		return;
	}

	try {
		const response = await window.API.apiFetch("/api/portfolio", {
			method: "POST",
			body: JSON.stringify({
				date: date,
				price: parseFloat(price),
				quantity: parseInt(quantity, 10),
			}),
		});

		if (response.status === "success") {
			// 입력창 초기화
			document.getElementById("port-date").value = "";
			document.getElementById("port-price").value = "";
			document.getElementById("port-qty").value = "";
			// 목록 새로고침
			fetchPortfolio();
		}
	} catch (error) {
		alert("추가 실패: " + error.message);
	}
}

/**
 * 포트폴리오 기록 삭제 (DELETE)
 */
async function deletePortfolioItem(id) {
	if (!confirm("정말 삭제하시겠습니까?")) return;

	try {
		const response = await window.API.apiFetch(`/api/portfolio/${id}`, {
			method: "DELETE",
		});

		if (response.status === "success") {
			fetchPortfolio(); // 목록 새로고침
		}
	} catch (error) {
		alert("삭제 실패: " + error.message);
	}
}

document.addEventListener("DOMContentLoaded", () => {
	fetchAndRenderData();
	fetchPortfolio(); // 추가: 페이지 로드 시 포트폴리오 목록 가져오기

	// 추가: '기록 추가' 버튼 클릭 이벤트 연결
	document.getElementById("btn-add-portfolio").addEventListener("click", addPortfolioItem);
});
