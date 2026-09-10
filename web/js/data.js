/**
 * web/js/data.js
 * 주가 데이터 조회, 통계 요약, 차트 렌더링을 담당합니다.
 */

let stockChartInstance = null;
let allStockData = [];
let currentChartType = "line";

document.addEventListener("DOMContentLoaded", () => {
	fetchAndRenderData();
	fetchPortfolio();

	document.getElementById("btn-add-portfolio").addEventListener("click", addPortfolioItem);

	// 미리 설정된 버튼(1일, 1달 등) 클릭
	document.querySelectorAll(".filter-btn").forEach((btn) => {
		btn.addEventListener("click", (e) => {
			document.querySelectorAll(".filter-btn").forEach((b) => (b.style.backgroundColor = "var(--bg-color)"));
			e.target.style.backgroundColor = "var(--hover-color)";

			const days = parseInt(e.target.dataset.days);
			if (allStockData.length === 0) return;
			const filteredData = allStockData.slice(-days);
			renderDataView(filteredData);
		});
	});

	// ✨ 직접 날짜 조회 버튼 이벤트
	document.getElementById("btn-custom-date").addEventListener("click", () => {
		const start = document.getElementById("start-date").value;
		const end = document.getElementById("end-date").value;
		if (!start || !end) return alert("시작일과 종료일을 모두 선택해주세요.");
		if (start > end) return alert("시작일이 종료일보다 클 수 없습니다.");

		// 직접 지정 시 기존 퀵 버튼 하이라이트 제거
		document.querySelectorAll(".filter-btn").forEach((b) => (b.style.backgroundColor = "var(--bg-color)"));

		// 날짜 구간으로 데이터 필터링 (allStockData는 시간순 배열)
		const filteredData = allStockData.filter((d) => d.date >= start && d.date <= end);
		if (filteredData.length === 0) return alert("선택하신 기간에 존재하는 주가 데이터가 없습니다.");

		renderDataView(filteredData);
	});

	document.getElementById("chart-type").addEventListener("change", (e) => {
		currentChartType = e.target.value;
		if (window.currentFilteredData && window.currentFilteredData.length > 0) {
			renderChart(window.currentFilteredData, currentChartType);
		} else {
			document.querySelector(".filter-btn[style*='var(--hover-color)']")?.click() || document.getElementById("btn-custom-date").click();
		}
	});

	// ✨ 탭(Tab) 전환 버그 완벽 수정 (closest 사용) 및 차트 리사이즈 처리
	document.querySelectorAll(".tab-btn").forEach((btn) => {
		btn.addEventListener("click", (e) => {
			// 버튼 내부의 아이콘을 클릭해도 정확히 버튼 요소를 찾도록 보완
			const currentBtn = e.target.closest(".tab-btn");
			if (!currentBtn) return;

			document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
			currentBtn.classList.add("active");

			document.querySelectorAll(".view-content").forEach((v) => v.classList.remove("active"));
			const targetId = currentBtn.getAttribute("data-target");
			document.getElementById(targetId).classList.add("active");

			// 차트 탭으로 돌아올 때 캔버스 크기 깨짐 방지
			if (targetId === "chart-view" && stockChartInstance) {
				stockChartInstance.resize();
			}
		});
	});

	document.getElementById("btn-toggle-sidebar").addEventListener("click", () => {
		document.querySelector(".sidebar").classList.toggle("collapsed");
	});

	document.getElementById("btn-toggle-portfolio").addEventListener("click", () => {
		const content = document.getElementById("portfolio-content");
		const icon = document.getElementById("portfolio-icon");
		content.classList.toggle("collapsed");
		icon.classList.replace(content.classList.contains("collapsed") ? "fa-chevron-up" : "fa-chevron-down", content.classList.contains("collapsed") ? "fa-chevron-down" : "fa-chevron-up");
	});

	const btnExport = document.getElementById("btn-export");
	if (btnExport) btnExport.addEventListener("click", exportToCSV);
});

