<template>
  <div class="container">
    <h1 class="page-title">Главная страница товаров</h1>

    <div class="results-header">
      <h3>Список товаров ({{ products.length }} товаров)</h3>
    </div>

    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else>
      <div v-if="products.length" class="product-grid">
        <div
          class="product-card"
          v-for="product in products"
          :key="product.id"
          @click="openModal(product)"
        >
          <img 
            :src="getProductImage(product)"
            alt="Изображение товара"
            @error="handleImageError"
          >
          <h4>{{ product.name }}</h4>
          <p>{{ getProductVendor(product) }}</p>
          <p class="price-highlight">{{ product.price }} ₽</p>
        </div>
      </div>
      <div v-else>
        <p>Нет данных о товарах</p>
      </div>
    </div>

    <!-- Модальное окно -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-backdrop" @click="closeModal"></div>
      <div class="modal-container">
        <div class="modal-content">
          <button class="close-btn" @click="closeModal">✕</button>
          <div class="modal-body">

            <!-- Основной товар -->
            <div class="product-detail-panel">
              <img 
                :src="getProductImage(activeProduct)"
                alt="Большое изображение товара"
                @error="handleImageError"
              >
              <h2>{{ activeProduct.name }}</h2>
              <p class="price-highlight">{{ activeProduct.price }} ₽</p>
              <div v-if="activeProduct.raw_attributes">
                <div v-for="(value, key) in getFilteredAttributes(activeProduct.raw_attributes)" 
                     :key="key">
                  <strong>{{ key }}:</strong> {{ value }}
                </div>
              </div>
            </div>

            <!-- Рекомендуемые товары -->
            <div class="recommendations-panel">
              <h3>Рекомендуемые товары</h3>

              <!-- 反馈状态显示区域 -->
              <div v-if="submittingAll" class="sending-indicator">
                Отправка...
              </div>

              <div v-if="submitSuccess && !refreshingRecommendations" class="success-indicator" style="color: green; font-weight: bold;">
                Успешно отправлено ✓
              </div>

              <div v-if="submitError" class="error-indicator" style="color: red; font-weight: bold;">
                Ошибка: {{ submitError }}
              </div>

              <!-- 重新加载推荐列表的加载状态 -->
              <div v-if="refreshingRecommendations" class="refreshing-indicator">
                <div class="loading-spinner"></div>
                Обновляем рекомендации...
              </div>

              <div v-if="recommendationsLoading">Загрузка...</div>
              <div v-else-if="recommendationsError">{{ recommendationsError }}</div>

              <div v-else class="recommendations-list">
                <div 
                  v-for="rec in recommendations" 
                  :key="rec.recommended_product.id" 
                  class="recommendation-card"
                >
                  <img 
                    :src="getProductImage(rec.recommended_product)"
                    alt="Изображение рекомендуемого товара"
                    @error="handleImageError"
                  >
                  <h4>{{ rec.recommended_product.name }}</h4>
                  <p>{{ getProductVendor(rec.recommended_product) }}</p>
                  <p class="price-highlight">{{ rec.recommended_product.price }} ₽</p>

                  <div v-if="rec.recommended_product.raw_attributes">
                    <div v-for="(value, key) in getFilteredAttributes(rec.recommended_product.raw_attributes)" 
                         :key="key">
                      <strong>{{ key }}:</strong> {{ value }}
                    </div>
                  </div>

                  <!-- Like/Dislike -->
                  <div class="feedback-buttons" @click.stop>
                    <button
                      type="button"
                      class="feedback-option"
                      :class="{ selected: feedbackMap[rec.recommended_product.id] === true }"
                      @click.stop="setFeedback(rec.recommended_product.id, true)"
                    >
                      ❤️
                    </button>

                    <button
                      type="button"
                      class="feedback-option"
                      :class="{ selected: feedbackMap[rec.recommended_product.id] === false }"
                      @click.stop="setFeedback(rec.recommended_product.id, false)"
                    >
                      💔
                    </button>
                  </div>
                </div>
              </div>

              <!-- 固定提交按钮 -->
              <div class="recommendations-footer">
                <button
                  class="submit-all-feedback-btn"
                  :disabled="submittingAll || Object.keys(feedbackMap).length === 0"
                  @click="submitAllFeedback"
                >
                  {{ submittingAll ? 'Отправка...' : `Отправить (${Object.keys(feedbackMap).length})` }}
                </button>
              </div>

            </div>

          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const products = ref([])
const loading = ref(false)
const error = ref(null)

const showModal = ref(false)
const activeProduct = ref(null)

const recommendations = ref([])
const recommendationsLoading = ref(false)
const recommendationsError = ref(null)

// ❤️💔 选择记录
const feedbackMap = ref({})  // { recommended_product_id: true/false }

// 提交状态
const submittingAll = ref(false)
const submitSuccess = ref(false)
const submitError = ref(null)

