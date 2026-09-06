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

	// 사이드바 토글 이벤트
	document.getElementById("btn-toggle-sidebar").addEventListener("click", () => {
		const sidebar = document.querySelector(".sidebar");
		sidebar.classList.toggle("collapsed");
	});

	// 포트폴리오 접기/펴기 이벤트
	document.getElementById("btn-toggle-portfolio").addEventListener("click", () => {
		const content = document.getElementById("portfolio-content");
		const icon = document.getElementById("portfolio-icon");

		content.classList.toggle("collapsed");
		if (content.classList.contains("collapsed")) {
			icon.classList.replace("fa-chevron-up", "fa-chevron-down");
		} else {
			icon.classList.replace("fa-chevron-down", "fa-chevron-up");
		}
	});
});

/**
 * 백엔드에서 주가 데이터를 가져와 화면에 렌더링합니다. (세션 캐싱 적용)
 */
async function fetchAndRenderData() {
	const summaryContainer = document.getElementById("summary-stats");
	summaryContainer.innerHTML = '<p style="padding:1rem;"><i class="fa-solid fa-spinner fa-spin"></i> 통계 및 차트를 불러오는 중...</p>';

	try {
		// 1. 브라우저 세션 스토리지에 캐시된 데이터가 있는지 확인 (F5 새로고침 시 빠른 로딩)
		const cachedData = sessionStorage.getItem("stockDataCache");
		if (cachedData) {
			allStockData = JSON.parse(cachedData);
			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			applyChartFilter(currentFilterDays);
			return; // 캐시가 있으면 서버에 요청하지 않고 즉시 종료
		}

		// 2. 캐시가 없으면 백엔드에 요청 (백엔드 역시 자체 SQLite 캐시에서 초고속으로 반환함)
		const response = await window.API.apiFetch("/api/data?limit=2500");
		if (response.status === "success" && response.data.length > 0) {
			allStockData = response.data.reverse();

			// 브라우저 탭을 닫기 전까지 유지되도록 스토리지에 저장
			sessionStorage.setItem("stockDataCache", JSON.stringify(allStockData));

			// 초기 렌더링 (1개월 기준)
			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			applyChartFilter(currentFilterDays);
		}
	} catch (error) {
		summaryContainer.innerHTML = `<p style="color: #ff4d4f;">❌ 로딩 실패: ${error.message}</p>`;
	}
}

/**
 * 선택된 기간에 맞게 차트와 요약 통계를 업데이트합니다.
 */
async function applyChartFilter(days) {
	if (allStockData.length === 0) return;

	// 차트용 데이터 필터링
	const filteredData = allStockData.slice(-days);
	renderChart(filteredData, currentChartType);

	// 통계 요약 API 호출 및 렌더링
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
                    <div style="font-size: 0.85rem; color: var(--text-muted);">
                        가격 변동성 
                        <i class="fa-regular fa-circle-question" title="주가의 흩어짐 정도(표준편차)를 의미합니다. 수치가 클수록 최근 주가의 등락폭이 큼을 나타냅니다." style="cursor:help;"></i>
                    </div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">±${s.volatility.toLocaleString()}</div>
                </div>
            `;
		}
	} catch (e) {
		console.error("통계 요약 로딩 실패:", e);
	}
}

/**
 * Chart.js를 이용해 주가 추세선을 그립니다.
 */
function renderChart(data, type) {
	const ctx = document.getElementById("stockChart").getContext("2d");
	const labels = data.map((item) => item.date);

	const gridColor = getComputedStyle(document.body).getPropertyValue("--border-color") || "rgba(0,0,0,0.1)";
	const textColor = getComputedStyle(document.body).getPropertyValue("--text-muted") || "#666";

	let datasets = [];
	let allPrices = []; // Y축 동적 스케일링을 위한 가격 수집 배열

	if (type === "line") {
		const lineData = data.map((item) => item.close || item.value);
		allPrices = [...lineData];
		datasets = [
			{
				type: "line",
				label: "삼성전자 종가 (원)",
				data: lineData,
				borderColor: "#0056b3",
				backgroundColor: "rgba(0, 86, 179, 0.1)",
				borderWidth: 2,
				pointRadius: data.length === 1 ? 6 : data.length > 50 ? 0 : 3, // 1일 데이터일 경우 점 크기 확대
				pointHoverRadius: 6,
				fill: true,
				tension: 0.4,
			},
		];
	} else {
		const boxData = data.map((item, index) => {
			const c = item.close || item.value;
			let o = item.open;
			if (o === undefined) o = index > 0 ? data[index - 1].close || data[index - 1].value : c * 0.999;
			allPrices.push(o, c);
			return [Math.min(o, c), Math.max(o, c)];
		});

		const boxColors = data.map((item, index) => {
			const c = item.close || item.value;
			let o = item.open;
			if (o === undefined) o = index > 0 ? data[index - 1].close || data[index - 1].value : c * 0.999;
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
				barPercentage: data.length === 1 ? 0.2 : 0.9, // 1일 데이터일 경우 박스 너비를 얇게 조절
			},
		];
	}

	// Y축 최소/최대값 동적 계산 (상하 5% 여백 추가)
	const minPrice = Math.min(...allPrices);
	const maxPrice = Math.max(...allPrices);
	const padding = (maxPrice - minPrice) * 0.05;

	// 데이터가 1개라서 min과 max가 같을 경우의 예외 처리
	const yMin = minPrice === maxPrice ? minPrice * 0.95 : minPrice - padding;
	const yMax = minPrice === maxPrice ? maxPrice * 1.05 : maxPrice + padding;

	if (stockChartInstance) stockChartInstance.destroy();

	stockChartInstance = new Chart(ctx, {
		data: { labels: labels, datasets: datasets },
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: {
				legend: { display: true, position: "top", labels: { color: textColor } },
				tooltip: {
					mode: "index",
					intersect: false,
					callbacks: {
						label: function (context) {
							// 툴팁에서 소수점 제거 및 정수 포맷 적용
							if (Array.isArray(context.raw)) {
								return `${context.dataset.label}: ${Math.round(context.raw[0]).toLocaleString()}원 ~ ${Math.round(context.raw[1]).toLocaleString()}원`;
							}
							return `${context.dataset.label}: ${Math.round(context.raw).toLocaleString()}원`;
						},
					},
				},
			},
			scales: {
				x: {
					offset: true, // X축 양끝에 여백을 주어 1일 데이터가 정중앙에 오도록 강제
					ticks: { color: textColor, maxTicksLimit: 15 },
					grid: { color: gridColor },
				},
				y: {
					min: yMin, // 동적 계산된 최저값
					max: yMax, // 동적 계산된 최고값
					ticks: {
						color: textColor,
						callback: function (value) {
							// Y축 라벨에서 소수점 제거 및 정수 포맷 적용
							return Math.round(value).toLocaleString() + "원";
						},
					},
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