async function fetchAndRenderData() {
	const summaryContainer = document.getElementById("summary-stats");
	summaryContainer.innerHTML = '<p style="padding:1rem;"><i class="fa-solid fa-spinner fa-spin"></i> 데이터를 불러오는 중...</p>';

	try {
		const cachedData = sessionStorage.getItem("stockDataCache");
		if (cachedData) {
			allStockData = JSON.parse(cachedData);
			initDatePickers();
			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			renderDataView(allStockData.slice(-20));
			return;
		}

		const response = await window.API.apiFetch("/api/data?limit=2500");
		if (response.status === "success" && response.data.length > 0) {
			allStockData = response.data.reverse(); // 과거 -> 최신 순 정렬
			sessionStorage.setItem("stockDataCache", JSON.stringify(allStockData));
			initDatePickers();
			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			renderDataView(allStockData.slice(-20));
		}
	} catch (error) {
		summaryContainer.innerHTML = `<p style="color: #ff4d4f;">❌ 로딩 실패: ${error.message}</p>`;
	}
}

// 캘린더 입력값의 Min/Max를 실제 DB 보유 기간으로 제한
function initDatePickers() {
	if (allStockData.length === 0) return;
	const oldest = allStockData[0].date;
	const newest = allStockData[allStockData.length - 1].date;

	const startInput = document.getElementById("start-date");
	const endInput = document.getElementById("end-date");

	startInput.min = oldest;
	startInput.max = newest;
	endInput.min = oldest;
	endInput.max = newest;
}

// ✨ 차트와 통계 탭을 동시에 갱신 & 캘린더 날짜 톱니바퀴 동기화
window.currentFilteredData = []; // 내보내기를 위한 전역 임시 저장
function renderDataView(data) {
	if (!data || data.length === 0) return;
	window.currentFilteredData = data;

	// 1. 차트 렌더링
	renderChart(data, currentChartType);

	// 2. 순수 데이터 기반 요약 통계 프론트엔드 실시간 연산
	const count = data.length;
	const startDate = data[0].date;
	const endDate = data[count - 1].date;

	// ✨ 퀵 버튼(1개월, 1년 등)을 눌렀을 때 캘린더 UI 날짜도 일치하도록 자동 동기화
	document.getElementById("start-date").value = startDate;
	document.getElementById("end-date").value = endDate;

	const prices = data.map((d) => d.close || d.value);
	const startPrice = prices[0];
	const endPrice = prices[count - 1];

	const maxP = Math.max(...prices);
	const minP = Math.min(...prices);
	const avgP = prices.reduce((a, b) => a + b, 0) / count;

	const diff = endPrice - startPrice;
	const diffRate = (diff / startPrice) * 100;
	const diffColor = diff > 0 ? "#ff4d4f" : diff < 0 ? "#1890ff" : "var(--text-main)";
	const diffSign = diff > 0 ? "+" : "";

	document.getElementById("summary-stats").innerHTML = `
        <div style="padding: 1.2rem; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.9rem; color: var(--text-muted);">조회 기간 (영업일 ${count}일)</div>
            <div style="font-size: 1.1rem; font-weight: bold; margin-top: 8px;">${startDate} <br>~ ${endDate}</div>
        </div>
        <div style="padding: 1.2rem; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.9rem; color: var(--text-muted);">해당 기간 시초가 ➔ 종가</div>
            <div style="font-size: 1.2rem; font-weight: bold; margin-top: 8px;">
                ${startPrice.toLocaleString()}원 ➔ ${endPrice.toLocaleString()}원
            </div>
        </div>
        <div style="padding: 1.2rem; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.9rem; color: var(--text-muted);">기간 내 등락률</div>
            <div style="font-size: 1.3rem; font-weight: bold; margin-top: 8px; color: ${diffColor};">
                ${diffSign}${diff.toLocaleString()}원 (${diffSign}${diffRate.toFixed(2)}%)
            </div>
        </div>
        <div style="padding: 1.2rem; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border-color); border-left: 4px solid var(--primary-color);">
            <div style="font-size: 0.9rem; color: var(--text-muted);">최고 / 최저가 (원)</div>
            <div style="font-size: 1.2rem; font-weight: bold; margin-top: 8px;">
                <span style="color:#ff4d4f">${maxP.toLocaleString()}</span> / <span style="color:#1890ff">${minP.toLocaleString()}</span>
                <div style="font-size:0.85rem; font-weight:normal; color:var(--text-muted); margin-top:4px;">(해당 기간 평균: ${Math.round(avgP).toLocaleString()}원)</div>
            </div>
        </div>
    `;
}

