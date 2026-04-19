<template>
  <div>
    <NCard class="auth-card">
      <h2 class="auth-title">企业注册</h2>

      <NForm ref="formRef" :model="form" :rules="rules">
        <NFormItem path="enterpriseName" label="企业名称">
          <NInput v-model:value="form.enterpriseName" placeholder="请输入企业名称" />
        </NFormItem>

        <NFormItem path="userName" label="您的姓名">
          <NInput v-model:value="form.userName" placeholder="请输入姓名" />
        </NFormItem>

        <NFormItem path="phone" label="手机号">
          <NInput v-model:value="form.phone" placeholder="请输入手机号" maxlength="11" />
        </NFormItem>

        <NFormItem path="code" label="验证码">
          <div class="code-row">
            <NInput v-model:value="form.code" placeholder="请输入验证码" maxlength="6" />
            <NButton
              :disabled="countdown > 0 || !isPhoneValid"
              :loading="sendingCode"
              @click="sendCode"
              class="code-btn"
            >
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </NButton>
          </div>
        </NFormItem>

        <NButton
          type="primary"
          block
          :loading="submitting"
          @click="handleRegister"
          class="submit-btn"
        >
          注册并登录
        </NButton>
      </NForm>

      <div class="auth-footer">
        已有账号？<NuxtLink to="/login" class="auth-link">去登录</NuxtLink>
      </div>
    </NCard>
  </div>
</template>

<script setup lang="ts">
import { NCard, NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'

definePageMeta({ layout: 'guest' })

const authStore = useAuthStore()
const router = useRouter()
const message = useMessage()

const form = reactive({
  enterpriseName: '',
  userName: '',
  phone: '',
  code: '',
})
const sendingCode = ref(false)
const submitting = ref(false)
const countdown = ref(0)

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))

const rules = {
  enterpriseName: { required: true, message: '请输入企业名称', trigger: 'blur' },
  userName: { required: true, message: '请输入姓名', trigger: 'blur' },
  phone: { required: true, message: '请输入手机号', trigger: 'blur' },
  code: { required: true, message: '请输入验证码', trigger: 'blur' },
}

async function sendCode() {
  if (!isPhoneValid.value) return
  sendingCode.value = true
  try {
    const res = await $fetch('/api/auth/sms.send', {
      method: 'POST',
      body: { phone: form.phone },
    })
    if ((res as any).code === 0) {
      message.success('验证码已发送')
      countdown.value = 60
      const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      message.error((res as any).message)
    }
  } catch {
    message.error('发送失败，请稍后重试')
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  if (!form.enterpriseName || !form.userName || !form.phone || !form.code) return
  submitting.value = true
  try {
    const res = await $fetch('/api/auth/register', {
      method: 'POST',
      body: form,
    })
    const data = res as any
    if (data.code === 0) {
      authStore.setAuth(data.data)
      message.success('注册成功')
      await router.push('/dashboard')
    } else {
      message.error(data.message)
    }
  } catch {
    message.error('注册失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-card {
  width: 100%;
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
  padding: 16px;
  box-shadow: var(--shadow-lg);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 28px;
  color: var(--text-primary);
}

.code-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.code-btn {
  flex-shrink: 0;
  width: 120px;
}

.submit-btn {
  margin-top: 12px;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-secondary);
}

.auth-link {
  color: var(--accent-blue);
  text-decoration: none;
  font-weight: 500;
}

.auth-link:hover {
  text-decoration: underline;
}
</style>
