/**
 * OneSquare SVG Chart Components
 * CSS/SVG 기반 실시간 차트 시각화 시스템
 * Chart.js 대신 사용하는 경량화된 차트 라이브러리
 */

class SVGCharts {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.colors = [
            '#3788d8', '#28a745', '#ffc107', '#dc3545', '#6f42c1',
            '#20c997', '#fd7e14', '#e83e8c', '#6c757d', '#007bff'
        ];
        this.animations = true;
        this.responsive = true;
    }

    /**
     * 원형 차트 (Pie Chart)
     */
    createPieChart(data, options = {}) {
        const config = {
            width: options.width || 300,
            height: options.height || 300,
            innerRadius: options.innerRadius || 0, // 도넛 차트용
            showLabels: options.showLabels !== false,
            showLegend: options.showLegend !== false,
            title: options.title || '',
            ...options
        };

        const radius = Math.min(config.width, config.height) / 2 - 20;
        const centerX = config.width / 2;
        const centerY = config.height / 2;

        // 전체 값 계산
        const total = data.reduce((sum, item) => sum + item.value, 0);
        
        let cumulativeAngle = 0;
        let svgPaths = '';
        let legendHtml = '';

        // 각 데이터 포인트에 대한 경로 생성
        data.forEach((item, index) => {
            const percentage = (item.value / total) * 100;
            const angle = (item.value / total) * 2 * Math.PI;
            const startAngle = cumulativeAngle;
            const endAngle = cumulativeAngle + angle;

            // SVG 경로 계산
            const x1 = centerX + Math.cos(startAngle) * radius;
            const y1 = centerY + Math.sin(startAngle) * radius;
            const x2 = centerX + Math.cos(endAngle) * radius;
            const y2 = centerY + Math.sin(endAngle) * radius;

            const largeArcFlag = angle > Math.PI ? 1 : 0;

            const pathData = [
                `M ${centerX} ${centerY}`,
                `L ${x1} ${y1}`,
                `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
                'Z'
            ].join(' ');

            const color = this.colors[index % this.colors.length];
            
            svgPaths += `
                <path d="${pathData}" 
                      fill="${color}" 
                      stroke="white" 
                      stroke-width="2" 
                      class="pie-slice"
                      data-value="${item.value}"
                      data-label="${item.label}"
                      data-percentage="${percentage.toFixed(1)}"
                      style="transition: transform 0.3s ease; transform-origin: ${centerX}px ${centerY}px;"
                      onmouseover="this.style.transform='scale(1.05)'"
                      onmouseout="this.style.transform='scale(1)'"
                      onclick="showTooltip('${item.label}: ${item.value.toLocaleString()}원 (${percentage.toFixed(1)}%)')">
                </path>
            `;

            // 레이블 표시
            if (config.showLabels && percentage > 5) { // 5% 이상만 라벨 표시
                const labelAngle = startAngle + angle / 2;
                const labelRadius = radius * 0.7;
                const labelX = centerX + Math.cos(labelAngle) * labelRadius;
                const labelY = centerY + Math.sin(labelAngle) * labelRadius;

                svgPaths += `
                    <text x="${labelX}" y="${labelY}" 
                          text-anchor="middle" 
                          dominant-baseline="middle"
                          fill="white"
                          font-size="12"
                          font-weight="bold">
                        ${percentage.toFixed(1)}%
                    </text>
                `;
            }

            // 범례 생성
            if (config.showLegend) {
                legendHtml += `
                    <div class="chart-legend-item" style="display: flex; align-items: center; margin: 5px 0;">
                        <div style="width: 16px; height: 16px; background: ${color}; margin-right: 8px; border-radius: 3px;"></div>
                        <span style="font-size: 14px;">${item.label} (${percentage.toFixed(1)}%)</span>
                    </div>
                `;
            }

            cumulativeAngle += angle;
        });

        // 도넛 차트 중앙 구멍
        if (config.innerRadius > 0) {
            svgPaths += `
                <circle cx="${centerX}" cy="${centerY}" r="${config.innerRadius}" 
                        fill="white" stroke="none"/>
            `;
        }

        // SVG 및 범례 HTML 생성
        this.container.innerHTML = `
            <div class="svg-chart-container" style="display: flex; flex-direction: column; align-items: center;">
                ${config.title ? `<h3 style="margin: 0 0 15px 0; color: #333;">${config.title}</h3>` : ''}
                <div style="display: flex; align-items: flex-start; gap: 20px;">
                    <svg width="${config.width}" height="${config.height}" class="pie-chart">
                        ${svgPaths}
                    </svg>
                    ${config.showLegend ? `<div class="chart-legend">${legendHtml}</div>` : ''}
                </div>
            </div>
        `;

        return this;
    }

    /**
     * 막대 차트 (Bar Chart)
     */
    createBarChart(data, options = {}) {
        const config = {
            width: options.width || 400,
            height: options.height || 300,
            margin: options.margin || { top: 20, right: 20, bottom: 40, left: 60 },
            showValues: options.showValues !== false,
            horizontal: options.horizontal || false,
            title: options.title || '',
            xLabel: options.xLabel || '',
            yLabel: options.yLabel || '',
            ...options
        };

        const chartWidth = config.width - config.margin.left - config.margin.right;
        const chartHeight = config.height - config.margin.top - config.margin.bottom;

        // 최대값 계산
        const maxValue = Math.max(...data.map(d => d.value));
        const yScale = chartHeight / maxValue;

        let barsHtml = '';
        let labelsHtml = '';
        
        const barWidth = chartWidth / data.length * 0.8;
        const barSpacing = chartWidth / data.length * 0.1;

        data.forEach((item, index) => {
            const barHeight = (item.value / maxValue) * chartHeight;
            const x = config.margin.left + (index * (barWidth + barSpacing)) + barSpacing;
            const y = config.margin.top + chartHeight - barHeight;
            
            const color = item.color || this.colors[index % this.colors.length];

            // 막대 생성
            barsHtml += `
                <rect x="${x}" y="${y}" 
                      width="${barWidth}" height="${barHeight}"
                      fill="${color}"
                      stroke="none"
                      class="bar-rect"
                      data-value="${item.value}"
                      data-label="${item.label}"
                      style="transition: all 0.3s ease;"
                      onmouseover="this.style.opacity='0.8'; showTooltip('${item.label}: ${item.value.toLocaleString()}')"
                      onmouseout="this.style.opacity='1'"
                      rx="3" ry="3">
                </rect>
            `;

            // 값 표시
            if (config.showValues) {
                barsHtml += `
                    <text x="${x + barWidth/2}" y="${y - 5}" 
                          text-anchor="middle" 
                          fill="#333"
                          font-size="12"
                          font-weight="bold">
                        ${item.value.toLocaleString()}
                    </text>
                `;
            }

            // X축 라벨
            labelsHtml += `
                <text x="${x + barWidth/2}" y="${config.height - 10}" 
                      text-anchor="middle" 
                      fill="#666"
                      font-size="12">
                    ${item.label}
                </text>
            `;
        });

        // Y축 그리드 및 라벨
        let gridHtml = '';
        const gridSteps = 5;
        for (let i = 0; i <= gridSteps; i++) {
            const value = (maxValue / gridSteps) * i;
            const y = config.margin.top + chartHeight - (chartHeight / gridSteps) * i;
            
            gridHtml += `
                <line x1="${config.margin.left}" y1="${y}" 
                      x2="${config.width - config.margin.right}" y2="${y}" 
                      stroke="#e0e0e0" stroke-width="1"/>
                <text x="${config.margin.left - 10}" y="${y + 4}" 
                      text-anchor="end" 
                      fill="#666"
                      font-size="11">
                    ${value.toLocaleString()}
                </text>
            `;
        }

        this.container.innerHTML = `
            <div class="svg-chart-container">
                ${config.title ? `<h3 style="margin: 0 0 15px 0; text-align: center; color: #333;">${config.title}</h3>` : ''}
                <svg width="${config.width}" height="${config.height}" class="bar-chart">
                    <!-- Y축 그리드 -->
                    ${gridHtml}
                    
                    <!-- 막대들 -->
                    ${barsHtml}
                    
                    <!-- X축 라벨들 -->
                    ${labelsHtml}
                    
                    <!-- 축 선들 -->
                    <line x1="${config.margin.left}" y1="${config.margin.top + chartHeight}" 
                          x2="${config.width - config.margin.right}" y2="${config.margin.top + chartHeight}" 
                          stroke="#333" stroke-width="2"/>
                    <line x1="${config.margin.left}" y1="${config.margin.top}" 
                          x2="${config.margin.left}" y2="${config.margin.top + chartHeight}" 
                          stroke="#333" stroke-width="2"/>
                          
                    <!-- 축 라벨 -->
                    ${config.yLabel ? `
                        <text x="20" y="${config.height/2}" 
                              text-anchor="middle" 
                              fill="#333"
                              font-size="14"
                              transform="rotate(-90, 20, ${config.height/2})">
                            ${config.yLabel}
                        </text>
                    ` : ''}
                    ${config.xLabel ? `
                        <text x="${config.width/2}" y="${config.height - 5}" 
                              text-anchor="middle" 
                              fill="#333"
                              font-size="14">
                            ${config.xLabel}
                        </text>
                    ` : ''}
                </svg>
            </div>
        `;

        return this;
    }

    /**
     * 선형 차트 (Line Chart)
     */
    createLineChart(data, options = {}) {
        const config = {
            width: options.width || 500,
            height: options.height || 300,
            margin: options.margin || { top: 20, right: 20, bottom: 40, left: 60 },
            showPoints: options.showPoints !== false,
            showArea: options.showArea || false,
            smooth: options.smooth || false,
            title: options.title || '',
            xLabel: options.xLabel || '',
            yLabel: options.yLabel || '',
            ...options
        };

        const chartWidth = config.width - config.margin.left - config.margin.right;
        const chartHeight = config.height - config.margin.top - config.margin.bottom;

        // 데이터 범위 계산
        const maxValue = Math.max(...data.map(d => d.value));
        const minValue = Math.min(...data.map(d => d.value));
        const yRange = maxValue - minValue;

        // 좌표 계산 함수
        const xScale = (index) => config.margin.left + (index / (data.length - 1)) * chartWidth;
        const yScale = (value) => config.margin.top + chartHeight - ((value - minValue) / yRange) * chartHeight;

        // 선 경로 생성
        let pathData = '';
        let pointsHtml = '';
        let areaPathData = '';

        data.forEach((item, index) => {
            const x = xScale(index);
            const y = yScale(item.value);

            if (index === 0) {
                pathData += `M ${x} ${y}`;
                if (config.showArea) {
                    areaPathData += `M ${x} ${config.margin.top + chartHeight} L ${x} ${y}`;
                }
            } else {
                if (config.smooth) {
                    // 스무딩 곡선 (간단한 구현)
                    const prevX = xScale(index - 1);
                    const prevY = yScale(data[index - 1].value);
                    const cp1x = prevX + (x - prevX) / 3;
                    const cp2x = x - (x - prevX) / 3;
                    pathData += ` C ${cp1x} ${prevY} ${cp2x} ${y} ${x} ${y}`;
                    if (config.showArea) {
                        areaPathData += ` C ${cp1x} ${prevY} ${cp2x} ${y} ${x} ${y}`;
                    }
                } else {
                    pathData += ` L ${x} ${y}`;
                    if (config.showArea) {
                        areaPathData += ` L ${x} ${y}`;
                    }
                }
            }

            // 포인트 표시
            if (config.showPoints) {
                pointsHtml += `
                    <circle cx="${x}" cy="${y}" r="4" 
                            fill="#3788d8" 
                            stroke="white" 
                            stroke-width="2"
                            class="line-point"
                            data-value="${item.value}"
                            data-label="${item.label}"
                            style="transition: r 0.3s ease;"
                            onmouseover="this.setAttribute('r', '6'); showTooltip('${item.label}: ${item.value.toLocaleString()}')"
                            onmouseout="this.setAttribute('r', '4')">
                    </circle>
                `;
            }
        });

        // 영역 채우기 완성
        if (config.showArea) {
            const lastX = xScale(data.length - 1);
            areaPathData += ` L ${lastX} ${config.margin.top + chartHeight} Z`;
        }

        // Y축 그리드 및 라벨
        let gridHtml = '';
        const gridSteps = 5;
        for (let i = 0; i <= gridSteps; i++) {
            const value = minValue + (yRange / gridSteps) * i;
            const y = yScale(value);
            
            gridHtml += `
                <line x1="${config.margin.left}" y1="${y}" 
                      x2="${config.width - config.margin.right}" y2="${y}" 
                      stroke="#e0e0e0" stroke-width="1"/>
                <text x="${config.margin.left - 10}" y="${y + 4}" 
                      text-anchor="end" 
                      fill="#666"
                      font-size="11">
                    ${value.toLocaleString()}
                </text>
            `;
        }

        // X축 라벨
        let xLabelsHtml = '';
        data.forEach((item, index) => {
            if (index % Math.ceil(data.length / 6) === 0) { // 최대 6개 라벨만 표시
                const x = xScale(index);
                xLabelsHtml += `
                    <text x="${x}" y="${config.height - 10}" 
                          text-anchor="middle" 
                          fill="#666"
                          font-size="12">
                        ${item.label}
                    </text>
                `;
            }
        });

        this.container.innerHTML = `
            <div class="svg-chart-container">
                ${config.title ? `<h3 style="margin: 0 0 15px 0; text-align: center; color: #333;">${config.title}</h3>` : ''}
                <svg width="${config.width}" height="${config.height}" class="line-chart">
                    <!-- Y축 그리드 -->
                    ${gridHtml}
                    
                    <!-- 영역 채우기 -->
                    ${config.showArea ? `
                        <path d="${areaPathData}" 
                              fill="rgba(55, 136, 216, 0.1)" 
                              stroke="none"/>
                    ` : ''}
                    
                    <!-- 선 -->
                    <path d="${pathData}" 
                          fill="none" 
                          stroke="#3788d8" 
                          stroke-width="3"
                          stroke-linecap="round"
                          stroke-linejoin="round"/>
                    
                    <!-- 포인트들 -->
                    ${pointsHtml}
                    
                    <!-- X축 라벨들 -->
                    ${xLabelsHtml}
                    
                    <!-- 축 선들 -->
                    <line x1="${config.margin.left}" y1="${config.margin.top + chartHeight}" 
                          x2="${config.width - config.margin.right}" y2="${config.margin.top + chartHeight}" 
                          stroke="#333" stroke-width="2"/>
                    <line x1="${config.margin.left}" y1="${config.margin.top}" 
                          x2="${config.margin.left}" y2="${config.margin.top + chartHeight}" 
                          stroke="#333" stroke-width="2"/>
                </svg>
            </div>
        `;

        return this;
    }

    /**
     * 통계 카드
     */
    createStatsCard(data, options = {}) {
        const config = {
            title: options.title || 'Stats',
            value: data.value || 0,
            unit: data.unit || '',
            change: data.change || 0,
            trend: data.trend || 'up', // up, down, stable
            icon: options.icon || 'chart-line',
            color: options.color || '#3788d8',
            ...options
        };

        const changeColor = config.change > 0 ? '#28a745' : config.change < 0 ? '#dc3545' : '#6c757d';
        const trendIcon = config.change > 0 ? '▲' : config.change < 0 ? '▼' : '●';

        this.container.innerHTML = `
            <div class="stats-card" style="
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border-left: 4px solid ${config.color};
                min-height: 120px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            ">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                    <h4 style="margin: 0; color: #666; font-size: 14px; font-weight: 500;">${config.title}</h4>
                    <i class="fas fa-${config.icon}" style="color: ${config.color}; font-size: 18px;"></i>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <div style="font-size: 28px; font-weight: bold; color: #333; line-height: 1;">
                        ${config.value.toLocaleString()}${config.unit}
                    </div>
                </div>
                
                <div style="display: flex; align-items: center; gap: 5px;">
                    <span style="color: ${changeColor}; font-size: 12px; font-weight: bold;">
                        ${trendIcon} ${Math.abs(config.change).toFixed(1)}%
                    </span>
                    <span style="color: #999; font-size: 12px;">vs 이전 기간</span>
                </div>
            </div>
        `;

        return this;
    }
}

/**
 * 전역 툴팁 함수
 */
function showTooltip(message) {
    // 기존 툴팁 제거
    const existingTooltip = document.getElementById('chart-tooltip');
    if (existingTooltip) {
        existingTooltip.remove();
    }

    // 새 툴팁 생성
    const tooltip = document.createElement('div');
    tooltip.id = 'chart-tooltip';
    tooltip.innerHTML = message;
    tooltip.style.cssText = `
        position: fixed;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        pointer-events: none;
        z-index: 10000;
        max-width: 200px;
    `;

    document.body.appendChild(tooltip);

    // 마우스 위치에 따라 툴팁 위치 조정
    document.addEventListener('mousemove', function(e) {
        const tooltip = document.getElementById('chart-tooltip');
        if (tooltip) {
            tooltip.style.left = (e.clientX + 10) + 'px';
            tooltip.style.top = (e.clientY - 30) + 'px';
        }
    });

    // 3초 후 자동 제거
    setTimeout(() => {
        const tooltip = document.getElementById('chart-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }, 3000);
}

// 전역으로 내보내기
window.SVGCharts = SVGCharts;