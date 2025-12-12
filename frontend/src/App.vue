<template>
  <div class="app-container">
    <nav class="top-nav glass-effect">
      <div class="nav-content">
        <div class="brand">
          <span class="brand-accent">PRO</span>.MARKET
        </div>
        <div class="nav-links">
          <span :class="{ active: !showWelcome && currentCategory === 'ALL' }">Каталог</span>
          <span>О нас</span>
          <span>Доставка</span>
        </div>
      </div>
    </nav>

    <transition name="page-switch" mode="out-in">
      
      <div v-if="showWelcome" class="welcome-hero-section" key="welcome">
        <div class="bg-pattern"></div>
        
        <div class="hero-content">
          <div class="brand-display">
            <h1 class="hero-brand-text">PRO.MARKET</h1>
            <p class="hero-subtitle">Профессиональные решения для вашего ремонта</p>
          </div>

          <div class="tape-viewport">
            <div class="fade-overlay left"></div>
            <div class="fade-overlay right"></div>
            
            <div 
              class="video-strip-wrapper"
              ref="videoStripWrapper"
            >
              <div 
                class="video-strip"
                :style="{ transform: `translate3d(${stripScrollX}px, 0, 0)` }" 
              >
                <div 
                  v-for="(item, index) in videoStripItems" 
                  :key="item.uniqueKey"
                  class="video-frame-card"
                  :style="getFrameCardStyle(index)"
                >
                  <img 
                    :src="item.path" 
                    @error="handleImageError" 
                    alt="Frame" 
                    draggable="false"
                  >
                </div>
              </div>
            </div>
          </div>
          <button class="enter-catalog-btn" @click="enterCatalog">
             <span>Перейти в каталог</span>
            <span class="btn-icon">→</span>
          </button>
        </div>
      </div>
      <div v-else class="main-content-area" key="catalog">
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
                   <div 
                    class="card-image-box"
                    @mousemove="handleTilt"
                    @mouseleave="resetTilt"
                  >
                     <div class="image-wrapper-3d">
                        <img 
                        :src="getProductImage(product)"
                        alt="Product Image"
                         @error="handleImageError"
                        loading="lazy"
                      >
                    </div>
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
        </div>
      </div>
    </transition>

    <transition name="modal-modern">
      <div v-if="showModal" class="modal-backdrop-modern" @click.self="closeModal">
        <div class="modal-window-modern">
          <button class="close-btn-modern" @click="closeModal">
             <span>✕</span>
          </button>

          <div class="modal-layout-modern">
            <section class="main-product-section custom-scrollbar">
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

            <section class="recommendations-section custom-scrollbar">
              <div class="rec-header">
                 <h3>С этим товаром покупают</h3>
                  <transition name="fade-quick">
                    <div v-if="submittingAll" class="status-badge sending">Сохранение...</div>
                    <div v-else-if="submitError" class="status-badge error">Ошибка</div>
                </transition>
              </div>

               <div class="rec-body-scroll relative-container" ref="recListContainer">
                
                <transition name="toast-slide">
                  <div v-if="showRefreshSuccess" class="refresh-toast">
                    <span class="toast-icon">✓</span>
                     <span class="toast-text">Список обновлён</span>
                  </div>
                </transition>

                <div v-if="recommendationsLoading" class="rec-loading-state">
                  <div class="spinner-modern sm color-accent"></div>
                 </div>

                <div v-else-if="refreshingRecommendations" class="rec-refresh-container">
                    <div class="spinner-modern color-accent"></div>
                    <p class="refresh-text">Подбираем новые рекомендации...</p>
                </div>
                
                 <div v-else-if="recommendationsError" class="rec-error-state">{{ recommendationsError }}</div>
                
                <div v-else class="rec-list-wrapper">
                  <div 
                    v-for="rec in recommendations" 
                     :key="rec.recommended_product.id" 
                    class="rec-card-modern"
                    :class="{ 
                      'is-selected-like': feedbackMap[rec.recommended_product.id] === true,
                       'is-selected-dislike': feedbackMap[rec.recommended_product.id] === false
                    }"
                  >
                    <div class="rec-thumb-box">
                      <a 
                         v-if="rec.recommended_product.url || rec.recommended_product.link"
                        :href="rec.recommended_product.url || rec.recommended_product.link"
                        target="_blank"
                        class="rec-img-link"
                        @click.stop
                      >
                         <div class="external-link-hint small-hint">↗</div>
                        <img 
                          :src="getProductImage(rec.recommended_product)"
                          @error="handleImageError"
                         >
                      </a>
                      <img 
                        v-else
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
                            <div 
                               v-if="rec.old_score !== undefined && (rec.similarity_score * 100).toFixed(0) !== (rec.old_score * 100).toFixed(0)" 
                              class="score-stack"
                            >
                               <span class="val-new">{{ (rec.similarity_score * 100).toFixed(0) }}</span>
                              <span class="val-arrow" :class="rec.similarity_score < rec.old_score ? 'text-red' : 'text-green'">
                                  {{ rec.similarity_score < rec.old_score ? '↓' : '↑' }}
                              </span>
                               <span class="val-old">{{ (rec.old_score * 100).toFixed(0) }}</span>
                            </div>
                            <span v-else>{{ (rec.similarity_score * 100).toFixed(0) }}%</span>
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
                  :disabled="submittingAll || refreshingRecommendations || Object.keys(feedbackMap).length === 0"
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

    <transition name="fade-slide">
      <button 
        v-if="showBackToTop && !showWelcome" 
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
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'