function exportToCSV() {
	if (!window.currentFilteredData || window.currentFilteredData.length === 0) {
		alert("내보낼 데이터가 없습니다.");
		return;
	}

	const csvRows = ["날짜,시가,고가,저가,종가,거래량"];
	window.currentFilteredData.forEach((row) => {
		const o = row.open || row.value;
		const h = row.high || row.value;
		const l = row.low || row.value;
		const c = row.close || row.value;
		const v = row.volume || 0;
		csvRows.push(`${row.date},${o},${h},${l},${c},${v}`);
	});

	const blob = new Blob(["\uFEFF" + csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.setAttribute("href", url);
	link.setAttribute("download", `samsung_stock_data.csv`);
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
}

function renderChart(data, type) {
	const ctx = document.getElementById("stockChart").getContext("2d");
	const labels = data.map((item) => item.date);

	const gridColor = getComputedStyle(document.body).getPropertyValue("--border-color") || "rgba(0,0,0,0.1)";
	const textColor = getComputedStyle(document.body).getPropertyValue("--text-muted") || "#666";

	let datasets = [];
	let allPrices = [];

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
				pointRadius: data.length === 1 ? 6 : data.length > 50 ? 0 : 3,
				pointHoverRadius: 6,
				fill: true,
				tension: 0.4,
			},
		];
	} else {
		const boxData = [];
		const boxColors = [];
		const borderColors = [];

		data.forEach((item, index) => {
			const c = Number(item.close || item.value);
			let o = Number(item.open);

			// 1. open 데이터가 유효하지 않거나 close와 동일한 경우(단일 종가 기반 시계열):
			//    전일 종가를 시작 기준가(시가)로 설정하여 일별 등락폭(전일대비 변동)을 캔들 몸통으로 시각화
			if (!o || o === c) {
				if (index > 0) {
					o = Number(data[index - 1].close || data[index - 1].value);
				} else {
					// 기간의 첫 번째 데이터: 전체 데이터셋에서 직전 영업일 탐색
					const globalIdx = allStockData.findIndex((d) => d.date === item.date);
					if (globalIdx > 0) {
						o = Number(allStockData[globalIdx - 1].close || allStockData[globalIdx - 1].value);
					} else {
						o = c;
					}
				}
			}

			// 2. 전일과 당일 종가마저 동일하여 변동폭이 0인 경우 (보합, Doji):
			//    Chart.js는 start === end이면 높이가 0px가 되어 캔버스가 아무것도 그리지 못하므로,
			//    보합을 가시화하기 위한 최소 높이(±0.15% 또는 최소 50원)를 부여하여 Doji 가로선 형태로 렌더링
			let minVal = Math.min(o, c);
			let maxVal = Math.max(o, c);
			const isFlat = Math.abs(maxVal - minVal) < 1;

			if (isFlat) {
				const delta = Math.max(c * 0.0015, 50);
				minVal = c - delta;
				maxVal = c + delta;
			}

			allPrices.push(minVal, maxVal);
			boxData.push([minVal, maxVal]);

			// 3. 색상 결정 (한국 증시 표준: 상승 빨강 / 하락 파랑 / 보합 회색)
			if (isFlat) {
				boxColors.push("rgba(140, 140, 140, 0.85)");
				borderColors.push("#8c8c8c");
			} else if (c > o) {
				boxColors.push("rgba(255, 77, 79, 0.85)"); // 상승 (양봉 - 빨간색)
				borderColors.push("#ff4d4f");
			} else {
				boxColors.push("rgba(24, 144, 255, 0.85)"); // 하락 (음봉 - 파란색)
				borderColors.push("#1890ff");
			}
		});

		datasets = [
			{
				type: "bar",
				label: "시가-종가 변동폭 (캔들)",
				data: boxData,
				backgroundColor: boxColors,
				borderColor: borderColors,
				borderWidth: 1,
				barPercentage: data.length === 1 ? 0.3 : data.length > 100 ? 0.95 : 0.8,
				categoryPercentage: 0.9,
			},
		];
	}

	const minPrice = Math.min(...allPrices);
	const maxPrice = Math.max(...allPrices);
	const padding = (maxPrice - minPrice) * 0.05;
	const yMin = minPrice === maxPrice ? minPrice * 0.95 : minPrice - padding;
	const yMax = minPrice === maxPrice ? maxPrice * 1.05 : maxPrice + padding;

	if (stockChartInstance) stockChartInstance.destroy();

	stockChartInstance = new Chart(ctx, {
		type: type === "box" ? "bar" : "line",
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
							if (Array.isArray(context.raw)) {
								const low = Math.round(context.raw[0]).toLocaleString();
								const high = Math.round(context.raw[1]).toLocaleString();
								return `변동폭: ${low}원 ~ ${high}원`;
							}
							return `${context.dataset.label}: ${Math.round(context.raw).toLocaleString()}원`;
						},
					},
				},
			},
			scales: {
				x: { offset: true, ticks: { color: textColor, maxTicksLimit: 15 }, grid: { color: gridColor } },
				y: {
					min: yMin,
					max: yMax,
					grid: { color: gridColor },
					ticks: {
						color: textColor,
						callback: function (value) {
							return Math.round(value).toLocaleString() + "원";
						},
					},
				},
			},
		},
	});
}

