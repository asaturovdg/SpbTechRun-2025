<template>
  <div class="app-container">
    <nav class="top-nav glass-effect">
      <div class="nav-content">
        <div class="brand">
          <span class="brand-accent">PRO</span>.MARKET
        </div>
        <div class="nav-links">
          <span class="active">Каталог</span>
          <span>О нас</span>
          <span>Доставка</span>
        </div>
      </div>
    </nav>

    <div class="main-content-area">
      <div class="bg-pattern"></div>
      
      <div class="content-wrapper">
        <header class="page-header">
          <h1 class="page-title">Каталог решений</h1>
          <p class="page-subtitle">Профессиональные материалы для качественного ремонта</p>
        </header>

        <div class="category-filter-container">
          <div class="category-tabs">
            <button 
              class="tab-btn" 
              :class="{ active: currentCategory === 'ALL' }"
              @click="switchCategory('ALL')"
            >
              Все товары
            </button>
            <button 
              class="tab-btn"
              :class="{ active: currentCategory === 'монтаж наливного пола' }"
              @click="switchCategory('монтаж наливного пола')"
            >
              Наливной пол
            </button>
            <button 
              class="tab-btn"
              :class="{ active: currentCategory === 'выравнивание стен' }"
              @click="switchCategory('выравнивание стен')"
            >
              Выравнивание стен
            </button>
            <button 
              class="tab-btn"
              :class="{ active: currentCategory === 'монтаж перегородок ГК и газоблоками' }"
              @click="switchCategory('монтаж перегородок ГК и газоблоками')"
            >
              Перегородки
            </button>
          </div>
        </div>

        <div class="results-bar">
          <span class="count-label">Найдено: <strong class="highlight-text">{{ filteredProducts.length }}</strong> товаров</span>
        </div>

        <div v-if="loading" class="state-container loading">
          <div class="spinner-modern"></div>
          <p>Загружаем каталог...</p>
        </div>

        <div v-else-if="error" class="state-container error">
          <div class="error-icon">✕</div>
          {{ error }}
        </div>

        <div v-else class="grid-container-wrapper">
          <transition name="grid-fade" mode="out-in">
            <div 
              v-if="filteredProducts.length" 
              class="product-grid" 
              :key="currentCategory"
            >
              <div
                class="product-card-modern"
                v-for="product in filteredProducts"
                :key="product.id"
                @click="openModal(product)"
              >
                <div class="card-image-box">
                  <div class="image-overlay"></div>
                  <img 
                    :src="getProductImage(product)"
                    alt="Product Image"
                    @error="handleImageError"
                    loading="lazy"
                  >
                </div>

                <div class="card-content">
                  <div class="vendor-pill">{{ getProductVendor(product) }}</div>
                  <h4 class="product-title" :title="product.name">{{ product.name }}</h4>
                  
                  <div class="card-price-row">
                    <span class="price-value">{{ formatPrice(product.price) }}</span>
                    <span class="price-currency">₽</span>
                  </div>

                  <div class="card-footer">
                    <button class="view-details-btn">
                      Быстрый просмотр
                      <span class="arrow">→</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="empty-state-modern" key="empty">
              <div class="empty-icon">📦</div>
              <p>В этой категории пока пусто</p>
            </div>
          </transition>
        </div>

        <transition name="modal-modern">
          <div v-if="showModal" class="modal-backdrop-modern" @click.self="closeModal">
            <div class="modal-window-modern">
              <button class="close-btn-modern" @click="closeModal">
                <span>✕</span>
              </button>

              <div class="modal-layout-modern">
                <section class="main-product-section">
                  <div class="detail-gallery">
                    <a 
                      v-if="activeProduct.url || activeProduct.link" 
                      :href="activeProduct.url || activeProduct.link" 
                      target="_blank" 
                      class="img-link-wrapper"
                      title="Перейти на страницу товара"
                    >
                      <div class="external-link-hint">↗ Перейти в магазин</div>
                      <img 
                        :src="getProductImage(activeProduct)"
                        alt="Main Product"
                        @error="handleImageError"
                      >
                    </a>
                    <div v-else class="img-wrapper-static">
                      <img 
                        :src="getProductImage(activeProduct)"
                        alt="Main Product"
                        @error="handleImageError"
                      >
                    </div>
                  </div>
                  
                  <div class="detail-info-container">
                    <div class="detail-header-block">
                      <h2 class="detail-title">{{ activeProduct.name }}</h2>
                      <div class="detail-price-row">
                        <span class="currency">₽</span>
                        <span class="amount">{{ formatPrice(activeProduct.price) }}</span>
                        <span class="unit">/ шт.</span>
                      </div>
                    </div>

                    <div class="detail-divider"></div>

                    <div class="detail-specs-block" v-if="activeProduct.raw_attributes">
                      <h4 class="block-title">Характеристики</h4>
                      <div class="specs-grid">
                        <div 
                          v-for="(value, key) in getFilteredAttributes(activeProduct.raw_attributes)" 
                          :key="key" 
                          class="spec-item"
                        >
                          <span class="spec-label">{{ key }}</span>
                          <span class="spec-dots"></span>
                          <span class="spec-value">{{ value }}</span>
                        </div>
                      </div>
                    </div>

                    <div class="detail-desc-block" v-if="activeProduct.description">
                      <h4 class="block-title">Описание</h4>
                      <p class="desc-text">{{ activeProduct.description }}</p>
                    </div>
                  </div>
                </section>

                <section class="recommendations-section">
                  <div class="rec-header">
                    <h3>С этим товаром покупают</h3>
                     <transition name="fade-quick">
                        <div v-if="submittingAll" class="status-badge sending">Сохранение...</div>
                        <div v-else-if="submitSuccess && !refreshingRecommendations" class="status-badge success">✓ Готово</div>
                        <div v-else-if="submitError" class="status-badge error">Ошибка</div>
                    </transition>
                  </div>

                  <div class="rec-body-scroll">
                    <div v-if="recommendationsLoading" class="rec-loading-state">
                      <div class="spinner-modern sm color-accent"></div>
                    </div>
                    <div v-else-if="recommendationsError" class="rec-error-state">{{ recommendationsError }}</div>
                    
                    <div v-else class="rec-list-wrapper">
                      <div 
                        v-for="rec in recommendations" 
                        :key="rec.recommended_product.id" 
                        class="rec-card-modern"
                        :class="{ 'is-selected': feedbackMap[rec.recommended_product.id] === true }"
                      >
                        <div class="rec-thumb-box">
                          <img 
                            :src="getProductImage(rec.recommended_product)"
                            @error="handleImageError"
                          >
                        </div>
                        <div class="rec-details">
                          <div class="rec-top-row">
                            <div class="rec-name" :title="rec.recommended_product.name">
                              {{ rec.recommended_product.name }}
                            </div>
                            <div class="match-ring" :style="{ '--score': rec.similarity_score }">
                               <span>{{ (rec.similarity_score * 100).toFixed(0) }}%</span>
                            </div>
                          </div>
                          <div class="rec-price-row">
                            {{ formatPrice(rec.recommended_product.price) }} ₽
                          </div>
                          
                          <div class="rec-actions-modern">
                            <button 
                              class="action-btn-modern like"
                              :class="{ active: feedbackMap[rec.recommended_product.id] === true }"
                              @click.stop="setFeedback(rec.recommended_product.id, true)"
                            >
                              <span class="icon">♥</span> 
                              <span class="text">{{ feedbackMap[rec.recommended_product.id] === true ? 'Добавлено' : 'Like' }}</span>
                            </button>
                            
                            <button 
                              class="action-btn-modern dislike"
                              :class="{ active: feedbackMap[rec.recommended_product.id] === false }"
                              @click.stop="setFeedback(rec.recommended_product.id, false)"
                              title="Не интересно"
                            >
                              <span class="icon">✕</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="rec-footer-action">
                    <button
                      class="submit-all-btn-modern"
                      :disabled="submittingAll || Object.keys(feedbackMap).length === 0"
                      @click="submitAllFeedback"
                    >
                      {{ submittingAll ? 'Обработка...' : `Сохранить выбор (${Object.keys(feedbackMap).length})` }}
                    </button>
                  </div>
                </section>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <transition name="fade-slide">
      <button 
        v-if="showBackToTop" 
        class="back-to-top-btn"
        @click="scrollToTop"
        aria-label="Вернуться наверх"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 19V5M5 12l7-7 7 7"/>
        </svg>
      </button>
    </transition>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