// =========================================================
// 🔧 CONFIGURATION (Welcome Screen)
// =========================================================
const VISIBLE_COUNT = 4 
const CARD_GAP = 100     
const CARD_HEIGHT = 100  
const CONFIG_FPS_FAST = 60  
const CONFIG_FPS_SLOW = 0.5   
const CONFIG_TIME_FAST = 4000 
const CONFIG_TIME_SLOW = 3000 
const CONFIG_RAMP_TIME = 4000 
// =========================================================

// --- State ---
const products = ref([])
const loading = ref(false)
const error = ref(null)

// Welcome Screen State
const showWelcome = ref(true)

// --- Tape/Marquee State ---
const pngModules = import.meta.glob('./PNG/*.png', { eager: true, import: 'default' })
const sortedImagePaths = Object.keys(pngModules)
  .sort((a, b) => {
    const numA = parseInt(a.match(/(\d+)/)?.[0] || '0')
    const numB = parseInt(b.match(/(\d+)/)?.[0] || '0')
    return numA - numB
  })
  .map(path => pngModules[path])

const videoStripWrapper = ref(null)
const stripScrollX = ref(0)
const currentSpeed = ref(0)
let scrollRAF = null
const dynamicCardWidth = ref(220)

// --- Other App State ---
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
const showRefreshSuccess = ref(false)

const showBackToTop = ref(false)

// Ref for scrolling
const recListContainer = ref(null)
const previousScores = ref({})

// --- Filtering ---
function switchCategory(cat) {
  currentCategory.value = cat
}

// --- Welcome Logic (Animation) ---

// Computed for total width
const totalItemWidth = computed(() => dynamicCardWidth.value + CARD_GAP)

function updateCardDimensions() {
  if (videoStripWrapper.value) {
    const containerWidth = Math.min(window.innerWidth, 1200) 
    const width = (containerWidth / VISIBLE_COUNT) - CARD_GAP
    dynamicCardWidth.value = Math.max(100, Math.floor(width))
  }
}

const speedFastVal = computed(() => (CONFIG_FPS_FAST * totalItemWidth.value) / 60)
const speedSlowVal = computed(() => (CONFIG_FPS_SLOW * totalItemWidth.value) / 60)

const REPEAT_COUNT = 3 
const ORIGINAL_COUNT = sortedImagePaths.length

const videoStripItems = computed(() => {
  if (ORIGINAL_COUNT === 0) return []
  const list = []
  for (let r = 0; r < REPEAT_COUNT; r++) {
    sortedImagePaths.forEach((path, idx) => {
      list.push({
        path,
        uniqueKey: `r${r}-i${idx}`
      })
    })
  }
  return list
})

function animationLoop() {
  if (!showWelcome.value) return
  stripScrollX.value -= currentSpeed.value
  const singleSetWidth = ORIGINAL_COUNT * totalItemWidth.value
  if (stripScrollX.value <= -singleSetWidth) {
    stripScrollX.value += singleSetWidth
  }
  scrollRAF = requestAnimationFrame(animationLoop)
}

async function startSpeedSequence() {
  while (showWelcome.value) {
    await rampToSpeed(speedFastVal.value, CONFIG_RAMP_TIME) 
    await sleep(CONFIG_TIME_FAST) 
    if (!showWelcome.value) break

    await rampToSpeed(speedSlowVal.value, CONFIG_RAMP_TIME)
    if (!showWelcome.value) break

    await sleep(CONFIG_TIME_SLOW)
  }
}

