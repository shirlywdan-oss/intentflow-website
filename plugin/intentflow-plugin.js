/**
 * Intentflow Plugin v1.1.0
 * D2C 网站搜索增强插件
 *
 * 用法：
 *   在页面中先于本脚本配置 window.IntentflowConfig，然后引入本文件。
 *
 * 配置项：
 *   apiEndpoint          搜索增强 API 地址
 *   siteId               站点标识
 *   takeoverThreshold    原搜索结果数低于等于此值则接管（默认 1）
 *   noResultsKeywords    判定为无结果的关键词列表（默认英文/印尼文常见文案）
 *   injectionSelector    增强结果注入位置（CSS 选择器）
 *   searchInputSelector  搜索框选择器
 *   searchButtonSelector 搜索按钮选择器
 *   searchFormSelector   搜索表单选择器（默认取表单祖先）
 *   resultContainerSelector 原结果容器选择器
 *   lang                 语言（默认 'auto'，自动检测浏览器语言）
 *   theme                主题：'light' 或 'dark'
 *   debug                是否输出调试日志（默认 false）
 *   openInNewTab         卡片点击是否在新标签页打开（默认 false）
 *   maxTags              系统标签最多显示数量（默认 10）
 *   enabled              是否启用插件（默认 true）
 */
(function () {
  'use strict';

  const VERSION = '1.1.0';

  // ==================== 默认配置 ====================
  const DEFAULT_CONFIG = {
    apiEndpoint: 'https://intentflow-engine-production.up.railway.app/api/search',
    siteId: 'unknown-site',
    takeoverThreshold: 1,
    noResultsKeywords: [
      'no results', 'tidak ditemukan', 'not found', 'maaf',
      '0 results', 'no products', 'produk tidak ditemukan'
    ],
    injectionSelector: '#search-results',
    searchInputSelector: '#search-input',
    searchButtonSelector: '#search-button',
    searchFormSelector: null,
    resultContainerSelector: '.product-list',
    lang: 'auto',
    theme: 'light',
    debug: false,
    openInNewTab: false,
    maxTags: 10,
    enabled: true,
  };

  // ==================== 工具函数 ====================
  const $ = (selector, context) => (context || document).querySelector(selector);
  const $$ = (selector, context) => Array.from((context || document).querySelectorAll(selector));

  function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function getSessionId() {
    try {
      const key = 'intentflow_session_id';
      let sid = sessionStorage.getItem(key);
      if (!sid) {
        sid = generateId();
        sessionStorage.setItem(key, sid);
      }
      return sid;
    } catch (e) {
      return generateId();
    }
  }

  // ==================== 合并配置 ====================
  const rawConfig = window.IntentflowConfig || {};
  const CONFIG = Object.assign({}, DEFAULT_CONFIG, rawConfig);

  const log = (level, ...args) => {
    if (!CONFIG.debug) return;
    const prefix = `[Intentflow ${VERSION}]`;
    if (level === 'error') console.error(prefix, ...args);
    else if (level === 'warn') console.warn(prefix, ...args);
    else console.log(prefix, ...args);
  };

  log('info', '配置已加载', CONFIG);

  // ==================== 样式注入 ====================
  const CSS_ID = 'intentflow-styles';

  function injectStyles() {
    if (document.getElementById(CSS_ID)) return;

    const isDark = CONFIG.theme === 'dark';
    const bg = isDark ? '#1a1a2e' : '#ffffff';
    const text = isDark ? '#e0e0e0' : '#333333';
    const border = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
    const cardBg = isDark ? '#16213e' : '#ffffff';
    const accent = '#ff758c';
    const accentLight = isDark ? 'rgba(255,117,140,0.2)' : '#fff0f3';
    const muted = isDark ? '#8888aa' : '#888888';
    const shadow = isDark ? '0 4px 20px rgba(0,0,0,0.4)' : '0 4px 20px rgba(0,0,0,0.08)';
    const scoreHigh = isDark ? '#4caf50' : '#2e7d32';
    const scoreMedium = isDark ? '#ff9800' : '#f57c00';
    const scoreLow = isDark ? '#f44336' : '#c2185b';

    const css = `
      .intentflow-enhanced-results {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background: ${bg};
        color: ${text};
        border: 1px solid ${border};
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        box-shadow: ${shadow};
        max-width: 100%;
        box-sizing: border-box;
      }
      .intentflow-header {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .intentflow-header-icon {
        font-size: 18px;
      }
      .intentflow-loading {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 16px;
        color: ${muted};
        font-size: 14px;
      }
      .intentflow-spinner {
        width: 18px;
        height: 18px;
        border: 2px solid ${accentLight};
        border-top-color: ${accent};
        border-radius: 50%;
        animation: intentflow-spin 0.8s linear infinite;
      }
      @keyframes intentflow-spin {
        to { transform: rotate(360deg); }
      }
      .intentflow-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 14px;
      }
      .intentflow-tag {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        background: ${accentLight};
        color: ${accent};
        border: 1px solid ${accentLight};
        white-space: nowrap;
      }
      .intentflow-tag-more {
        background: transparent;
        border: 1px dashed ${border};
        color: ${muted};
      }
      .intentflow-cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 14px;
      }
      .intentflow-card {
        background: ${cardBg};
        border: 1px solid ${border};
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: flex;
        flex-direction: column;
      }
      .intentflow-card:hover {
        transform: translateY(-3px);
        box-shadow: ${shadow};
      }
      .intentflow-card-image {
        width: 100%;
        height: 150px;
        object-fit: cover;
        background: ${isDark ? '#0f0f23' : '#f8f8f8'};
        display: block;
      }
      .intentflow-card-body {
        padding: 12px;
        flex: 1;
        display: flex;
        flex-direction: column;
      }
      .intentflow-card-brand {
        font-size: 11px;
        font-weight: 700;
        color: ${accent};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
      }
      .intentflow-card-title {
        font-size: 13px;
        font-weight: 600;
        line-height: 1.4;
        margin-bottom: 8px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .intentflow-card-footer {
        margin-top: auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .intentflow-card-price {
        font-size: 14px;
        font-weight: 700;
      }
      .intentflow-card-score {
        font-size: 11px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 10px;
      }
      .intentflow-card-score.high {
        background: ${isDark ? 'rgba(76,175,80,0.2)' : '#e8f5e9'};
        color: ${scoreHigh};
      }
      .intentflow-card-score.medium {
        background: ${isDark ? 'rgba(255,152,0,0.2)' : '#fff8e1'};
        color: ${scoreMedium};
      }
      .intentflow-card-score.low {
        background: ${isDark ? 'rgba(244,67,54,0.2)' : '#fce4ec'};
        color: ${scoreLow};
      }
      .intentflow-card-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid ${border};
      }
      .intentflow-card-tag {
        font-size: 10px;
        color: ${muted};
        background: ${isDark ? 'rgba(255,255,255,0.05)' : '#f5f5f5'};
        padding: 2px 6px;
        border-radius: 4px;
      }
      .intentflow-card {
        position: relative;
      }
      .intentflow-ai-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        background: #FFF3E0;
        color: #E8734A;
        padding: 4px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        z-index: 2;
      }
      .intentflow-powered {
        margin-top: 14px;
        padding-top: 10px;
        border-top: 1px solid ${border};
        font-size: 11px;
        color: ${muted};
        text-align: right;
      }
      @media (max-width: 640px) {
        .intentflow-cards {
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
        }
        .intentflow-card-image {
          height: 120px;
        }
        .intentflow-enhanced-results {
          padding: 14px;
        }
      }
    `;

    const style = document.createElement('style');
    style.id = CSS_ID;
    style.textContent = css;
    document.head.appendChild(style);
    log('debug', '样式已注入');
  }

  // ==================== 埋点上报 ====================
  function getAnalyticsUrl() {
    try {
      const url = new URL(CONFIG.apiEndpoint);
      return `${url.protocol}//${url.host}/api/analytics/event`;
    } catch {
      return CONFIG.apiEndpoint.replace(/\/search(?:\?.*)?$/, '/analytics/event');
    }
  }

  function track(event, data = {}, query = '') {
    try {
      const payload = {
        event,
        siteId: CONFIG.siteId,
        sessionId: getSessionId(),
        query: query || '',
        lang: getRequestLang(),
        timestamp: Date.now(),
        data: data || {},
      };
      const url = getAnalyticsUrl();
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });

      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, blob);
      } else {
        fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          keepalive: true,
        }).catch(() => {});
      }
      log('debug', '埋点上报', payload);
    } catch (e) {
      log('debug', '埋点失败', e);
    }
  }

  // ==================== 语言检测 ====================
  function detectLanguage() {
    const htmlLang = (document.documentElement.lang || '').toLowerCase();
    const navLang = (navigator.language || navigator.userLanguage || '').toLowerCase();

    if (htmlLang.startsWith('id') || navLang.startsWith('id')) return 'id';
    if (htmlLang.startsWith('zh') || navLang.startsWith('zh')) return 'zh';
    if (htmlLang.startsWith('en') || navLang.startsWith('en')) return 'en';
    return 'auto';
  }

  function getRequestLang() {
    return CONFIG.lang === 'auto' ? detectLanguage() : CONFIG.lang;
  }

  // ==================== 搜索监听 ====================
  function getSearchQuery() {
    const input = $(CONFIG.searchInputSelector);
    return input ? input.value.trim() : '';
  }

  function onSearchTriggered(event) {
    if (CONFIG.enabled === false) {
      log('debug', '插件已禁用，跳过增强搜索');
      return;
    }

    const query = getSearchQuery();
    if (!query) return;
    const searchId = generateId();
    log('debug', '搜索触发', { query, searchId });

    // 移除之前的增强结果
    removeEnhancedResults();

    // 等待原结果加载（优先 MutationObserver，兜底 1.5s 定时器）
    waitForOriginalResults().then((originalCount) => {
      log('debug', '原结果数量', originalCount);
      const isTakeover = checkTakeover(originalCount);

      // 记录每一次搜索，用于后端量化分析
      track('search_executed', { searchId, originalResultsCount: originalCount, isTakeover }, query);

      if (isTakeover) {
        log('info', '满足接管条件，激活增强搜索', { query, originalCount, searchId });
        activateEnhancement(query, searchId);
      } else {
        log('debug', '不满足接管条件，跳过');
      }
    });
  }

  function waitForOriginalResults() {
    return new Promise((resolve) => {
      let resolved = false;
      const container = $(CONFIG.resultContainerSelector);

      function finish(count) {
        if (resolved) return;
        resolved = true;
        if (observer) observer.disconnect();
        clearTimeout(fallbackTimer);
        resolve(count);
      }

      function checkCount() {
        const c = $(CONFIG.resultContainerSelector);
        return c ? countProducts(c) : 0;
      }

      // MutationObserver 监听原结果容器变化
      let observer = null;
      if (typeof MutationObserver !== 'undefined' && container) {
        observer = new MutationObserver(() => {
          const count = checkCount();
          if (count > 0) finish(count);
        });
        observer.observe(container, { childList: true, subtree: true });
      }

      // 兜底 1.5s 后无论如何结束
      const fallbackTimer = setTimeout(() => {
        finish(checkCount());
      }, 1500);

      // 如果已经存在结果，立即结束
      const initialCount = checkCount();
      if (initialCount > 0) {
        finish(initialCount);
      }
    });
  }

  function countProducts(container) {
    if (!container) return 0;
    // 尝试多种常见商品卡片选择器
    const selectors = [
      '.product-item', '.product-card', '.product', '[data-product-id]',
      '.item', '.goods-item', '.sku-item', '.list-item',
    ];
    for (const s of selectors) {
      const items = $$(s, container);
      if (items.length > 0) return items.length;
    }
    // 兜底：计算直接子元素数量（排除脚本、样式等）
    return Array.from(container.children).filter(
      (el) => el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE'
    ).length;
  }

  function checkNoResultsText(container) {
    if (!container) return false;
    const text = container.textContent.toLowerCase();
    const patterns = Array.isArray(CONFIG.noResultsKeywords)
      ? CONFIG.noResultsKeywords
      : DEFAULT_CONFIG.noResultsKeywords;
    return patterns.some((p) => text.includes(String(p).toLowerCase()));
  }

  function checkTakeover(originalCount) {
    const container = $(CONFIG.resultContainerSelector);
    const isEmpty = !container || container.innerText.trim() === '';
    const belowThreshold = originalCount <= CONFIG.takeoverThreshold;
    const hasNoResultsText = checkNoResultsText(container);

    log('debug', '接管判断', { isEmpty, belowThreshold, hasNoResultsText, originalCount });
    return isEmpty || belowThreshold || hasNoResultsText;
  }

  // ==================== 增强搜索激活 ====================
  async function activateEnhancement(query, searchId) {
    track('plugin_activated', { searchId }, query);
    showLoading();

    try {
      const data = await fetchEnhancedResults(query);
      const results = data.results || [];

      if (!results.length) {
        log('debug', 'API 返回空结果，不注入');
        removeEnhancedResults();
        return;
      }

      injectResults(results, data.normalizedTags || {}, query, searchId);
    } catch (e) {
      log('debug', '增强搜索失败（已静默处理）', e);
      removeEnhancedResults();
    }
  }

  async function fetchEnhancedResults(query) {
    const lang = getRequestLang();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const resp = await fetch(CONFIG.apiEndpoint, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, site_url: window.location.href }),
      });
      clearTimeout(timeoutId);

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      log('debug', 'API 返回', data);
      return {
        results: data.items || data.results || [],
        normalizedTags: data.normalized_tags || {},
      };
    } catch (e) {
      clearTimeout(timeoutId);
      if (e.name === 'AbortError') {
        log('debug', 'API 请求超时（已静默处理）');
      } else {
        log('debug', 'API 请求失败（已静默处理）', e.message);
      }
      throw e;
    }
  }

  // ==================== UI 操作 ====================
  function getInjectionTarget() {
    return $(CONFIG.injectionSelector);
  }

  function showLoading() {
    const target = getInjectionTarget();
    if (!target) return;

    const el = document.createElement('div');
    el.id = 'intentflow-loading';
    el.className = 'intentflow-enhanced-results';
    el.innerHTML = `
      <div class="intentflow-loading">
        <div class="intentflow-spinner"></div>
        <span>正在为您增强搜索结果...</span>
      </div>
    `;
    target.parentNode.insertBefore(el, target);
  }

  function removeEnhancedResults() {
    const existing = document.getElementById('intentflow-enhanced');
    if (existing) existing.remove();
    const loading = document.getElementById('intentflow-loading');
    if (loading) loading.remove();
  }

  function formatPrice(price) {
    if (typeof price === 'number') return 'Rp ' + price.toLocaleString('id-ID');
    if (typeof price === 'string' && price) return price;
    return '';
  }

  function getScoreClass(score) {
    const s = typeof score === 'number' ? score : 0;
    if (s >= 0.8) return 'high';
    if (s >= 0.5) return 'medium';
    return 'low';
  }

  function getScoreLabel(score) {
    const s = typeof score === 'number' ? score : 0;
    if (s >= 0.8) return '高度匹配';
    if (s >= 0.5) return '部分匹配';
    return '推荐';
  }

  function buildTagsHtml(normalizedTags) {
    if (!normalizedTags || typeof normalizedTags !== 'object') return '';

    const tags = [];
    Object.entries(normalizedTags).forEach(([category, values]) => {
      if (Array.isArray(values)) {
        values.forEach((value) => tags.push({ category, value: String(value) }));
      }
    });

    if (!tags.length) return '';

    const maxTags = Math.max(1, parseInt(CONFIG.maxTags, 10) || 10);
    const visible = tags.slice(0, maxTags);
    const hiddenCount = Math.max(0, tags.length - maxTags);

    const html = visible
      .map((t) => `<span class="intentflow-tag" title="${escapeHtml(t.category)}">${escapeHtml(t.value)}</span>`)
      .join('');
    const more = hiddenCount
      ? `<span class="intentflow-tag intentflow-tag-more" title="还有 ${hiddenCount} 个标签">+${hiddenCount}</span>`
      : '';

    return `<div class="intentflow-tags">${html}${more}</div>`;
  }

  function injectResults(results, normalizedTags, query, searchId) {
    removeEnhancedResults();
    const target = getInjectionTarget();
    if (!target) {
      log('warn', '注入目标元素不存在', CONFIG.injectionSelector);
      return;
    }

    const productIds = results.map((r) => r.id).filter(Boolean);
    track('results_displayed', {
      searchId,
      resultCount: results.length,
      productIds,
      normalizedTags,
    }, query);

    const container = document.createElement('div');
    container.id = 'intentflow-enhanced';
    container.className = 'intentflow-enhanced-results';

    // Header
    const header = document.createElement('div');
    header.className = 'intentflow-header';
    header.innerHTML = `<span class="intentflow-header-icon">✨</span> <span>Can't find what you're looking for? Our Smart Assistant found these for you:</span>`;
    container.appendChild(header);

    // 系统识别标签
    const tagsHtml = buildTagsHtml(normalizedTags);
    if (tagsHtml) {
      const tagsWrap = document.createElement('div');
      tagsWrap.innerHTML = tagsHtml;
      container.appendChild(tagsWrap.firstElementChild);
    }

    // Cards
    const cardsWrap = document.createElement('div');
    cardsWrap.className = 'intentflow-cards';

    results.forEach((product, idx) => {
      const card = document.createElement('div');
      card.className = 'intentflow-card';
      card.setAttribute('data-product-id', product.id || '');
      card.setAttribute('data-position', String(idx));

      const score = typeof product.match_score === 'number' ? product.match_score : 0;
      const scoreClass = getScoreClass(score);
      const scoreLabel = getScoreLabel(score);
      const priceStr = formatPrice(product.price);
      const title = product.title || product.name || '';
      const imageUrl = product.image || product.image_url || 'https://placehold.co/300x200/e0e0e0/666?text=No+Image';

      const tagsHtml = (product.tags || [])
        .slice(0, 3)
        .map((t) => `<span class="intentflow-card-tag">${escapeHtml(t)}</span>`)
        .join('');

      const aiBadgeHtml = (product.match_type === 'semantic_rewritten' || product.match_type === 'fallback_recommend')
        ? `<div class="intentflow-ai-badge">✨ AI Optimized</div>`
        : '';

      card.innerHTML = `
        ${aiBadgeHtml}
        <img class="intentflow-card-image"
             src="${escapeHtml(imageUrl)}"
             alt="${escapeHtml(title)}"
             onerror="this.src='https://placehold.co/300x200/e0e0e0/666?text=No+Image'">
        <div class="intentflow-card-body">
          <div class="intentflow-card-brand">${escapeHtml(product.brand || '')}</div>
          <div class="intentflow-card-title">${escapeHtml(title)}</div>
          <div class="intentflow-card-footer">
            <div class="intentflow-card-price">${priceStr}</div>
            <div class="intentflow-card-score ${scoreClass}">${scoreLabel}</div>
          </div>
          ${tagsHtml ? `<div class="intentflow-card-tags">${tagsHtml}</div>` : ''}
        </div>
      `;

      card.addEventListener('click', () => {
        track('result_clicked', {
          searchId,
          productId: product.id,
          position: idx,
        }, query);
        log('debug', '卡片点击', { productId: product.id, position: idx });
        // 如果 API 返回了链接则跳转，否则仅记录埋点
        if (product.link) {
          if (CONFIG.openInNewTab) {
            window.open(product.link, '_blank');
          } else {
            window.location.href = product.link;
          }
        }
      });

      cardsWrap.appendChild(card);
    });

    container.appendChild(cardsWrap);

    // Footer
    const footer = document.createElement('div');
    footer.className = 'intentflow-powered';
    footer.textContent = 'Powered by Intentflow';
    container.appendChild(footer);

    target.parentNode.insertBefore(container, target);
    log('info', '增强结果已注入', { count: results.length });
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ==================== 事件绑定 ====================
  function getSearchForm() {
    // 优先使用配置的选择器，其次尝试从搜索框/按钮向上查找 form
    if (CONFIG.searchFormSelector) {
      return $(CONFIG.searchFormSelector);
    }
    const input = $(CONFIG.searchInputSelector);
    if (input) {
      const form = input.closest('form');
      if (form) return form;
    }
    const btn = $(CONFIG.searchButtonSelector);
    if (btn) {
      const form = btn.closest('form');
      if (form) return form;
    }
    return null;
  }

  function bindEvents() {
    // 监听搜索表单 submit：不拦截原生行为，让网站自己的搜索正常执行
    const form = getSearchForm();
    if (form) {
      form.addEventListener('submit', (e) => {
        // 不调用 e.preventDefault()，保留原生提交/跳转
        onSearchTriggered(e);
      });
      log('debug', '已绑定搜索表单', form);
      return;
    }

    // 兜底：若找不到表单，仍绑定按钮点击与回车
    const searchBtn = $(CONFIG.searchButtonSelector);
    if (searchBtn) {
      searchBtn.addEventListener('click', onSearchTriggered);
      log('debug', '已绑定搜索按钮', CONFIG.searchButtonSelector);
    }

    const searchInput = $(CONFIG.searchInputSelector);
    if (searchInput) {
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          onSearchTriggered(e);
        }
      });
      log('debug', '已绑定搜索框回车', CONFIG.searchInputSelector);
    }
  }

  // ==================== 暴露外部接口 ====================
  window.Intentflow = {
    version: VERSION,
    config: CONFIG,
    setEnabled: (enabled) => {
      CONFIG.enabled = !!enabled;
      log('debug', '插件启用状态已切换', CONFIG.enabled);
      if (!CONFIG.enabled) {
        removeEnhancedResults();
      }
    },
  };

  // ==================== 初始化 ====================
  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
      bootstrap();
    }
  }

  function bootstrap() {
    try {
      injectStyles();
      bindEvents();
      log('info', 'Intentflow Plugin 初始化完成', { version: VERSION });
    } catch (e) {
      log('debug', '初始化失败（已静默处理）', e);
    }
  }

  // 启动
  init();
})();