// 新加：重新加载推荐列表的状态
const refreshingRecommendations = ref(false)

function getProductImage(product) {
  if (product.picture_url) return product.picture_url
  if (product.raw_attributes && product.raw_attributes.picture_url) {
    return product.raw_attributes.picture_url
  }
  return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"%3E%3Crect width="300" height="200" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" font-family="Arial" font-size="16" fill="%23999" text-anchor="middle" dominant-baseline="middle"%3EНет изображения%3C/text%3E%3C/svg%3E'
}

function getProductVendor(product) {
  if (product.vendor) return product.vendor
  if (product.raw_attributes && product.raw_attributes.vendor) {
    return product.raw_attributes.vendor
  }
  return 'Неизвестный поставщик'
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

async function fetchMainProducts() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/main-products')
    if (!res.ok) throw new Error(`HTTP ошибка: ${res.status}`)
    products.value = await res.json()
  } catch (err) {
    console.error('Ошибка при получении товаров:', err)
    error.value = `Ошибка при получении товаров: ${err.message}`
  } finally {
    loading.value = false
  }
}

async function fetchRecommendations(productId) {
  recommendationsLoading.value = true
  recommendationsError.value = null
  try {
    const res = await fetch(`/api/recommendations/${productId}`)
    if (!res.ok) throw new Error(`HTTP ошибка: ${res.status}`)
    recommendations.value = await res.json()
  } catch (err) {
    console.error('Ошибка при получении рекомендуемых товаров:', err)
    recommendationsError.value = `Ошибка при получении рекомендуемых товаров: ${err.message}`
  } finally {
    recommendationsLoading.value = false
  }
}

// 新加：重新获取推荐列表的函数
async function refreshRecommendations() {
  if (!activeProduct.value) return
  
  refreshingRecommendations.value = true
  try {
    const res = await fetch(`/api/recommendations/${activeProduct.value.id}`)
    if (!res.ok) throw new Error(`HTTP ошибка: ${res.status}`)
    recommendations.value = await res.json()
    console.log('Рекомендации успешно обновлены')
    
    // ✅ 重要：在获取新推荐后清理提交状态
    submitSuccess.value = false
    submitError.value = null
    
  } catch (err) {
    console.error('Ошибка при обновлении рекомендаций:', err)
    // 不显示错误，保持原有推荐列表
  } finally {
    refreshingRecommendations.value = false
  }
}

// 新加：睡眠函数
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function openModal(product) {
  activeProduct.value = product
  showModal.value = true
  // 清空提交状态
  submitSuccess.value = false
  submitError.value = null
  feedbackMap.value = {}
  submittingAll.value = false
  refreshingRecommendations.value = false
  fetchRecommendations(product.id)
}

function closeModal() {
  showModal.value = false
  activeProduct.value = null
  recommendations.value = []
}

function setFeedback(recommendedProductId, value) {
  feedbackMap.value = { ...feedbackMap.value, [recommendedProductId]: value }
}

function handleImageError(event) {
  event.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"%3E%3Crect width="300" height="200" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" font-family="Arial" font-size="16" fill="%23999" text-anchor="middle" dominant-baseline="middle"%3EОшибка загрузки изображения%3C/text%3E%3C/svg%3E'
}

// ⭐ 修改后的总提交逻辑（提交后睡眠5秒并重新获取推荐）
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

    // 顺序提交每个反馈
    for (const [recommendedId, isRelevant] of feedbackEntries) {
      try {
        const payload = {
          product_id: activeProduct.value.id,
          recommended_product_id: Number(recommendedId),
          is_relevant: isRelevant === true
        }
        
        console.log('Отправка отзыва:', payload)
        
        const res = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload)
        })
        
        if (res.ok) {
          successCount++
          console.log(`Отзыв ${recommendedId} успешно отправлен`)
        } else {
          errorCount++
          const errorText = await res.text()
          console.error(`Ошибка отправки отзыва ${recommendedId}:`, res.status, errorText)
        }
      } catch (err) {
        errorCount++
        console.error(`Исключение при отправке отзыва ${recommendedId}:`, err)
      }
    }

    // 处理结果
    if (errorCount === 0) {
      submitSuccess.value = true
      feedbackMap.value = {} // 清空已提交的反馈
      
      // ✅ 新加逻辑：睡眠5秒后重新获取推荐列表
      console.log('Ожидаем 5 секунд перед обновлением рекомендаций...')
      await sleep(5000) // 睡眠5秒
      
      console.log('Начинаем обновление рекомендаций...')
      refreshingRecommendations.value = true
      await refreshRecommendations() // 重新获取推荐列表
      
    } else if (successCount > 0) {
      submitError.value = `Частично отправлено (успешно: ${successCount}, ошибок: ${errorCount})`
    } else {
      submitError.value = 'Все отправки завершились ошибкой'
    }

  } catch (err) {
    console.error('Критическая ошибка при отправке:', err)
    submitError.value = `Критическая ошибка: ${err.message}`
  } finally {
    submittingAll.value = false
  }
}