function rampToSpeed(target, duration) {
  return new Promise(resolve => {
    const startSpeed = currentSpeed.value
    const startTime = performance.now()
    function update() {
      if (!showWelcome.value) {
        resolve()
        return
      }
      const now = performance.now()
      const progress = Math.min((now - startTime) / duration, 1)
      
      const ease = progress < 0.5 
        ? 4 * progress * progress * progress 
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      currentSpeed.value = startSpeed + (target - startSpeed) * ease
      
      if (progress < 1) {
        requestAnimationFrame(update)
      } else {
        currentSpeed.value = target
        resolve()
      }
    }
    update()
  })
}

function getFrameCardStyle(index) {
  return {
    width: `${dynamicCardWidth.value}px`,
    height: `${CARD_HEIGHT}px`,
    marginRight: `${CARD_GAP}px`,
    transform: 'scale(1)',
    opacity: 1,
    filter: 'brightness(1)',
    zIndex: 1,
    boxShadow: 'none'
  }
}

function enterCatalog() {
  showWelcome.value = false
  if (scrollRAF) cancelAnimationFrame(scrollRAF)
  window.scrollTo({ top: 0, behavior: 'smooth' })
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
  // If it's the welcome strip images, we hide them if they fail
  if (event.target.closest('.video-strip')) {
      event.target.style.display = 'none';
      return;
  }
  // Default logic for products
  event.target.src = getProductImage(null)
}

// --- 3D Tilt Effect for Products ---
function handleTilt(e) {
  const el = e.currentTarget
  const rect = el.getBoundingClientRect()
  
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  const centerX = rect.width / 2
  const centerY = rect.height / 2
  
  const rotateX = ((y - centerY) / centerY) * -20
  const rotateY = ((x - centerX) / centerX) * 20
  
  const shineX = ((x / rect.width) * 100)
  const shineY = ((y / rect.height) * 100)

  el.style.setProperty('--rotateX', `${rotateX}deg`)
  el.style.setProperty('--rotateY', `${rotateY}deg`)
  el.style.setProperty('--shineX', `${shineX}%`)
  el.style.setProperty('--shineY', `${shineY}%`)
  el.style.setProperty('--transition-speed', '0.1s') 
}

function resetTilt(e) {
  const el = e.currentTarget
  el.style.setProperty('--rotateX', `0deg`)
  el.style.setProperty('--rotateY', `0deg`)
  el.style.setProperty('--shineX', `50%`)
  el.style.setProperty('--shineY', `50%`)
  el.style.setProperty('--transition-speed', '0.6s') 
}

// --- API Calls ---
async function fetchMainProducts() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/main-products')
    if (!res.ok) throw new Error(`HTTP Code: ${res.status}`)
    products.value = await res.json()
    
    // START NEW ANIMATION LOGIC IF WELCOME IS SHOWN
    if (showWelcome.value) {
      nextTick(() => {
         updateCardDimensions()
         // Init position
         stripScrollX.value = - (ORIGINAL_COUNT * totalItemWidth.value * 0.5)
         animationLoop()
         startSpeedSequence()
      })
    }
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

  const snapshot = {}
  if (recommendations.value && recommendations.value.length) {
    recommendations.value.forEach(rec => {
      snapshot[rec.recommended_product.id] = rec.similarity_score
    })
  }
  previousScores.value = snapshot

  try {
    const res = await fetch(`/api/recommendations/${activeProduct.value.id}`)
    if (!res.ok) throw new Error(`HTTP Code: ${res.status}`)
    
    const newData = await res.json()
    
    recommendations.value = newData.map(item => {
      const oldScore = previousScores.value[item.recommended_product.id]
      if (oldScore !== undefined) {
        return { ...item, old_score: oldScore }
      }
      return item
    })

    submitSuccess.value = false
    submitError.value = null
  } catch (err) {
    console.error('Refresh error:', err)
  }
}

// --- Interaction Handlers ---
function openModal(product) {
  activeProduct.value = product
  showModal.value = true
  document.body.style.overflow = 'hidden' 
  
  if (!product.url) product.url = '#' 
  
  submitSuccess.value = false
  submitError.value = null
  feedbackMap.value = {}
  submittingAll.value = false
  refreshingRecommendations.value = false
  showRefreshSuccess.value = false 
  previousScores.value = {}

  fetchRecommendations(product.id)
}