async function fetchPortfolio() {
	const container = document.getElementById("portfolio-list");
	container.innerHTML = '<div style="padding:1rem; text-align:center;">데이터를 불러오는 중...</div>';
	try {
		const response = await window.API.apiFetch("/api/portfolio");
		if (response.status === "success") renderPortfolio(response.data);
	} catch (error) {
		container.innerHTML = `<div style="padding:1rem; text-align:center; color: #ff4d4f;">❌ 로딩 실패</div>`;
	}
}

function renderPortfolio(data) {
	const summaryDiv = document.getElementById("portfolio-summary");
	let totalBuy = 0,
		totalBuyQty = 0,
		totalSell = 0,
		totalSellQty = 0;

	const newListContainer = document.getElementById("portfolio-list");
	newListContainer.innerHTML = data
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

			const typeBadge = isBuy ? `<span style="background:#ff4d4f; color:white; padding:3px 8px; border-radius:12px; font-size:0.8rem; font-weight:bold;">매수</span>` : `<span style="background:#1890ff; color:white; padding:3px 8px; border-radius:12px; font-size:0.8rem; font-weight:bold;">매도</span>`;

			return `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 8px;">
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div>${typeBadge} <span style="font-size:0.9rem; color:var(--text-muted); margin-left:6px;">${item.date}</span></div>
                    <div style="font-size:1.1rem; font-weight:bold; margin-top:4px;">${item.price.toLocaleString()}원 <span style="font-size:0.9rem; font-weight:normal;">× ${item.quantity.toLocaleString()}주</span></div>
                </div>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="text-align: right;">
                        <div style="font-size:0.8rem; color:var(--text-muted);">총액</div>
                        <div style="font-weight:bold;">${total.toLocaleString()}원</div>
                    </div>
                    <button onclick="deletePortfolioItem('${item.id}')" style="background:none; border:none; color:#ff4d4f; cursor:pointer; padding:8px; border-radius:4px;" title="삭제">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>`;
		})
		.join("");

	if (data.length === 0) {
		newListContainer.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">등록된 가상 투자 기록이 없습니다.</div>`;
	}

	const currentHolding = totalBuyQty - totalSellQty;
	const realizedProfit = totalSell - totalBuy * (totalSellQty / (totalBuyQty || 1));
	const profitRate = totalSellQty > 0 ? ((realizedProfit / (totalBuy * (totalSellQty / totalBuyQty))) * 100).toFixed(2) : 0;

	summaryDiv.innerHTML = `현재 보유 수량: <span style="color:var(--primary-color)">${currentHolding}주</span> | 총 매도 수익실현: <span style="color: ${realizedProfit >= 0 ? "#ff4d4f" : "#1890ff"}">${realizedProfit.toLocaleString()}원 (${profitRate}%)</span>`;
}

async function addPortfolioItem() {
	const type = document.getElementById("port-type").value;
	const date = document.getElementById("port-date").value;
	const price = document.getElementById("port-price").value;
	const quantity = document.getElementById("port-qty").value;

	if (!date || !price || !quantity) return alert("날짜, 단가, 수량을 모두 입력해주세요.");

	try {
		const response = await window.API.apiFetch("/api/portfolio", {
			method: "POST",
			body: JSON.stringify({ trade_type: type, date: date, price: parseFloat(price), quantity: parseInt(quantity, 10) }),
		});
		if (response.status === "success") {
			document.getElementById("port-date").value = "";
			document.getElementById("port-price").value = "";
			document.getElementById("port-qty").value = "";
			fetchPortfolio();
		}
	} catch (error) {
		alert("추가 실패: " + error.message);
	}
}

async function deletePortfolioItem(id) {
	if (!confirm("정말 삭제하시겠습니까?")) return;
	try {
		const response = await window.API.apiFetch(`/api/portfolio/${id}`, { method: "DELETE" });
		if (response.status === "success") fetchPortfolio();
	} catch (error) {
		alert("삭제 실패: " + error.message);
	}
}
