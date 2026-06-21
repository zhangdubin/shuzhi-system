<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi, type OcrResult } from '@/api/modules'

const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)
const result = ref<OcrResult | null>(null)
const previewUrl = ref<string>('')

// 内置一个最小可用的 base64 PNG（1x1 透明）作为示例
const samplePngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='

function dataUrlToFile(dataUrl: string, filename: string): File {
  const arr = dataUrl.split(',')
  const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/png'
  const bstr = atob(arr[1])
  const u8arr = new Uint8Array(bstr.length)
  for (let i = 0; i < bstr.length; i++) u8arr[i] = bstr.charCodeAt(i)
  return new File([u8arr], filename, { type: mime })
}

async function handleUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  previewUrl.value = URL.createObjectURL(file)
  await doUpload(file)
}

async function handleSample() {
  // 用示例图演示
  const file = dataUrlToFile(samplePngBase64, 'sample-invoice.png')
  previewUrl.value = samplePngBase64
  await doUpload(file)
}

async function doUpload(file: File) {
  uploading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('mode', 'real')
    const r = await invoiceOcrApi.upload(fd)
    result.value = r
    ElMessage.success(`识别成功：${r.code}（置信度 ${(r.confidence * 100).toFixed(1)}%）`)
  } catch (err) {
    console.error(err)
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div><h2>发票识别</h2><p class="page-desc">AI 智能识别发票字段，置信度 &gt; 90% 自动入库</p></div>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <div class="page-card">
          <h3 class="panel-title">上传发票</h3>

          <div class="upload-zone">
            <input ref="fileInput" type="file" accept="image/*" hidden @change="handleUpload" />
            <div v-if="!previewUrl" class="upload-empty">
              <div class="upload-icon">📷</div>
              <p>点击下方按钮上传发票图片</p>
              <p class="text-tertiary" style="font-size: 12px">支持 JPG / PNG / PDF · 单张最大 10MB</p>
            </div>
            <div v-else class="upload-preview">
              <img v-if="previewUrl.startsWith('http') || previewUrl.startsWith('blob:') || previewUrl.startsWith('data:')" :src="previewUrl" />
            </div>
          </div>

          <div class="upload-actions">
            <el-button type="primary" :loading="uploading" @click="fileInput?.click()">📁 选择文件</el-button>
            <el-button :loading="uploading" @click="handleSample">✨ 用示例图演示</el-button>
          </div>
        </div>
      </el-col>

      <el-col :span="14">
        <div class="page-card">
          <h3 class="panel-title">识别结果</h3>
          <el-skeleton v-if="uploading" :rows="6" animated />
          <el-empty v-else-if="!result" description="上传图片后查看识别结果" />
          <div v-else class="result-content">
            <div class="result-summary">
              <el-tag :type="result.verifyStatus === 'verified' ? 'success' : 'warning'">
                {{ result.verifyStatus === 'verified' ? '✓ 自动入库' : '⏳ 待人工复核' }}
              </el-tag>
              <el-tag>{{ result.code }}</el-tag>
              <el-tag type="info">置信度 {{ (result.confidence * 100).toFixed(1) }}%</el-tag>
              <el-tag :type="result.ocrStatus === 'success' ? 'success' : 'danger'" size="small">
                {{ result.ocrStatus }}
              </el-tag>
            </div>

            <el-descriptions :column="2" border style="margin-top: 12px">
              <el-descriptions-item label="发票类型">{{ result.fields.invoiceType }}</el-descriptions-item>
              <el-descriptions-item label="发票代码">{{ result.fields.invoiceCode }}</el-descriptions-item>
              <el-descriptions-item label="发票号码" :span="2">
                <strong>{{ result.fields.invoiceNo }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="开票日期">{{ result.fields.issueDate }}</el-descriptions-item>
              <el-descriptions-item label="金额(元)">
                <span style="color: #EF4444; font-weight: 600">¥ {{ result.fields.totalAmount?.toLocaleString() }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="销售方" :span="2">{{ result.fields.sellerName }}</el-descriptions-item>
              <el-descriptions-item label="购买方" :span="2">{{ result.fields.buyerName }}</el-descriptions-item>
            </el-descriptions>

            <div v-if="result.fields.items?.length" style="margin-top: 12px">
              <h4 style="font-size: 13px; margin: 0 0 8px 0">商品明细</h4>
              <el-table :data="result.fields.items" size="small" border>
                <el-table-column prop="name" label="商品名称" />
                <el-table-column label="金额" align="right" width="120">
                  <template #default="{ row }">{{ row.amount.toLocaleString() }}</template>
                </el-table-column>
                <el-table-column prop="taxRate" label="税率" width="100" align="right" />
              </el-table>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style lang="scss" scoped>
.upload-zone {
  border: 2px dashed $color-border-strong;
  border-radius: $radius-md;
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  background: $color-bg;
}
.upload-empty {
  text-align: center;
  color: $color-text-secondary;
  .upload-icon { font-size: 48px; margin-bottom: 8px; }
}
.upload-preview {
  max-width: 100%;
  max-height: 320px;
  img { max-width: 100%; max-height: 320px; }
}
.upload-actions {
  display: flex;
  gap: 8px;
}
.result-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