function closeModal() {
  showModal.value = false
  document.body.style.overflow = ''
  
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
  showRefreshSuccess.value = false

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
      submittingAll.value = false 
      if (recListContainer.value) {
        recListContainer.value.scrollTop = 0
      }
      refreshingRecommendations.value = true 
      try {
        await Promise.all([
          refreshRecommendations(),
          sleep(1500) 
        ])
      } finally {
        refreshingRecommendations.value = false
        showRefreshSuccess.value = true
        setTimeout(() => {
          showRefreshSuccess.value = false
        }, 2500)
      }

    } else if (successCount > 0) {
      submitError.value = `Сохранено частично (${successCount}/${feedbackEntries.length})`
      submittingAll.value = false
    } else {
      submitError.value = 'Ошибка при сохранении'
      submittingAll.value = false
    }
  } catch (err) {
    submitError.value = `Системная ошибка: ${err.message}`
    submittingAll.value = false
  }
}

function handleScroll() {
  showBackToTop.value = window.scrollY > 400
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  fetchMainProducts()
  window.addEventListener('scroll', handleScroll)
  window.addEventListener('resize', updateCardDimensions)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('resize', updateCardDimensions)
  document.body.style.overflow = ''
  if (scrollRAF) cancelAnimationFrame(scrollRAF)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
:root {
  --color-primary: #0F172A; 
  --color-primary-light: #1E293B;
  --color-accent: #F59E0B; 
  --color-success: #10B981;
  --color-error: #EF4444;

  --bg-main: #F0F2F5;
  --bg-card: #FFFFFF;
  --bg-secondary: #F1F5F9;
  --text-primary: #1E293B;
  --text-secondary: #64748B;
  
  --shadow-card: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
  --shadow-hover: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
  --shadow-modal: 0 25px 50px -12px rgba(15, 23, 42, 0.25);

  --radius-card: 24px;
  --font-main: 'Montserrat', sans-serif;
}

.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #F1F5F9 0%, #DEE4EA 100%);
  color: var(--text-primary);
  font-family: var(--font-main);
  display: flex;
  flex-direction: column;
}

.bg-pattern {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: 
    radial-gradient(#94A3B8 1px, transparent 1px),
    radial-gradient(circle at 0% 0%, rgba(15, 23, 42, 0.03) 0%, transparent 60%);
  background-size: 32px 32px, 100% 100%;
  opacity: 0.5;
}

.main-content-area, .welcome-hero-section { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column;
}
.content-wrapper { max-width: 1320px; margin: 0 auto; padding: 40px 24px; width: 100%; box-sizing: border-box;}

/* Navigation */
.top-nav { position: sticky;
top: 0; z-index: 100; border-bottom: 1px solid rgba(0,0,0,0.05); transition: all 0.3s; }
.glass-effect { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px);
-webkit-backdrop-filter: blur(12px); }
.nav-content { max-width: 1320px; margin: 0 auto; height: 70px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px;
}
.brand { font-size: 1.6rem; font-weight: 800; color: var(--color-primary); }
.brand-accent { color: var(--color-accent); }
.nav-links { display: flex; gap: 32px; font-weight: 600;
color: var(--text-secondary); }
.nav-links span:hover, .nav-links span.active { color: var(--color-primary); }

/* =========================================
   NEW Welcome / Hero Section Styles
   ========================================= */
.welcome-hero-section {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 70px);
  padding: 40px 20px;
  overflow: hidden; 
}

.hero-content {
  max-width: 1200px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 50px;
  position: relative;
  z-index: 2;
}

.brand-display { text-align: center; }

.hero-brand-text {
  font-size: 6rem;
  font-weight: 900;
  letter-spacing: -2px;
  margin: 0;
  color: var(--color-primary);
  text-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
  line-height: 1.1;
}

.hero-subtitle {
  font-size: 1.5rem;
  color: var(--text-secondary);
  margin-top: 16px;
  font-weight: 500;
}

/* Tape / Marquee Styles */
.tape-viewport {
  position: relative;
  width: 100%;
  height: 320px; 
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: transparent; 
}

