<template>
  <div class="container">
    <!-- 搜索栏 -->
    <header class="topbar">
      <input
        v-model="keyword"
        @keyup.enter="doSearch"
        placeholder="输入商品关键词，按回车或点击搜索"
      />
      <button @click="doSearch">🔍</button>
    </header>

    <!-- 内容区域 -->
    <main class="main-area">
      <!-- 欢迎界面 -->
      <section v-if="!searchPerformed" class="welcome">
        <div class="welcome-content">
          <h2>商品推荐系统</h2>
          <p>在搜索框中输入商品关键词开始探索</p>
          <div class="example-keywords">
            <span class="example-tag" @click="setKeyword('水泥')">水泥</span>
            <span class="example-tag" @click="setKeyword('油漆')">油漆</span>
            <span class="example-tag" @click="setKeyword('瓷砖')">瓷砖</span>
          </div>
        </div>
      </section>

      <!-- 搜索结果 -->
      <section v-else class="results">
        <div class="results-header">
          <h3>搜索结果（{{ products.length }}个商品）</h3>
          <div class="view-controls">
            <button 
              :class="{ active: viewMode === 'grid' }" 
              @click="viewMode = 'grid'"
            >网格视图</button>
            <button 
              :class="{ active: viewMode === 'list' }" 
              @click="viewMode = 'list'"
            >列表视图</button>
          </div>
        </div>
        
        <div v-if="loading" class="loading">加载中...</div>
        
        <!-- 网格视图 -->
        <div v-else-if="products.length && viewMode === 'grid'" class="product-grid">
          <div
            class="product-card"
            v-for="product in products"
            :key="product.id"
            @click="openModal(product)"
          >
            <div class="card-image">
              <img :src="product.picture_url || 'https://via.placeholder.com/300'" alt="product image" />
              <div class="image-overlay">
                <span class="view-details">查看详情</span>
              </div>
            </div>
            <div class="product-info">
              <h4 class="title">{{ product.name }}</h4>
              <p class="vendor">{{ product.vendor || '未知供应商' }}</p>
              <div class="price-section">
                <span class="price">¥{{ product.price || 0 }}</span>
                <span class="price-unit">起</span>
              </div>
              <div class="product-tags">
                <span class="tag" v-if="product.raw_attributes">有属性信息</span>
                <span class="tag stock">有库存</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 列表视图 -->
        <div v-else-if="products.length && viewMode === 'list'" class="product-list">
          <div
            class="list-item"
            v-for="product in products"
            :key="product.id"
            @click="openModal(product)"
          >
            <div class="list-image">
              <img :src="product.picture_url || 'https://via.placeholder.com/100'" alt="product image" />
            </div>
            <div class="list-info">
              <h4 class="title">{{ product.name }}</h4>
              <p class="vendor">{{ product.vendor || '未知供应商' }}</p>
              <div class="attributes" v-if="product.raw_attributes">
                <span v-for="(value, key) in product.raw_attributes" :key="key" class="attribute">
                  {{ key }}: {{ value }}
                </span>
              </div>
            </div>
            <div class="list-price">
              <span class="price">¥{{ product.price || 0 }}</span>
              <button class="view-btn">查看推荐</button>
            </div>
          </div>
        </div>
        
        <div v-else class="no-results">
          <div class="no-results-content">
            <div class="no-results-icon">🔍</div>
            <p>没有找到相关商品</p>
            <p class="suggestion">请尝试其他关键词或调整搜索条件</p>
          </div>
        </div>
      </section>
    </main>

    <!-- 商品详情弹窗 -->
    <div v-if="showModal" class="modal-overlay">
      <!-- 背景虚化层 -->
      <div class="modal-backdrop" @click="closeModal"></div>
      
      <!-- 弹窗内容 - 居中显示 -->
      <div class="modal-container">
        <div class="modal-content">
          <button class="close-btn" @click="closeModal">✕</button>
          
          <div class="modal-body">
            <!-- 左侧商品大图详情 -->
            <div class="product-detail-panel">
              <div class="product-image-large">
                <img :src="activeProduct.picture_url || 'https://via.placeholder.com/400'" alt="商品大图" />
              </div>
              <div class="product-info-large">
                <h2 class="product-title">{{ activeProduct.name }}</h2>
                <div class="price-large">¥{{ activeProduct.price || 0 }}</div>
                <div v-if="activeProduct.raw_attributes" class="product-attributes">
                  <div v-for="(value, key) in activeProduct.raw_attributes" :key="key" class="attribute-item">
                    <span class="attr-key">{{ key }}：</span>
                    <span class="attr-value">{{ value }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 右侧推荐商品面板 -->
            <div class="recommendations-panel">
              <div class="panel-header">
                <h3>推荐商品</h3>
                <span class="recommend-count">{{ recommendations.length }}个推荐</span>
              </div>
              
              <div v-if="recommendationsLoading" class="loading-panel">加载推荐中...</div>
              
              <div v-else class="recommendations-list">
                <div
                  class="recommendation-item"
                  v-for="recommendation in recommendations"
                  :key="recommendation.id"
                >
                  <div class="rec-product" @click="viewRecommendedProduct(recommendation.recommended_product)">
                    <img 
                      :src="recommendation.recommended_product.picture_url || 'https://via.placeholder.com/80'" 
                      alt="推荐商品"
                      class="rec-image"
                    />
                    <div class="rec-info">
                      <h4 class="rec-title">{{ recommendation.recommended_product.name }}</h4>
                      <div class="rec-meta">
                        <span class="rec-price">¥{{ recommendation.recommended_product.price || 0 }}</span>
                        <span class="similarity-score">相似度: {{ (recommendation.similarity_score * 100).toFixed(1) }}%</span>
                      </div>
                    </div>
                  </div>
                  
                  <div class="feedback-section">
                    <div class="feedback-label">这个推荐是否相关？</div>
                    <div class="feedback-buttons">
                      <button
                        class="feedback-btn relevant"
                        :class="{ active: selections[recommendation.id] === true }"
                        @click="setFeedback(recommendation.id, true)"
                      >
                        <span class="btn-icon">✓</span>
                        <span class="btn-text">相关</span>
                      </button>
                      <button
                        class="feedback-btn not-relevant"
                        :class="{ active: selections[recommendation.id] === false }"
                        @click="setFeedback(recommendation.id, false)"
                      >
                        <span class="btn-icon">✗</span>
                        <span class="btn-text">不相关</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 提交反馈区域 -->
              <div class="feedback-actions" v-if="hasFeedback">
                <div class="feedback-stats">
                  <span class="selected-count">已选择 {{ feedbackCount }} 个商品</span>
                </div>
                <button 
                  class="submit-feedback-btn"
                  @click="submitAllFeedback"
                  :disabled="feedbackSubmitting"
                >
                  <span v-if="feedbackSubmitting" class="loading-spinner"></span>
                  {{ feedbackSubmitting ? '提交中...' : '提交反馈' }}
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
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

const API_BASE = 'http://localhost:8000'

// 响应式数据
const keyword = ref('')
const products = ref([])
const searchPerformed = ref(false)
const loading = ref(false)
const showModal = ref(false)
const activeProduct = ref(null)
const recommendations = ref([])
const recommendationsLoading = ref(false)
const selections = reactive({})
const feedbackSubmitting = ref(false)
const viewMode = ref('grid') // 视图模式：grid | list
const containerWidth = ref(0)

// 计算属性
const hasFeedback = computed(() => {
  return Object.values(selections).some(value => value !== null)
})

const feedbackCount = computed(() => {
  return Object.values(selections).filter(value => value !== null).length
})

// 监听窗口大小变化
function updateContainerWidth() {
  const container = document.querySelector('.container')
  if (container) {
    containerWidth.value = container.clientWidth
  }
}

onMounted(() => {
  updateContainerWidth()
  window.addEventListener('resize', updateContainerWidth)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateContainerWidth)
})

