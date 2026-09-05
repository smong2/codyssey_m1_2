/**
 * web/js/data.js
 * 주가 데이터 조회, 통계 요약, 차트 렌더링을 담당합니다.
 */

let stockChartInstance = null; // 차트 인스턴스 전역 관리 (업데이트 시 기존 차트 파괴 용도)
let allStockData = []; // 서버에서 불러온 전체 데이터 원본 저장
let currentChartType = "line"; // 현재 차트 타입 (line 또는 box)
let currentFilterDays = 20; // 기본 1개월

document.addEventListener("DOMContentLoaded", () => {
	fetchAndRenderData();
	fetchPortfolio();
	document.getElementById("btn-add-portfolio").addEventListener("click", addPortfolioItem);

	// 차트 기간 필터 버튼 이벤트
	document.querySelectorAll(".filter-btn").forEach((btn) => {
		btn.addEventListener("click", (e) => {
			document.querySelectorAll(".filter-btn").forEach((b) => (b.style.backgroundColor = "var(--bg-color)"));
			e.target.style.backgroundColor = "var(--hover-color)";

			currentFilterDays = parseInt(e.target.dataset.days);
			applyChartFilter(currentFilterDays);
		});
	});

	// 차트 타입 선택 이벤트
	document.getElementById("chart-type").addEventListener("change", (e) => {
		currentChartType = e.target.value;
		applyChartFilter(currentFilterDays); // 타입 변경 시 차트 리렌더링
	});
});

/**
 * 백엔드에서 주가 데이터를 가져와 화면에 렌더링합니다.
 */
async function fetchAndRenderData() {
	const summaryContainer = document.getElementById("summary-stats");
	summaryContainer.innerHTML = '<p style="padding:1rem;"><i class="fa-solid fa-spinner fa-spin"></i> 통계 및 차트를 불러오는 중...</p>';

	try {
		const response = await window.API.apiFetch("/api/data?limit=2500");
		if (response.status === "success" && response.data.length > 0) {
			allStockData = response.data.reverse();

			// 초기 렌더링 (1개월 기준)
			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			applyChartFilter(currentFilterDays);
		}
	} catch (error) {
		summaryContainer.innerHTML = `<p style="color: #ff4d4f;">❌ 로딩 실패: ${error.message}</p>`;
	}
}

async function applyChartFilter(days) {
	if (allStockData.length === 0) return;

	// 차트용 데이터 필터링
	const filteredData = allStockData.slice(-days);
	renderChart(filteredData, currentChartType);

	// ✨ 통계 요약 API 호출 및 렌더링 (보너스 과제)
	try {
		const summaryResponse = await window.API.apiFetch(`/api/data/summary?limit=${days}`);
		if (summaryResponse.status === "success") {
			const s = summaryResponse.summary;
			const trendColor = s.trend === "상승" ? "#ff4d4f" : s.trend === "하락" ? "#1890ff" : "var(--text-main)";

			document.getElementById("summary-stats").innerHTML = `
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">조회 기간 (영업일 기준 ${s.count}일)</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">${s.period}</div>
                </div>
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">평균 종가 / 최근 추세</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">
                        ${s.average.toLocaleString()}원 <span style="color:${trendColor}">(${s.trend})</span>
                    </div>
                </div>
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">최고 / 최저 (원)</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px; color:#ff4d4f;">${s.max.toLocaleString()}</div>
                    <div style="font-size: 1rem; font-weight: bold; color:#1890ff;">${s.min.toLocaleString()}</div>
                </div>
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px; border-left: 3px solid #8e44ad;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">가격 변동성 (보너스 지표)</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">±${s.volatility.toLocaleString()}</div>
                </div>
            `;
		}
	} catch (e) {
		console.error("통계 요약 로딩 실패:", e);
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
function renderChart(data, type) {
	const ctx = document.getElementById("stockChart").getContext("2d");
	const labels = data.map((item) => item.date);

	// ✨ 다크모드 대응: body에 설정된 --border-color 속성을 읽어와 격자색으로 사용
	const gridColor = getComputedStyle(document.body).getPropertyValue("--border-color") || "rgba(0,0,0,0.1)";
	const textColor = getComputedStyle(document.body).getPropertyValue("--text-muted") || "#666";

	let datasets = [];

	if (type === "line") {
		datasets = [
			{
				type: "line",
				label: "삼성전자 종가 (원)",
				data: data.map((item) => item.close || item.value),
				borderColor: "#0056b3",
				backgroundColor: "rgba(0, 86, 179, 0.1)",
				borderWidth: 2,
				pointRadius: data.length > 50 ? 0 : 3, // 데이터가 많으면 점 숨김
				pointHoverRadius: 6,
				fill: true,
				tension: 0.4,
			},
		];
	} else {
		// 박스 차트 (시가-종가)
		const boxData = data.map((item) => {
			const o = item.open || item.value;
			const c = item.close || item.value;
			return [Math.min(o, c), Math.max(o, c)];
		});
		const boxColors = data.map((item) => {
			const o = item.open || item.value;
			const c = item.close || item.value;
			return c >= o ? "rgba(255, 77, 79, 0.8)" : "rgba(24, 144, 255, 0.8)";
		});

		datasets = [
			{
				type: "bar",
				label: "시가-종가 변동폭",
				data: boxData,
				backgroundColor: boxColors,
				borderWidth: 1,
				borderColor: boxColors,
			},
		];
	}

	if (stockChartInstance) stockChartInstance.destroy();

	stockChartInstance = new Chart(ctx, {
		data: { labels: labels, datasets: datasets },
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: {
				legend: { display: true, position: "top", labels: { color: textColor } },
				tooltip: { mode: "index", intersect: false },
			},
			scales: {
				x: {
					ticks: { color: textColor, maxTicksLimit: 15 },
					grid: { color: gridColor },
				},
				y: {
					ticks: { color: textColor },
					grid: { color: gridColor },
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
	const summaryDiv = document.getElementById("portfolio-summary");

	let totalBuy = 0,
		totalBuyQty = 0;
	let totalSell = 0,
		totalSellQty = 0;

	tbody.innerHTML = data
		.map((item) => {
			const isBuy = item.trade_type === "buy";
			const total = item.price * item.quantity;

			if (isBuy) {
				totalBuy += total;
				totalBuyQty += item.quantity;
			} else {
				totalSell += total;
				totalSellQty += item.quantity;
			}

			const typeBadge = isBuy ? `<span style="color:#ff4d4f">매수</span>` : `<span style="color:#1890ff">매도</span>`;

			return `
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 0.8rem 0;">${item.date}<br><small>${typeBadge}</small></td>
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

	// 단순 누적 기반 실현 수익 및 보유 현황 표시
	const currentHolding = totalBuyQty - totalSellQty;
	const realizedProfit = totalSell - totalBuy * (totalSellQty / (totalBuyQty || 1)); // 평단가 기반 단순 실현수익
	const profitRate = totalSellQty > 0 ? ((realizedProfit / (totalBuy * (totalSellQty / totalBuyQty))) * 100).toFixed(2) : 0;

	summaryDiv.innerHTML = `
        현재 보유 수량: ${currentHolding}주 | 
        총 매도 수익실현: <span style="color: ${realizedProfit >= 0 ? "#ff4d4f" : "#1890ff"}">${realizedProfit.toLocaleString()}원 (${profitRate}%)</span>
    `;
}

/**
 * 포트폴리오 새 기록 추가 (POST)
 */
async function addPortfolioItem() {
	const type = document.getElementById("port-type").value;
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
				trade_type: type,
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