.fade-overlay {
  position: absolute;
  top: 0; bottom: 0;
  width: 15%; 
  z-index: 20;
  pointer-events: none;
}
.fade-overlay.left { left: 0; background: linear-gradient(to right, #F0F2F5 10%, rgba(240,242,245,0) 100%); }
.fade-overlay.right { right: 0; background: linear-gradient(to left, #F0F2F5 10%, rgba(240,242,245,0) 100%); }

.video-strip-wrapper {
  width: 100%;
  max-width: 1200px; 
  height: 100%;
  display: flex;
  align-items: center;
  perspective: 1000px; 
}

.video-strip {
  display: flex;
  align-items: center;
  height: 100%;
  will-change: transform;
  backface-visibility: hidden;
  flex-wrap: nowrap; 
}

.video-frame-card {
  /* Flex shrink 0 is critical for the strip */
  flex-shrink: 0;
  border-radius: 12px;
  background: #fff; 
  overflow: visible; 
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translate3d(0,0,0);
  backface-visibility: hidden;
}

.video-frame-card img {
  width: 100%;
  height: 100%;
  object-fit: contain; 
  display: block;
  image-rendering: -webkit-optimize-contrast;
  image-rendering: high-quality;
}

/* Button */
.enter-catalog-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  padding: 16px 48px;
  font-size: 1.2rem;
  font-weight: 700;
  border-radius: 50px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.3s;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.2);
  margin-top: 20px;
  z-index: 30;
}

.enter-catalog-btn:hover {
  background: var(--color-accent);
  color: var(--color-primary); 
  transform: translateY(-2px);
  box-shadow: 0 15px 30px rgba(245, 158, 11, 0.3);
}

.enter-catalog-btn .btn-icon { font-size: 1.4rem; transition: transform 0.3s; }
.enter-catalog-btn:hover .btn-icon { transform: translateX(6px);
}

/* Page Switch Transition */
.page-switch-enter-active, .page-switch-leave-active { transition: opacity 0.5s ease, transform 0.5s ease; }
.page-switch-enter-from { opacity: 0; transform: translateY(20px);
}
.page-switch-leave-to { opacity: 0; transform: translateY(-20px); }

/* Responsive for Welcome */
@media (max-width: 960px) {
  .hero-brand-text { font-size: 4rem; }
  .tape-viewport { height: 280px; }
  .nav-links { display: none; }
}

/* =========================================
   Existing App Styles (Catalog, Cards, Modal)
   ========================================= */

.page-header { text-align: center;
margin-bottom: 48px; padding-top: 20px; }
.page-title { font-size: 2.5rem; font-weight: 800; color: var(--color-primary); margin-bottom: 12px; }
.page-subtitle { font-size: 1.1rem; color: var(--text-secondary);
}

.category-filter-container { display: flex; justify-content: center; margin-bottom: 32px; }
.category-tabs { display: inline-flex; background: rgba(255,255,255,0.6); padding: 6px; border-radius: 50px; gap: 4px;
box-shadow: 0 4px 6px rgba(0,0,0,0.02); flex-wrap: wrap; justify-content: center;}
.tab-btn { padding: 10px 24px; border-radius: 40px; border: none; background: transparent;
color: var(--text-secondary); font-weight: 600; cursor: pointer; transition: all 0.3s; border: 2px solid transparent;
}

.tab-btn.active { 
  background: transparent; 
  color: var(--color-primary); 
  border-color: var(--color-primary);
}

.results-bar { display: flex; justify-content: flex-end;
margin-bottom: 24px; color: var(--text-secondary); }
.highlight-text { color: var(--color-primary); }

/* Product Grid */
.grid-container-wrapper { min-height: 400px; }
.product-grid { display: grid;
grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 40px 32px; } 

.product-card-modern {
  background: #FFFFFF;
  overflow: visible; 
  border: none;
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  transition: transform 0.3s, box-shadow 0.3s;
  cursor: pointer;
  position: relative;
  display: flex;
  flex-direction: column;
}

.product-card-modern:hover { transform: translateY(-5px);
box-shadow: var(--shadow-hover); }

.card-image-box { 
  position: relative; width: 100%; aspect-ratio: 4/3; background: #F8FAFC; 
  border-bottom: 1px solid #F1F5F9;
  border-radius: var(--radius-card) var(--radius-card) 0 0;
  overflow: visible; perspective: 800px; z-index: 1;
}

.product-card-modern:hover .card-image-box { z-index: 10;
}

.image-wrapper-3d {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  padding: 24px; box-sizing: border-box;
  transform-style: preserve-3d;
  transition: all var(--transition-speed, 0.6s) cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative; background: transparent;
  border: 2px solid transparent; border-radius: 20px;
}

.card-image-box.tilt-effect .image-wrapper-3d { transform: rotateX(var(--rotateX, 0deg)) rotateY(var(--rotateY, 0deg)); }
.image-wrapper-3d img { 
  max-width: 100%; max-height: 100%; object-fit: contain;
  mix-blend-mode: multiply;
  filter: drop-shadow(0 5px 5px rgba(0,0,0,0.05));
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), filter 0.4s ease;
  will-change: transform;
}
.card-image-box:hover .image-wrapper-3d {
  background: #FFFFFF; border-color: #E2E8F0; border-radius: 20px; overflow: hidden; 
  box-shadow: 0 15px 30px rgba(0,0,0,0.15);
  transform: translateZ(20px) rotateX(var(--rotateX, 0deg)) rotateY(var(--rotateY, 0deg));
}
.card-image-box:hover img {
  transform: scale(1.35) translateY(-10px) translateZ(40px);
  filter: drop-shadow(0 10px 10px rgba(0,0,0,0.1));
}

.card-content { 
  padding: 20px; flex: 1; display: flex; flex-direction: column; background: #FFFFFF;
  border-radius: 0 0 var(--radius-card) var(--radius-card);
  position: relative; z-index: 2; 
}

.vendor-pill { font-size: 0.75rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px; }
.product-title { font-size: 1.05rem;
font-weight: 700; color: #1E293B; margin: 0 0 12px 0; line-height: 1.4; }

.card-price-row { margin-top: auto; margin-bottom: 16px; display: flex;
align-items: baseline; gap: 4px; }
.price-value { font-size: 1.5rem; font-weight: 800; color: #0F172A; }
.price-currency { font-size: 1rem; font-weight: 600; color: #64748B;
}

.view-details-btn {
  width: 100%; padding: 12px; background: #F1F5F9; color: #475569; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;
  transition: all 0.2s ease; display: flex; align-items: center; justify-content: center; gap: 6px;
}
.product-card-modern:hover .view-details-btn { background: #0F172A; color: #FFFFFF;
}
.product-card-modern:hover .arrow { transform: translateX(4px); }

/* Modal Styles */
.modal-backdrop-modern { 
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.7); 
  backdrop-filter: blur(8px); 
  z-index: 2000; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  padding: 40px 20px 20px 20px;
}

.modal-window-modern { 
  width: 100%; 
  max-width: 1100px; 
  max-height: 85vh; 
  height: auto; 
  background: var(--bg-card); 
  border-radius: 16px; 
  box-shadow: var(--shadow-modal); 
  position: relative;
  display: flex; 
  flex-direction: column; 
  overflow: hidden; 
}

.modal-layout-modern { 
  display: flex; 
  flex: 1; 
  min-height: 0; 
  overflow: hidden;
}

.main-product-section { 
  flex: 3; 
  padding: 40px; 
  overflow-y: auto; 
  overflow-x: hidden; 
  background: #FFFFFF; 
  display: flex; 
  flex-direction: column; 
  gap: 30px;
  box-sizing: border-box;
}

.recommendations-section { 
  flex: 2; 
  min-width: 380px; 
  background: #F8FAFC; 
  border-left: 1px solid #E2E8F0; 
  display: flex; 
  flex-direction: column;
  overflow: hidden; 
}

.rec-body-scroll { 
  flex: 1; 
  overflow-y: auto; 
  overflow-x: hidden; 
  padding: 24px; 
  box-sizing: border-box;
}

.custom-scrollbar::-webkit-scrollbar { width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #CBD5E1; border-radius: 10px; }
.rec-body-scroll::-webkit-scrollbar { width: 6px; }
.rec-body-scroll::-webkit-scrollbar-track { background: transparent;
}
.rec-body-scroll::-webkit-scrollbar-thumb { background-color: #CBD5E1; border-radius: 10px; }

.close-btn-modern { position: absolute; top: 20px; right: 20px; width: 36px; height: 36px; background: var(--bg-secondary);
border: none; border-radius: 50%; cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); transition: all 0.3s;
}
.close-btn-modern:hover { background: var(--color-error); color: white; transform: rotate(90deg); }

.detail-gallery { width: 100%; height: 300px; background: var(--bg-secondary); border-radius: 12px; display: flex;
align-items: center; justify-content: center; padding: 20px; flex-shrink: 0; position: relative; box-sizing: border-box; }
.img-link-wrapper { display: flex; width: 100%; height: 100%;
align-items: center; justify-content: center; position: relative;}
.img-link-wrapper img { max-width: 100%; max-height: 100%; object-fit: contain; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.1));
transition: transform 0.3s; mix-blend-mode: multiply;}
.img-link-wrapper:hover img { transform: scale(1.05); }
.external-link-hint { position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.6);
color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; opacity: 0; transition: opacity 0.3s; pointer-events: none;
}
.img-link-wrapper:hover .external-link-hint { opacity: 1; }
.img-wrapper-static { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
}
.img-wrapper-static img { max-width: 100%; max-height: 100%; object-fit: contain; mix-blend-mode: multiply; }

