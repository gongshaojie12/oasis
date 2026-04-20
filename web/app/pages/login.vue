<template>
  <div>
    <NCard class="auth-card">
      <h2 class="auth-title">{{ $t('auth.login') }}</h2>

      <NForm ref="formRef" :model="form" :rules="rules">
        <NFormItem path="phone" :label="$t('auth.phone')">
          <NInput v-model:value="form.phone" :placeholder="$t('auth.phonePlaceholder')" maxlength="11" />
        </NFormItem>

        <NFormItem path="code" :label="$t('auth.code')">
          <div class="code-row">
            <NInput v-model:value="form.code" :placeholder="$t('auth.codePlaceholder')" maxlength="6" />
            <NButton
              :disabled="countdown > 0 || !isPhoneValid"
              :loading="sendingCode"
              @click="sendCode"
              class="code-btn"
            >
              {{ countdown > 0 ? `${countdown}s` : $t('auth.getCode') }}
            </NButton>
          </div>
        </NFormItem>

        <NButton
          type="primary"
          block
          :loading="submitting"
          @click="handleLogin"
          class="submit-btn"
        >
          {{ $t('auth.login') }}
        </NButton>
      </NForm>

      <div class="auth-footer">
        {{ $t('auth.noAccount') }}<NuxtLink to="/register" class="auth-link">{{ $t('auth.registerNow') }}</NuxtLink>
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
const { $t } = useI18n()

const form = reactive({ phone: '', code: '' })
const sendingCode = ref(false)
const submitting = ref(false)
const countdown = ref(0)

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))

const rules = computed(() => ({
  phone: { required: true, message: $t('auth.phoneRequired'), trigger: 'blur' },
  code: { required: true, message: $t('auth.codeRequired'), trigger: 'blur' },
}))

async function sendCode() {
  if (!isPhoneValid.value) return
  sendingCode.value = true
  try {
    const res = await $fetch('/api/auth/sms.send', {
      method: 'POST',
      body: { phone: form.phone },
    })
    if ((res as any).code === 0) {
      message.success($t('auth.codeSent'))
      countdown.value = 60
      const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      message.error((res as any).message)
    }
  } catch (err: any) {
    message.error($t('auth.sendFailed'))
  } finally {
    sendingCode.value = false
  }
}

async function handleLogin() {
  if (!form.phone || !form.code) return
  submitting.value = true
  try {
    const res = await $fetch('/api/auth/login', {
      method: 'POST',
      body: form,
    })
    const data = res as any
    if (data.code === 0) {
      authStore.setAuth(data.data)
      message.success($t('auth.loginSuccess'))
      await router.push('/dashboard')
    } else {
      message.error(data.message)
    }
  } catch (err: any) {
    message.error($t('auth.loginFailed'))
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
