/**
 * web/js/data.js
 * 주가 데이터 조회, 통계 요약, 차트 렌더링을 담당합니다.
 */

let stockChartInstance = null;
let allStockData = [];
let currentChartType = "line";
let currentFilterDays = 20;

document.addEventListener("DOMContentLoaded", () => {
	fetchAndRenderData();
	fetchPortfolio();

	document.getElementById("btn-add-portfolio").addEventListener("click", addPortfolioItem);

	document.querySelectorAll(".filter-btn").forEach((btn) => {
		btn.addEventListener("click", (e) => {
			document.querySelectorAll(".filter-btn").forEach((b) => (b.style.backgroundColor = "var(--bg-color)"));
			e.target.style.backgroundColor = "var(--hover-color)";

			currentFilterDays = parseInt(e.target.dataset.days);
			applyChartFilter(currentFilterDays);
		});
	});

	document.getElementById("chart-type").addEventListener("change", (e) => {
		currentChartType = e.target.value;
		applyChartFilter(currentFilterDays);
	});

	document.getElementById("btn-toggle-sidebar").addEventListener("click", () => {
		const sidebar = document.querySelector(".sidebar");
		sidebar.classList.toggle("collapsed");
	});

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

	// ✨ 보너스 과제: CSV 내보내기 버튼 이벤트 등록 (엑셀 한글 깨짐 방지 BOM 추가)
	const btnExport = document.getElementById("btn-export");
	if (btnExport) {
		btnExport.addEventListener("click", exportToCSV);
	}
});

async function fetchAndRenderData() {
	const summaryContainer = document.getElementById("summary-stats");
	summaryContainer.innerHTML = '<p style="padding:1rem;"><i class="fa-solid fa-spinner fa-spin"></i> 통계 및 차트를 불러오는 중...</p>';

	try {
		const cachedData = sessionStorage.getItem("stockDataCache");
		if (cachedData) {
			allStockData = JSON.parse(cachedData);
			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			applyChartFilter(currentFilterDays);
			return;
		}

		const response = await window.API.apiFetch("/api/data?limit=2500");
		if (response.status === "success" && response.data.length > 0) {
			allStockData = response.data.reverse();
			sessionStorage.setItem("stockDataCache", JSON.stringify(allStockData));

			document.querySelector('.filter-btn[data-days="20"]').style.backgroundColor = "var(--hover-color)";
			applyChartFilter(currentFilterDays);
		}
	} catch (error) {
		summaryContainer.innerHTML = `<p style="color: #ff4d4f;">❌ 로딩 실패: ${error.message}</p>`;
	}
}

async function applyChartFilter(days) {
	if (allStockData.length === 0) return;

	const filteredData = allStockData.slice(-days);
	renderChart(filteredData, currentChartType);

	try {
		const summaryResponse = await window.API.apiFetch(`/api/data/summary?limit=${days}`);
		if (summaryResponse.status === "success") {
			const s = summaryResponse.summary;
			// 상승/하락 색상 동적 지정
			const returnColor = s.return_rate > 0 ? "#ff4d4f" : s.return_rate < 0 ? "#1890ff" : "var(--text-main)";
			const currentPrice = s.current_price || s.average; // fallback

			// ✨ 확장된 요약 지표 (수익률, MDD) 화면에 렌더링
			document.getElementById("summary-stats").innerHTML = `
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">조회 기간 (${s.count}일)</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">${s.period}</div>
                </div>
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">현재 종가 (기간 평균)</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">
                        ${currentPrice.toLocaleString()}원 <span style="font-size:0.85rem; font-weight:normal; color:var(--text-muted)">(평균 ${s.average.toLocaleString()})</span>
                    </div>
                </div>
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">기간 수익률 / 최대 낙폭(MDD)</div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">
                        <span style="color:${returnColor}">${s.return_rate}%</span> / <span style="color:#1890ff">${s.mdd}%</span>
                    </div>
                </div>
                <div style="padding: 1rem; background: var(--bg-color); border-radius: 8px; border-left: 3px solid #8e44ad;">
                    <div style="font-size: 0.85rem; color: var(--text-muted);">
                        최고 / 최저가 (원)
                    </div>
                    <div style="font-size: 1rem; font-weight: bold; margin-top: 5px;">
                        <span style="color:#ff4d4f">${s.max.toLocaleString()}</span> <span style="color:var(--text-muted)">/</span> <span style="color:#1890ff">${s.min.toLocaleString()}</span>
                    </div>
                </div>
            `;
		}
	} catch (e) {
		console.error("통계 요약 로딩 실패:", e);
	}
}