.detail-info-container { display: flex; flex-direction: column; width: 100%;
}
.detail-header-block { margin-bottom: 20px; }
.detail-title { font-size: 2rem; font-weight: 800; color: var(--text-primary); margin-bottom: 12px; }
.detail-price-row { display: flex; align-items: baseline;
color: var(--color-accent); }
.detail-price-row .amount { font-size: 2.4rem; font-weight: 800; }
.detail-divider { height: 1px; background: #E2E8F0; margin: 10px 0 30px 0;
}
.block-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 16px; border-left: 4px solid var(--color-accent); padding-left: 10px; }
.detail-specs-block { margin-bottom: 30px;
}
.specs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 40px; }
.spec-item { display: flex; align-items: baseline; font-size: 0.95rem;
}
.spec-label { color: var(--text-secondary); white-space: nowrap; }
.spec-dots { flex: 1; border-bottom: 1px dotted #CBD5E1; margin: 0 8px; position: relative;
top: -4px; }
.spec-value { font-weight: 600; color: var(--text-primary); text-align: right; }
.detail-desc-block { background: var(--bg-secondary); padding: 20px; border-radius: 12px;
}
.desc-text { line-height: 1.8; color: var(--text-secondary); }

.rec-header { padding: 24px; border-bottom: 1px solid #E2E8F0; background: #FFFFFF; display: flex; justify-content: space-between;
align-items: center; flex-shrink: 0; }
.rec-header h3 { margin: 0; font-size: 1.1rem; font-weight: 700; }
.status-badge { padding: 4px 10px; border-radius: 20px;
font-size: 0.8rem; font-weight: 600; }
.status-badge.sending { background: var(--color-accent-light); color: var(--color-accent); }
.status-badge.error { background: #FEE2E2; color: var(--color-error); }
.relative-container { position: relative;
} 

.rec-refresh-container { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-secondary); animation: fadeIn 0.4s ease;
}
.refresh-text { margin-top: 16px; font-weight: 600; font-size: 0.95rem; color: var(--text-primary); text-align: center; }
@keyframes fadeIn { from { opacity: 0;
} to { opacity: 1; } }
.refresh-toast { position: absolute; top: 16px; left: 50%; transform: translateX(-50%); background: #FFFFFF;
padding: 10px 20px; border-radius: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 8px; z-index: 50;
border: 1px solid #E2E8F0; white-space: nowrap; }
.toast-icon { background: #DCFCE7; color: #10B981; width: 20px; height: 20px; border-radius: 50%; display: flex;
align-items: center; justify-content: center; font-size: 12px; font-weight: 800; flex-shrink: 0; }
.toast-text { font-size: 0.9rem; font-weight: 600; color: #10B981;
}
.toast-slide-enter-active, .toast-slide-leave-active { transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); }
.toast-slide-enter-from, .toast-slide-leave-to { opacity: 0; transform: translate(-50%, -10px);
}