// 设置关键词并搜索
function setKeyword(kw) {
  keyword.value = kw
  doSearch()
}

// 搜索商品
async function doSearch() {
  if (!keyword.value.trim()) return
  
  loading.value = true
  searchPerformed.value = true
  
  try {
    // 模拟搜索数据
    products.value = await mockSearchProducts(keyword.value)
  } catch (error) {
    console.error('搜索失败:', error)
    products.value = []
  } finally {
    loading.value = false
  }
}

// 打开模态框
async function openModal(product) {
  activeProduct.value = product
  showModal.value = true
  await loadRecommendations(product.id)
}

// 加载推荐商品
async function loadRecommendations(productId) {
  recommendationsLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/recommendations/${productId}`)
    if (!response.ok) throw new Error('获取推荐失败')
    
    const data = await response.json()
    recommendations.value = data
    
    // 初始化选择状态
    Object.keys(selections).forEach(key => delete selections[key])
    data.forEach(rec => {
      selections[rec.id] = null
    })
  } catch (error) {
    console.error('加载推荐失败:', error)
    // 使用模拟数据作为降级方案
    recommendations.value = await mockRecommendations(productId)
  } finally {
    recommendationsLoading.value = false
  }
}

// 设置反馈
function setFeedback(recommendationId, isRelevant) {
  selections[recommendationId] = isRelevant
}

// 提交所有反馈
async function submitAllFeedback() {
  if (!hasFeedback.value) return
  
  feedbackSubmitting.value = true
  
  try {
    const feedbackPromises = recommendations.value
      .filter(rec => selections[rec.id] !== null)
      .map(rec => 
        fetch(`${API_BASE}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_id: activeProduct.value.id,
            recommended_product_id: rec.recommended_product.id,
            is_relevant: selections[rec.id]
          })
        })
      )
    
    await Promise.all(feedbackPromises)
    
    // 清空选择状态
    recommendations.value.forEach(rec => {
      selections[rec.id] = null
    })
    
    alert('反馈提交成功！')
    
  } catch (error) {
    console.error('提交反馈失败:', error)
    alert('反馈提交失败，请重试')
  } finally {
    feedbackSubmitting.value = false
  }
}