// --- State ---
const products = ref([])
const loading = ref(false)
const error = ref(null)

const currentCategory = ref('ALL')
const showModal = ref(false)
const activeProduct = ref(null)

const recommendations = ref([])
const recommendationsLoading = ref(false)
const recommendationsError = ref(null)

const feedbackMap = ref({}) 
const submittingAll = ref(false)
const submitSuccess = ref(false)
const submitError = ref(null)
const refreshingRecommendations = ref(false)

const showBackToTop = ref(false)

// --- Filtering ---
function switchCategory(cat) {
  currentCategory.value = cat
}

const filteredProducts = computed(() => {
  if (currentCategory.value === 'ALL') {
    return products.value
  }
  return products.value.filter(p => p.type === currentCategory.value)
})

// --- Helpers ---
function getProductImage(product) {
  if (!product) return ''
  if (product.picture_url) return product.picture_url
  if (product.raw_attributes && product.raw_attributes.picture_url) {
    return product.raw_attributes.picture_url
  }
  // Placeholder SVG
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='200' viewBox='0 0 300 200'%3E%3Crect width='300' height='200' fill='%23f0f2f5'/%3E%3Cpath d='M135.5 91.5a14.5 14.5 0 1 1 29 0 14.5 14.5 0 0 1-29 0zm-24 44l18-24 13 17 20-26 28 33H111.5z' fill='%23cbd5e1'/%3E%3C/svg%3E`
}

function getProductVendor(product) {
  if (product.vendor) return product.vendor
  if (product.raw_attributes && product.raw_attributes.vendor) {
    return product.raw_attributes.vendor
  }
  return 'PRO.BRAND'
}

function getFilteredAttributes(attributes) {
  if (!attributes) return {}
  const filtered = {}
  Object.keys(attributes).forEach(key => {
    if (key !== 'picture_url' && key !== 'int_id' && attributes[key]) {
      filtered[key] = attributes[key]
    }
  })
  return filtered
}

function formatPrice(value) {
  if (!value) return '0'
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ")
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function handleImageError(event) {
  event.target.src = getProductImage(null)
}

// --- API Calls ---
async function fetchMainProducts() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/main-products')
    if (!res.ok) throw new Error(`HTTP Code: ${res.status}`)
    products.value = await res.json()
  } catch (err) {
    console.error('Fetch error:', err)
    error.value = `Ошибка загрузки каталога`
  } finally {
    loading.value = false
  }
}

async function fetchRecommendations(productId) {
  recommendationsLoading.value = true
  recommendationsError.value = null
  try {
    const res = await fetch(`/api/recommendations/${productId}`)
    if (!res.ok) throw new Error(`HTTP Code: ${res.status}`)
    recommendations.value = await res.json()
  } catch (err) {
    console.error('Rec fetch error:', err)
    recommendationsError.value = `Не удалось загрузить рекомендации`
  } finally {
    recommendationsLoading.value = false
  }
}

async function refreshRecommendations() {
  if (!activeProduct.value) return
  refreshingRecommendations.value = true
  try {
    const res = await fetch(`/api/recommendations/${activeProduct.value.id}`)
    if (!res.ok) throw new Error(`HTTP Code: ${res.status}`)
    recommendations.value = await res.json()
    submitSuccess.value = false
    submitError.value = null
  } catch (err) {
    console.error('Refresh error:', err)
  } finally {
    refreshingRecommendations.value = false
  }
}

// --- Interaction Handlers ---
function openModal(product) {
  activeProduct.value = product
  showModal.value = true
  if (!product.url) product.url = '#' 
  
  // Reset states
  submitSuccess.value = false
  submitError.value = null
  feedbackMap.value = {}
  submittingAll.value = false
  refreshingRecommendations.value = false
  fetchRecommendations(product.id)
}

function closeModal() {
  showModal.value = false
  setTimeout(() => {
    activeProduct.value = null
    recommendations.value = []
  }, 300) 
}

function setFeedback(recommendedProductId, value) {
  if (feedbackMap.value[recommendedProductId] === value) {
    const newMap = { ...feedbackMap.value }
    delete newMap[recommendedProductId]
    feedbackMap.value = newMap
  } else {
    feedbackMap.value = { ...feedbackMap.value, [recommendedProductId]: value }
  }
}

async function submitAllFeedback() {
  if (submittingAll.value || Object.keys(feedbackMap.value).length === 0) return

  submittingAll.value = true
  submitSuccess.value = false
  submitError.value = null
  refreshingRecommendations.value = false

  try {
    const feedbackEntries = Object.entries(feedbackMap.value)
    let successCount = 0
    let errorCount = 0

    for (const [recommendedId, isRelevant] of feedbackEntries) {
      try {
        const payload = {
          product_id: activeProduct.value.id,
          recommended_product_id: Number(recommendedId),
          is_relevant: isRelevant === true
        }
        
        const res = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        
        if (res.ok) successCount++
        else errorCount++
      } catch (err) {
        errorCount++
      }
    }

    if (errorCount === 0) {
      submitSuccess.value = true
      feedbackMap.value = {} 
      await sleep(1200)
      refreshingRecommendations.value = true
      await refreshRecommendations()
    } else if (successCount > 0) {
      submitError.value = `Сохранено частично (${successCount}/${feedbackEntries.length})`
    } else {
      submitError.value = 'Ошибка при сохранении'
    }
  } catch (err) {
    submitError.value = `Системная ошибка: ${err.message}`
  } finally {
    submittingAll.value = false
  }
}

// --- Back To Top Logic ---
function handleScroll() {
  showBackToTop.value = window.scrollY > 400
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

// --- Lifecycle ---
onMounted(() => {
  fetchMainProducts()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');

:root {
  --color-primary: #0F172A; 
  --color-primary-light: #1E293B;
  --color-accent: #F59E0B; 
  --color-accent-dark: #D97706;
  --color-accent-light: #FFFBEB;
  --color-success: #10B981;
  --color-error: #EF4444;

  /* 高端背景色调整：冷调灰白 */
  --bg-main: #F0F2F5;
  --bg-card: #FFFFFF;
  --bg-secondary: #F1F5F9;
  
  --text-primary: #1E293B;
  --text-secondary: #64748B;
  --text-light: #94A3B8;
  --text-white: #FFFFFF;

  --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  --shadow-hover: 0 20px 25px -5px rgba(0, 0, 0, 0.08);
  --shadow-modal: 0 25px 50px -12px rgba(15, 23, 42, 0.25);

  --radius-md: 12px;
  --radius-lg: 16px;
  --font-main: 'Montserrat', sans-serif;
}

.app-container {
  min-height: 100vh;
  /* 垂直渐变背景，模拟天光 */
  background: linear-gradient(180deg, #F8FAFC 0%, #EFF2F6 100%);
  color: var(--text-primary);
  font-family: var(--font-main);
  display: flex;
  flex-direction: column;
  position: relative;
}

/* 高端纹理：点阵 + 双色环境光晕 */
.bg-pattern {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  
  background-image: 
    radial-gradient(#94A3B8 0.8px, transparent 0.8px),
    radial-gradient(circle at 0% 0%, rgba(15, 23, 42, 0.03) 0%, transparent 60%),
    radial-gradient(circle at 90% 90%, rgba(245, 158, 11, 0.04) 0%, transparent 50%);
    
  background-size: 24px 24px, 100% 100%, 100% 100%;
  opacity: 0.6;
}

.main-content-area {
  position: relative;
  z-index: 1;
  flex: 1;
}

.content-wrapper {
  max-width: 1320px;
  margin: 0 auto;
  padding: 40px 24px;
}

/* =========================================
   Navigation
   ========================================= */
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  transition: all 0.3s;
}

.glass-effect {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.nav-content {
  max-width: 1320px;
  margin: 0 auto;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px; 
}

.brand { font-size: 1.6rem; font-weight: 800; color: var(--color-primary); letter-spacing: -0.5px; }
.brand-accent { color: var(--color-accent); }

.nav-links { display: flex; gap: 32px; font-weight: 600; color: var(--text-secondary); }
.nav-links span { cursor: pointer; transition: color 0.3s; }
.nav-links span:hover, .nav-links span.active { color: var(--color-primary); }

.page-header { text-align: center; margin-bottom: 48px; padding-top: 20px; }
.page-title { font-size: 2.5rem; font-weight: 800; color: var(--color-primary); margin-bottom: 12px; }
.page-subtitle { font-size: 1.1rem; color: var(--text-secondary); }

/* Category Tabs */
.category-filter-container { display: flex; justify-content: center; margin-bottom: 32px; }
.category-tabs { display: inline-flex; background: var(--bg-secondary); padding: 6px; border-radius: 50px; gap: 4px; }
.tab-btn {
  padding: 10px 24px; border-radius: 40px; border: none; background: transparent;
  color: var(--text-secondary); font-weight: 600; cursor: pointer; transition: all 0.3s;
}
.tab-btn:hover:not(.active) { color: var(--color-primary); background: rgba(255,255,255,0.5); }
.tab-btn.active { background: var(--color-primary); color: var(--text-white); box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2); }

/* =========================================
   Product Grid
   ========================================= */
.results-bar { display: flex; justify-content: flex-end; margin-bottom: 24px; color: var(--text-secondary); }
.highlight-text { color: var(--color-primary); }

.grid-container-wrapper {
  min-height: 400px; 
}

.product-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); 
  gap: 32px; 
}

.grid-fade-enter-active, .grid-fade-leave-active { transition: opacity 0.25s ease; }
.grid-fade-enter-from, .grid-fade-leave-to { opacity: 0; }

.product-card-modern {
  background: var(--bg-card); border-radius: var(--radius-md); overflow: hidden;
  box-shadow: var(--shadow-card); transition: all 0.4s; cursor: pointer;
  position: relative; display: flex; flex-direction: column; border: 1px solid transparent;
}
.product-card-modern:hover { transform: translateY(-8px); box-shadow: var(--shadow-hover); border-color: rgba(245, 158, 11, 0.3); }

.card-image-box { 
  position: relative; 
  width: 100%; 
  aspect-ratio: 4/3; 
  background: #F8FAFC; 
  overflow: hidden;
  border-bottom: 1px solid #F1F5F9;
}
.card-image-box img { 
  width: 100%; height: 100%; object-fit: cover; 
  transition: transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94); 
}
.product-card-modern:hover .card-image-box img { transform: scale(1.06); }

.card-content { padding: 20px; flex: 1; display: flex; flex-direction: column; }

.vendor-pill { 
  font-size: 0.75rem; font-weight: 600; color: #94A3B8; 
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; 
}

.product-title { 
  font-size: 1.05rem; font-weight: 700; color: #1E293B; margin: 0 0 12px 0; line-height: 1.4;
  display: block; overflow: visible; white-space: normal; min-height: 4.2em; 
}

.card-price-row {
  margin-top: auto; margin-bottom: 16px;
  display: flex; align-items: baseline; gap: 4px;
}
.price-value { font-size: 1.5rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; }
.price-currency { font-size: 1rem; font-weight: 600; color: #64748B; }

.card-footer { margin-top: 0; }

.view-details-btn {
  width: 100%; padding: 12px; background: #F1F5F9; color: #475569;
  border: none; border-radius: 8px; font-weight: 600; font-size: 0.9rem;
  cursor: pointer; transition: all 0.2s ease;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.product-card-modern:hover .view-details-btn { background: #0F172A; color: #FFFFFF; }
.arrow { transition: transform 0.2s; }
.product-card-modern:hover .arrow { transform: translateX(4px); }

/* =========================================
   MODAL Styles
   ========================================= */
.modal-backdrop-modern {
  position: fixed; inset: 0; 
  background: rgba(15, 23, 42, 0.7); 
  backdrop-filter: blur(8px);
  z-index: 2000; 
  display: flex; align-items: center; justify-content: center; padding: 20px;
}

.modal-window-modern {
  width: 100%; max-width: 1100px; height: 85vh; background: var(--bg-card);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-modal);
  position: relative; overflow: hidden; display: flex; flex-direction: column;
}

.close-btn-modern {
  position: absolute; top: 20px; right: 20px; width: 36px; height: 36px;
  background: var(--bg-secondary); border: none; border-radius: 50%; cursor: pointer;
  z-index: 10; display: flex; align-items: center; justify-content: center;
  color: var(--text-secondary); transition: all 0.3s;
}
.close-btn-modern:hover { background: var(--color-error); color: white; transform: rotate(90deg); }

.modal-layout-modern { display: flex; height: 100%; overflow: hidden; }

/* Left Side: Main Product */
.main-product-section {
  flex: 3; padding: 40px; overflow-y: auto; background: #FFFFFF;
  display: flex; flex-direction: column; gap: 30px;
}

.detail-gallery {
  width: 100%; height: 300px;
  background: var(--bg-secondary); border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center; padding: 20px;
  flex-shrink: 0; position: relative;
}

.img-link-wrapper {
  display: block; width: 100%; height: 100%; position: relative;
  display: flex; align-items: center; justify-content: center;
}
.img-link-wrapper img { transition: transform 0.3s; }
.img-link-wrapper:hover img { transform: scale(1.03); cursor: pointer; }

.external-link-hint {
  position: absolute; top: 10px; right: 10px;
  background: rgba(0,0,0,0.6); color: white; padding: 4px 10px;
  border-radius: 20px; font-size: 0.8rem; font-weight: 500;
  opacity: 0; transition: opacity 0.3s; pointer-events: none;
  z-index: 5;
}
.img-link-wrapper:hover .external-link-hint { opacity: 1; }

.img-wrapper-static { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }

.detail-gallery img { max-width: 100%; max-height: 100%; object-fit: contain; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.1)); }

.detail-info-container { display: flex; flex-direction: column; }
.detail-header-block { margin-bottom: 20px; }
.detail-title { font-size: 2rem; font-weight: 800; color: var(--text-primary); line-height: 1.2; margin-bottom: 12px; }
.detail-price-row { display: flex; align-items: baseline; color: var(--color-accent); }
.detail-price-row .currency { font-size: 1.5rem; font-weight: 600; margin-right: 4px; }
.detail-price-row .amount { font-size: 2.4rem; font-weight: 800; }
.detail-price-row .unit { font-size: 1rem; color: var(--text-secondary); margin-left: 8px; }

.detail-divider { height: 1px; background: #E2E8F0; margin: 10px 0 30px 0; }
.block-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 16px; border-left: 4px solid var(--color-accent); padding-left: 10px; }

.detail-specs-block { margin-bottom: 30px; }
.specs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: x 24px; column-gap: 40px; row-gap: 12px; }
.spec-item { display: flex; align-items: baseline; font-size: 0.95rem; }
.spec-label { color: var(--text-secondary); white-space: nowrap; }
.spec-dots { flex: 1; border-bottom: 1px dotted #CBD5E1; margin: 0 8px; position: relative; top: -4px; }
.spec-value { font-weight: 600; color: var(--text-primary); text-align: right; }

.detail-desc-block { background: var(--bg-secondary); padding: 20px; border-radius: var(--radius-md); }
.desc-text { line-height: 1.8; color: var(--text-secondary); font-size: 0.95rem; }

/* Right Side: Recommendations */
.recommendations-section {
  flex: 2; min-width: 380px; background: #F8FAFC; border-left: 1px solid #E2E8F0;
  display: flex; flex-direction: column;
}

.rec-header {
  padding: 24px; border-bottom: 1px solid #E2E8F0; background: #FFFFFF;
  display: flex; justify-content: space-between; align-items: center;
}
.rec-header h3 { margin: 0; font-size: 1.1rem; font-weight: 700; }

.status-badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
.status-badge.sending { background: var(--color-accent-light); color: var(--color-accent); }
.status-badge.success { background: #DCFCE7; color: var(--color-success); }
.status-badge.error { background: #FEE2E2; color: var(--color-error); }

.rec-body-scroll { flex: 1; overflow-y: auto; padding: 24px; }

.rec-card-modern {
  display: flex; gap: 16px; background: #FFFFFF; padding: 16px;
  border-radius: var(--radius-md); box-shadow: 0 2px 5px rgba(0,0,0,0.03);
  border: 2px solid transparent; transition: all 0.3s ease; margin-bottom: 16px;
}
.rec-card-modern.is-selected {
  border-color: var(--color-accent); background: var(--color-accent-light);
}

.rec-thumb-box { width: 72px; height: 72px; flex-shrink: 0; background: var(--bg-secondary); border-radius: 8px; padding: 4px; }
.rec-thumb-box img { width: 100%; height: 100%; object-fit: contain; mix-blend-mode: multiply; }

.rec-details { flex: 1; display: flex; flex-direction: column; }
.rec-top-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
.rec-name { font-size: 0.95rem; font-weight: 600; line-height: 1.3; margin-right: 8px; }
.match-ring { width: 36px; height: 36px; border-radius: 50%; background: conic-gradient(var(--color-accent) calc(var(--score) * 100%), #E2E8F0 0); display: flex; align-items: center; justify-content: center; position: relative; }
.match-ring::after { content: ''; position: absolute; inset: 3px; background: white; border-radius: 50%; }
.match-ring span { position: relative; z-index: 1; font-size: 0.7rem; font-weight: 700; color: var(--color-accent); }
.rec-price-row { font-weight: 800; color: var(--text-primary); margin-bottom: 12px; }

.rec-actions-modern { display: flex; gap: 8px; }

.action-btn-modern {
  flex: 1; border: 1px solid #E2E8F0; padding: 10px; border-radius: 8px;
  font-weight: 600; font-size: 0.9rem; cursor: pointer;
  transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 6px;
  background: #FFFFFF; color: var(--text-secondary);
}

.action-btn-modern.like.active {
  background: #10B981; color: #FFFFFF; border-color: #10B981;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}
.action-btn-modern.like:hover:not(.active) {
  background: #FFFFFF; color: #10B981; border-color: #10B981;
}

.action-btn-modern.dislike { flex: 0 0 40px; padding: 0; }
.action-btn-modern.dislike.active {
  background: #EF4444; color: #FFFFFF; border-color: #EF4444;
}
.action-btn-modern.dislike:hover:not(.active) {
  background: #FFFFFF; color: #EF4444; border-color: #EF4444;
}

.action-btn-modern:active { transform: scale(0.98); }

.rec-footer-action { padding: 20px; background: #FFFFFF; border-top: 1px solid #E2E8F0; }

.submit-all-btn-modern {
  width: 100%; padding: 14px; border: none; border-radius: var(--radius-md);
  font-size: 1.05rem; font-weight: 700; cursor: not-allowed; transition: all 0.2s;
  background: #E2E8F0; color: #94A3B8; box-shadow: none; 
}
.submit-all-btn-modern:enabled {
  background: #2563EB; color: #FFFFFF; cursor: pointer;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}

/* Modal Animation */
.modal-modern-enter-active .modal-window-modern { animation: modalSlideIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-modern-leave-active .modal-window-modern { animation: modalSlideOut 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
@keyframes modalSlideIn { from { opacity: 0; transform: scale(0.92) translateY(20px); } to { opacity: 1; transform: scale(1) translateY(0); } }
@keyframes modalSlideOut { to { opacity: 0; transform: scale(0.96) translateY(10px); } }

.spinner-modern { width: 40px; height: 40px; border: 3px solid rgba(15, 23, 42, 0.1); border-top-color: var(--color-accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
.spinner-modern.sm { width: 24px; height: 24px; border-width: 2px; }
@keyframes spin { to { transform: rotate(360deg); } }

.state-container { text-align: center; padding: 80px 0; color: var(--text-secondary); }
.empty-state-modern { text-align: center; padding: 60px; color: var(--text-secondary); background: var(--bg-secondary); border-radius: var(--radius-md); }
.empty-icon { font-size: 3rem; margin-bottom: 16px; opacity: 0.5; }

/* =========================================
   Back to Top Button
   ========================================= */
.back-to-top-btn {
  position: fixed;
  bottom: 40px;
  right: 40px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  z-index: 900;
  cursor: pointer;
  background: var(--color-primary); 
  color: #000000;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.back-to-top-btn:hover {
  background: var(--color-accent);
  transform: translateY(-6px) scale(1.05);
  box-shadow: 0 20px 30px -10px rgba(245, 158, 11, 0.5);
}
.back-to-top-btn:active { transform: translateY(-2px) scale(0.95); }

.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.4s ease; }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(20px) scale(0.8); }

@media (max-width: 960px) {
  .modal-layout-modern { flex-direction: column; overflow-y: auto; }
  .main-product-section { flex: none; border-bottom: 1px solid #E2E8F0; padding: 30px 20px; }
  .recommendations-section { flex: none; border-left: none; background: #F8FAFC; }
  .modal-window-modern { height: 95vh; max-width: 95%; }
  .nav-links { display: none; }
  .page-title { font-size: 2rem; }
  .specs-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .back-to-top-btn {
    bottom: 24px; right: 24px; width: 48px; height: 48px;
  }
}
</style>