.rec-card-modern { display: flex; gap: 16px; background: #FFFFFF; padding: 16px; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);
border: 2px solid transparent; transition: all 0.3s ease; margin-bottom: 16px; width: 100%; box-sizing: border-box; }

.rec-card-modern.is-selected-like { border-color: var(--color-accent); background: var(--color-accent-light);
}
.rec-card-modern.is-selected-dislike { border-color: var(--color-error); background: #FEF2F2; }

.rec-thumb-box { width: 72px; height: 72px; flex-shrink: 0; background: var(--bg-secondary); border-radius: 8px; padding: 4px;
position: relative; overflow: hidden; }
.rec-thumb-box img { width: 100%; height: 100%; object-fit: contain; mix-blend-mode: multiply; }
.rec-img-link { display: block;
width: 100%; height: 100%; position: relative; }
.rec-img-link:hover img { transform: scale(1.1); }
.rec-thumb-box .external-link-hint { top: 2px; right: 2px; padding: 0;
width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; }
.rec-details { flex: 1; display: flex; flex-direction: column;
min-width: 0; }
.rec-top-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
.rec-name { font-size: 0.95rem; font-weight: 600; line-height: 1.3; margin-right: 8px;
white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.match-ring { width: 36px; height: 36px; flex-shrink: 0; border-radius: 50%;
background: conic-gradient(var(--color-accent) calc(var(--score) * 100%), #E2E8F0 0); display: flex; align-items: center; justify-content: center; position: relative; }
.match-ring::after { content: '';
position: absolute; inset: 3px; background: white; border-radius: 50%; }
.match-ring > span { position: relative; z-index: 1; font-size: 0.7rem; font-weight: 700;
color: var(--color-accent); }
.score-stack { display: flex; flex-direction: column; align-items: center; justify-content: center; line-height: 1; position: relative; z-index: 2;
}
.val-new { font-size: 9px; font-weight: 800; color: var(--color-primary); line-height: 9px; }
.val-arrow { font-size: 8px; font-weight: 800; line-height: 8px;
margin: 1px 0; }
.val-old { font-size: 8px; color: #94A3B8; font-weight: 600; line-height: 8px; }
.text-green { color: #10B981;
} .text-red { color: #EF4444; }
.rec-price-row { font-weight: 800; color: var(--text-primary); margin-bottom: 12px; }
.rec-actions-modern { display: flex; gap: 8px;
}
.action-btn-modern { flex: 1; border: 1px solid #E2E8F0; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 0.9rem; cursor: pointer;
transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 6px; background: #FFFFFF; color: var(--text-secondary); }
.action-btn-modern.like.active { background: #10B981;
color: #FFFFFF; border-color: #10B981; }
.action-btn-modern.dislike { flex: 0 0 40px; padding: 0; }
.action-btn-modern.dislike.active { background: #EF4444; color: #FFFFFF; border-color: #EF4444;
}
.action-btn-modern:active { transform: scale(0.98); }
.rec-footer-action { padding: 20px; background: #FFFFFF; border-top: 1px solid #E2E8F0; flex-shrink: 0; }
.submit-all-btn-modern { width: 100%;
padding: 14px; border: none; border-radius: 12px; font-size: 1.05rem; font-weight: 700; cursor: not-allowed; transition: all 0.2s; background: #E2E8F0; color: #94A3B8;
}
.submit-all-btn-modern:enabled { background: #2563EB; color: #FFFFFF; cursor: pointer; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}

/* Loaders & Empty States */
.spinner-modern { width: 40px; height: 40px; border: 3px solid rgba(15, 23, 42, 0.1); border-top-color: var(--color-accent);
border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
.spinner-modern.sm { width: 24px; height: 24px; border-width: 2px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.state-container { text-align: center; padding: 80px 0; color: var(--text-secondary);
}
.empty-state-modern { text-align: center; padding: 60px; color: var(--text-secondary); background: var(--bg-secondary); border-radius: 12px; }
.empty-icon { font-size: 3rem; margin-bottom: 16px; opacity: 0.5;
}

/* Transitions */
.grid-fade-enter-active, .grid-fade-leave-active { transition: opacity 0.25s ease; }
.grid-fade-enter-from, .grid-fade-leave-to { opacity: 0;
}
.modal-modern-enter-active .modal-window-modern { animation: modalSlideIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-modern-leave-active .modal-window-modern { animation: modalSlideOut 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes modalSlideIn { from { opacity: 0; transform: scale(0.92) translateY(20px); } to { opacity: 1; transform: scale(1) translateY(0);
} }
@keyframes modalSlideOut { to { opacity: 0; transform: scale(0.96) translateY(10px); } }

.back-to-top-btn { position: fixed; bottom: 40px; right: 40px;
width: 56px; height: 56px; border-radius: 50%; border: none; z-index: 900; cursor: pointer; background: var(--color-primary); color: #000000;
box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.4); display: flex; align-items: center; justify-content: center;
transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); }
.back-to-top-btn:hover { background: var(--color-accent); transform: translateY(-6px) scale(1.05);
}
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.4s ease; }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(20px) scale(0.8);
}

@media (max-width: 960px) {
  .modal-layout-modern { flex-direction: column; overflow-y: auto; overflow-x: hidden; }
  .main-product-section { flex: none;
border-bottom: 1px solid #E2E8F0; padding: 30px 20px; }
  .recommendations-section { flex: none; border-left: none; background: #F8FAFC;
}
  .modal-window-modern { height: 90vh; max-width: 95%; max-height: 90vh; }
  .specs-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .back-to-top-btn { bottom: 24px; right: 24px; width: 48px;
height: 48px; }
}
</style>