// 查看推荐商品
function viewRecommendedProduct(product) {
  // 可以在这里实现查看推荐商品详情的逻辑
  console.log('查看推荐商品:', product)
}

// 关闭模态框
function closeModal() {
  showModal.value = false
  activeProduct.value = null
  recommendations.value = []
  // 清空选择状态
  Object.keys(selections).forEach(key => {
    selections[key] = null
  })
}

// 模拟搜索商品数据
async function mockSearchProducts(keyword) {
  return Array.from({ length: 20 }).map((_, i) => ({
    id: 1000 + i,
    external_id: `EXT${1000 + i}`,
    name: `${keyword} 商品 ${i + 1} - 优质${keyword}材料`,
    price: 1000 + i * 100,
    vendor: ['供应商A', '供应商B', '供应商C', '供应商D'][i % 4],
    picture_url: `https://picsum.photos/300/200?random=${i}`,
    raw_attributes: {
      材质: ['水泥', '陶瓷', '金属', '塑料'][i % 4],
      规格: `${i + 1}kg/包`,
      用途: '建筑装饰材料',
      品牌: ['品牌A', '品牌B', '品牌C'][i % 3]
    }
  }))
}

// 模拟推荐数据
async function mockRecommendations(productId) {
  return Array.from({ length: 8 }).map((_, i) => ({
    id: 2000 + i,
    similarity_score: 0.9 - i * 0.1,
    created_at: new Date().toISOString(),
    recommended_product: {
      id: 3000 + i,
      external_id: `REC${3000 + i}`,
      name: `推荐商品 ${i + 1}`,
      price: 800 + i * 80,
      picture_url: `https://picsum.photos/60/60?random=${i + 100}`,
      vendor: '推荐供应商',
      raw_attributes: {
        相似特征: `特征${i + 1}`,
        匹配度: `${85 - i * 5}%`
      }
    }
  }))
}
</script>