onMounted(() => {
  fetchMainProducts()
})
</script>

<style scoped>
.container {
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-title {
  text-align: center;
  margin-bottom: 24px;
  font-size: 2.5rem;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.product-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: transform 0.3s;
  padding: 16px;
}

.product-card:hover {
  transform: translateY(-4px);
}

.product-card img {
  width: 100%;
  height: 200px;
  object-fit: cover;
  display: block;
  border-radius: 8px;
  margin-bottom: 12px;
}

.modal-overlay {
  position: fixed;
  top:0; left:0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-container {
  position: relative;
  width: 90%;
  max-width: 900px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px;
  max-height: 90vh;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0,0,0,0.7);
  color: white;
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  cursor: pointer;
  z-index: 1001;
}

.modal-body {
  display: flex;
  gap: 20px;
  overflow-y: auto;
}

.product-detail-panel {
  flex: 2;
  min-width: 0;
}

.product-detail-panel img {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 12px;
  margin-bottom: 12px;
}

.recommendations-panel {
  flex: 1;
  max-width: 300px;
  min-width: 200px;
  /* 调整为 column 布局，使 footer 固定在底部 */
  display: flex;
  flex-direction: column;
  background: transparent;
  border: none;
  padding: 0;
}

.recommendations-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 这个区域是实际可滚动的推荐列表（不会包含 footer） */
.recommendations-list {
  overflow-y: auto;
  padding-right: 6px;
  /* 限制高度，以便 footer 可见；使用 calc 让其自适应 Modal 高度 */
  max-height: calc(90vh - 260px); /* 保守值，通常够用；不破坏整体布局 */
}

/* 推荐卡片样式保留你原来的风格 */
.recommendation-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px;
  font-size: 0.85rem;
  background: #fafafa;
  margin-bottom: 12px;
}

.recommendation-card img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 6px;
  margin-bottom: 8px;
}
.price-highlight {
  color: red;
  font-weight: bold;
}

.loading, .error {
  text-align: center;
  padding: 3rem;
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .modal-body {
    flex-direction: column;
  }
  .recommendations-panel {
    max-width: 100%;
    min-width: 0;
    margin-top: 20px;
  }
}

/* feedback buttons（美观版） */
.recommendation-card .feedback-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.recommendation-card .feedback-option {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  user-select: none;
  background: linear-gradient(145deg, #ffffff, #f2f2f2);
  box-shadow: 2px 2px 6px rgba(0,0,0,0.08), -1px -1px 4px rgba(255,255,255,0.9);
  font-size: 20px;
  transition: 0.15s ease-in-out;
}

.recommendation-card .feedback-option:hover {
  transform: translateY(-2px);
  box-shadow: 3px 3px 8px rgba(0,0,0,0.1), -1px -1px 6px rgba(255,255,255,1);
}

.recommendation-card .feedback-option.selected {
  background: #ffecec;
  box-shadow: inset 2px 2px 6px rgba(255,0,0,0.12), inset -2px -2px 6px rgba(255,255,255,0.9);
}

/* footer（固定在推荐面板底部，不随上方滚动） */
.recommendations-footer {
  border-top: 1px solid #eee;
  padding: 10px;
  background: #fff;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 主提交按钮 */
.recommendations-footer .submit-all-feedback-btn {
  width: 100%;
  background: #ff4d4d;
  color: #fff;
  border: none;
  padding: 10px 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}

.recommendations-footer .submit-all-feedback-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* footer 状态文本 */
.recommendations-footer .footer-sending,
.recommendations-footer .footer-success {
  font-size: 13px;
  color: #666;
  text-align: center;
}
.submit-feedback-container {
  position: sticky;
  bottom: 0;
  padding: 10px 0;
  background: #fafafa;
}

.recommendation-card .sending-indicator,
.recommendation-card .success-indicator {
  margin-top: 6px;
  font-size: 0.85rem;
  color: #666;
}

/* 状态指示器样式 */
.sending-indicator {
  background: #e3f2fd;
  color: #1565c0;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 10px;
  text-align: center;
}

.success-indicator {
  background: #e8f5e8;
  color: #2e7d32;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 10px;
  text-align: center;
  border: 1px solid #4caf50;
}

.error-indicator {
  background: #ffebee;
  color: #c62828;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 10px;
  text-align: center;
  border: 1px solid #f44336;
}

/* 新加：重新加载推荐列表的加载动画 */
.refreshing-indicator {
  background: #fff3cd;
  color: #856404;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 10px;
  text-align: center;
  border: 1px solid #ffeaa7;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #856404;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>