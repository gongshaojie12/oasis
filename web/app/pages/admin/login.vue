<template>
  <div>
    <NCard class="auth-card">
      <h2 class="auth-title">管理员登录</h2>

      <NForm ref="formRef" :model="form" :rules="rules">
        <NFormItem path="username" label="用户名">
          <NInput v-model:value="form.username" placeholder="请输入用户名" />
        </NFormItem>

        <NFormItem path="password" label="密码">
          <NInput
            v-model:value="form.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
          />
        </NFormItem>

        <NButton
          type="primary"
          block
          :loading="submitting"
          @click="handleLogin"
          class="submit-btn"
        >
          登录
        </NButton>
      </NForm>

      <div class="auth-footer">
        <NuxtLink to="/login" class="auth-link">返回用户登录</NuxtLink>
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

const form = reactive({ username: '', password: '' })
const submitting = ref(false)

const rules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

async function handleLogin() {
  if (!form.username || !form.password) return
  submitting.value = true
  try {
    const res = await $fetch('/api/auth/admin-login', {
      method: 'POST',
      body: form,
    })
    const data = res as any
    if (data.code === 0) {
      authStore.setAuth(data.data)
      message.success('登录成功')
      await router.push('/dashboard')
    } else {
      message.error(data.message)
    }
  } catch (err: any) {
    message.error('登录失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-card {
  width: 100%;
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
  padding: 12px;
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 24px;
  color: var(--text-primary);
}

.submit-btn {
  margin-top: 8px;
  height: 42px;
  font-size: 15px;
}

.auth-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: var(--text-secondary);
}

.auth-link {
  color: var(--accent-blue);
  text-decoration: none;
}

.auth-link:hover {
  text-decoration: underline;
}
</style>