<style scoped>
/* 基础容器样式 */
.container {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  padding: 20px;
  max-width: 100%;
  box-sizing: border-box;
  min-height: 100vh;
  background: #f5f5f5;
}

/* 搜索栏样式 */
.topbar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.topbar input {
  flex: 1;
  padding: 12px 16px;
  font-size: 16px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  transition: border-color 0.3s;
  background: white;
}

.topbar input:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.topbar button {
  padding: 12px 20px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
  font-weight: 500;
}

.topbar button:hover {
  background: #1976D2;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3);
}

/* 欢迎界面 */
.welcome {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60vh;
  text-align: center;
}

.welcome-content h2 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 1rem;
  font-weight: 300;
}

.welcome-content p {
  font-size: 1.2rem;
  color: #7f8c8d;
  margin-bottom: 2rem;
}

.example-keywords {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.example-tag {
  padding: 0.8rem 1.5rem;
  background: white;
  border: 2px solid #e1e5e9;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 1rem;
  color: #2c3e50;
  font-weight: 500;
}

.example-tag:hover {
  background: #2196F3;
  color: white;
  border-color: #2196F3;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
}

/* 结果头部 */
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.results-header h3 {
  color: #2c3e50;
  font-size: 1.5rem;
  margin: 0;
  font-weight: 600;
}

.view-controls {
  display: flex;
  gap: 8px;
  background: #f8f9fa;
  padding: 4px;
  border-radius: 8px;
}

.view-controls button {
  padding: 8px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
  color: #6c757d;
}

.view-controls button.active {
  background: white;
  color: #2196F3;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* 网格视图 */
.product-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

.product-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e1e5e9;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.card-image {
  position: relative;
  overflow: hidden;
  height: 200px;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.product-card:hover .card-image img {
  transform: scale(1.05);
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.product-card:hover .image-overlay {
  opacity: 1;
}

.view-details {
  color: white;
  font-size: 1.1rem;
  font-weight: 500;
}

.product-info {
  padding: 16px;
}

.title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.vendor {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin: 0 0 12px 0;
}

.price-section {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 12px;
}

.price {
  font-size: 1.4rem;
  font-weight: 700;
  color: #e74c3c;
}

.price-unit {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.product-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  padding: 4px 8px;
  background: #ecf0f1;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #7f8c8d;
}

.tag.stock {
  background: #d4edda;
  color: #155724;
}

/* 列表视图 */
.product-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e1e5e9;
  cursor: pointer;
  transition: all 0.3s;
}

.list-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transform: translateX(4px);
}

.list-image img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 6px;
}

.list-info {
  flex: 1;
}

.list-info .title {
  margin: 0 0 4px 0;
}

.attributes {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.attribute {
  padding: 2px 6px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #6c757d;
}

.list-price {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.list-price .price {
  font-size: 1.2rem;
}

.view-btn {
  padding: 6px 12px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

/* 无结果状态 */
.no-results {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.no-results-content {
  text-align: center;
}

.no-results-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.no-results p {
  color: #7f8c8d;
  margin: 0.5rem 0;
}

.suggestion {
  font-size: 0.9rem;
}

/* 加载状态 */
.loading {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
  font-size: 1.1rem;
}

/* ==================== 弹窗样式 ==================== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 1001;
}

.modal-container {
  position: relative;
  z-index: 1002;
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  animation: modalAppear 0.3s ease-out;
}

@keyframes modalAppear {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.7);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1003;
  transition: all 0.3s;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.9);
  transform: scale(1.1);
}

.modal-body {
  display: flex;
  height: 80vh;
  overflow: hidden;
}

/* 左侧商品详情面板 */
.product-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px;
  background: #f8f9fa;
  border-right: 1px solid #e1e5e9;
}

.product-image-large {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 24px;
}

.product-image-large img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.product-info-large {
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.product-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px 0;
  line-height: 1.3;
}

.price-large {
  font-size: 2rem;
  font-weight: 700;
  color: #e74c3c;
  margin-bottom: 20px;
}

.product-attributes {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.attribute-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f1f1f1;
}

.attr-key {
  font-weight: 600;
  color: #2c3e50;
  min-width: 80px;
}

.attr-value {
  color: #7f8c8d;
  text-align: right;
}

/* 右侧推荐面板 */
.recommendations-panel {
  width: 400px;
  display: flex;
  flex-direction: column;
  background: white;
}

.panel-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid #e1e5e9;
  background: #f8f9fa;
}

.panel-header h3 {
  margin: 0 0 8px 0;
  font-size: 1.3rem;
  color: #2c3e50;
  font-weight: 600;
}

.recommend-count {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.recommendations-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.recommendation-item {
  padding: 16px;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  margin-bottom: 12px;
  background: white;
  transition: all 0.3s;
}

.recommendation-item:hover {
  border-color: #2196F3;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
}

.rec-product {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  cursor: pointer;
}

.rec-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
}

.rec-info {
  flex: 1;
  min-width: 0;
}

.rec-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 6px 0;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rec-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rec-price {
  font-size: 1rem;
  font-weight: 700;
  color: #e74c3c;
}

.similarity-score {
  font-size: 0.8rem;
  color: #7f8c8d;
  background: #f1f1f1;
  padding: 2px 6px;
  border-radius: 4px;
}

.feedback-section {
  border-top: 1px solid #f1f1f1;
  padding-top: 12px;
}

.feedback-label {
  font-size: 0.8rem;
  color: #7f8c8d;
  margin-bottom: 8px;
  font-weight: 500;
}

.feedback-buttons {
  display: flex;
  gap: 8px;
}

.feedback-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid #e1e5e9;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.9rem;
  font-weight: 500;
}

.feedback-btn.relevant:hover,
.feedback-btn.relevant.active {
  background: #d4edda;
  border-color: #28a745;
  color: #155724;
}

.feedback-btn.not-relevant:hover,
.feedback-btn.not-relevant.active {
  background: #f8d7da;
  border-color: #dc3545;
  color: #721c24;
}

.btn-icon {
  font-size: 1rem;
}

.feedback-actions {
  padding: 16px;
  border-top: 1px solid #e1e5e9;
  background: #f8f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selected-count {
  font-size: 0.9rem;
  color: #7f8c8d;
  font-weight: 500;
}

.submit-feedback-btn {
  padding: 10px 20px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.submit-feedback-btn:hover:not(:disabled) {
  background: #1976D2;
  transform: translateY(-1px);
}

.submit-feedback-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.loading-panel {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: #7f8c8d;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .modal-body {
    flex-direction: column;
    height: auto;
    max-height: 90vh;
  }
  
  .product-detail-panel {
    border-right: none;
    border-bottom: 1px solid #e1e5e9;
    max-height: 50vh;
  }
  
  .recommendations-panel {
    width: 100%;
    max-height: 40vh;
  }
}

@media (max-width: 768px) {
  .container {
    padding: 12px;
  }
  
  .product-grid {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 16px;
  }
  
  .results-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .view-controls {
    justify-content: center;
  }
  
  .modal-container {
    width: 95%;
  }
  
  .product-detail-panel {
    padding: 20px;
  }
  
  .product-info-large {
    padding: 16px;
  }
  
  .product-title {
    font-size: 1.4rem;
  }
  
  .price-large {
    font-size: 1.6rem;
  }
}

@media (max-width: 480px) {
  .product-grid {
    grid-template-columns: 1fr;
  }
  
  .topbar {
    flex-direction: column;
  }
  
  .modal-body {
    padding: 16px;
  }
  
  .rec-product {
    flex-direction: column;
    text-align: center;
  }
  
  .rec-image {
    align-self: center;
  }
}
</style>