/**
 * ✨ CSV 다운로드 핵심 함수
 */
function exportToCSV() {
	if (allStockData.length === 0) {
		alert("내보낼 데이터가 없습니다.");
		return;
	}

	// 현재 보고 있는 차트 기준 기간의 데이터를 내보냅니다.
	const filteredData = allStockData.slice(-currentFilterDays);
	const csvRows = ["날짜,시가,고가,저가,종가,거래량"];

	filteredData.forEach((row) => {
		const o = row.open || row.value;
		const h = row.high || row.value;
		const l = row.low || row.value;
		const c = row.close || row.value;
		const v = row.volume || 0;
		csvRows.push(`${row.date},${o},${h},${l},${c},${v}`);
	});

	// 엑셀에서 한글이 깨지지 않도록 BOM(\uFEFF)을 추가하여 Blob 생성
	const blob = new Blob(["\uFEFF" + csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
	const url = URL.createObjectURL(blob);

	const link = document.createElement("a");
	link.setAttribute("href", url);
	link.setAttribute("download", `samsung_stock_${currentFilterDays}days.csv`);
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
				barPercentage: data.length === 1 ? 0.2 : 0.9,
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
								return `${context.dataset.label}: ${Math.round(context.raw[0]).toLocaleString()}원 ~ ${Math.round(context.raw[1]).toLocaleString()}원`;
							}
							return `${context.dataset.label}: ${Math.round(context.raw).toLocaleString()}원`;
						},
					},
				},
			},
			scales: {
				x: {
					offset: true,
					ticks: { color: textColor, maxTicksLimit: 15 },
					grid: { color: gridColor },
				},
				y: {
					min: yMin,
					max: yMax,
					ticks: {
						color: textColor,
						callback: function (value) {
							return Math.round(value).toLocaleString() + "원";
						},
					},
					grid: { color: gridColor },
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
		if (response.status === "success") {
			renderPortfolio(response.data);
		}
	} catch (error) {
		container.innerHTML = `<div style="padding:1rem; text-align:center; color: #ff4d4f;">❌ 로딩 실패</div>`;
	}
}

function renderPortfolio(data) {
	const container = document.getElementById("portfolio-list");
	const summaryDiv = document.getElementById("portfolio-summary");

	let totalBuy = 0,
		totalBuyQty = 0;
	let totalSell = 0,
		totalSellQty = 0;

	container.outerHTML = `<div id="portfolio-list" style="display: flex; flex-direction: column; gap: 0.8rem; margin-top: 1rem;"></div>`;
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
            </div>
        `;
		})
		.join("");

	if (data.length === 0) {
		newListContainer.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">등록된 가상 투자 기록이 없습니다.</div>`;
	}

	const currentHolding = totalBuyQty - totalSellQty;
	const realizedProfit = totalSell - totalBuy * (totalSellQty / (totalBuyQty || 1));
	const profitRate = totalSellQty > 0 ? ((realizedProfit / (totalBuy * (totalSellQty / totalBuyQty))) * 100).toFixed(2) : 0;

	summaryDiv.innerHTML = `
        현재 보유 수량: <span style="color:var(--primary-color)">${currentHolding}주</span> | 
        총 매도 수익실현: <span style="color: ${realizedProfit >= 0 ? "#ff4d4f" : "#1890ff"}">${realizedProfit.toLocaleString()}원 (${profitRate}%)</span>
    `;
}

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
		const response = await window.API.apiFetch(`/api/portfolio/${id}`, {
			method: "DELETE",
		});

		if (response.status === "success") {
			fetchPortfolio();
		}
	} catch (error) {
		alert("삭제 실패: " + error.message);
	}
}
