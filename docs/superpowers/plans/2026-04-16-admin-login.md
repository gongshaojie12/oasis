# Admin Login & Test Phone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a platform super admin login (username/password via env vars, at `/admin/login`) and a test phone number that bypasses real SMS sending, while keeping the existing phone+SMS login unchanged.

**Architecture:** Super admin is independent from the enterprise/user system - credentials live in env vars, JWT payload uses `role: "superadmin"` with no enterpriseId. Test phone is also env-var driven: when `TEST_PHONE` is set, that number skips SMS sending and uses a fixed verification code. When `TEST_PHONE` is empty, all requests go through real SMS.

**Tech Stack:** Nuxt 3, Naive UI, Drizzle ORM, jose (JWT), zod (validation)

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `web/server/api/auth/admin-login.post.ts` | Admin login API - validates credentials against env vars, issues JWT |
| `web/app/pages/admin/login.vue` | Admin login page - username/password form |

### Modified files
| File | Change |
|------|--------|
| `web/nuxt.config.ts` | Add 4 runtimeConfig entries |
| `web/server/middleware/01.auth.ts` | Add `/api/auth/admin-login` to public routes |
| `web/server/middleware/02.enterprise.ts` | Skip enterprise check for superadmin |
| `web/app/middleware/auth.global.ts` | Add `/admin/login` to public pages |
| `web/app/stores/auth.ts` | Make `enterprise` nullable in `setAuth` |
| `web/server/api/auth/me.get.ts` | Handle superadmin user (no DB lookup) |
| `web/server/api/auth/sms.send.post.ts` | Skip SMS for test phone |
| `web/server/api/auth/login.post.ts` | Skip code verification for test phone |
| `web/server/api/auth/register.post.ts` | Skip code verification for test phone |
| `.env.production` | Add 4 new variables |
| `.env.production.example` | Add 4 new variables with placeholders |

---

### Task 1: Add environment variables and runtimeConfig

**Files:**
- Modify: `web/nuxt.config.ts:26-37`
- Modify: `.env.production`
- Modify: `.env.production.example`

- [ ] **Step 1: Add env vars to `.env.production`**

Add these lines at the end of the `# === Web (Nuxt) ===` section (after line 15):

```env
# === Admin ===
ADMIN_USERNAME=admin
ADMIN_PASSWORD=oasis-admin-2026

# === Test Account (leave empty in production to disable) ===
TEST_PHONE=13800000000
TEST_SMS_CODE=888888
```

- [ ] **Step 2: Add env vars to `.env.production.example`**

Add these lines at the same location:

```env
# === Admin ===
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD

# === Test Account (leave empty in production to disable) ===
TEST_PHONE=
TEST_SMS_CODE=
```

- [ ] **Step 3: Add runtimeConfig entries in `nuxt.config.ts`**

In the `runtimeConfig` object (after line 36, before the closing `},`), add:

```ts
    adminUsername: process.env.ADMIN_USERNAME || '',
    adminPassword: process.env.ADMIN_PASSWORD || '',
    testPhone: process.env.TEST_PHONE || '',
    testSmsCode: process.env.TEST_SMS_CODE || '',
```

- [ ] **Step 4: Commit**

```bash
git add web/nuxt.config.ts .env.production .env.production.example
git commit -m "feat(auth): add admin and test phone environment variables"
```

---

### Task 2: Create admin login API

**Files:**
- Create: `web/server/api/auth/admin-login.post.ts`

- [ ] **Step 1: Create the admin login endpoint**

Create `web/server/api/auth/admin-login.post.ts`:

```ts
import { z } from 'zod'
import { signToken, signRefreshToken } from '~~/server/utils/jwt'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_CODE_INVALID, '请输入账号和密码')
  }

  const { username, password } = parsed.data
  const config = useRuntimeConfig()

  if (!config.adminUsername || !config.adminPassword) {
    return error(ErrorCodes.FORBIDDEN, '管理员登录未启用')
  }

  if (username !== config.adminUsername || password !== config.adminPassword) {
    return error(ErrorCodes.FORBIDDEN, '账号或密码错误')
  }

  const tokenPayload = {
    userId: 'superadmin',
    enterpriseId: '',
    role: 'superadmin',
  }
  const token = await signToken(tokenPayload)
  const refreshToken = await signRefreshToken(tokenPayload)

  return success({
    token,
    refreshToken,
    user: {
      id: 'superadmin',
      phone: '',
      name: '超级管理员',
      role: 'superadmin',
    },
    enterprise: null,
  })
})
```

- [ ] **Step 2: Commit**

```bash
git add web/server/api/auth/admin-login.post.ts
git commit -m "feat(auth): add admin login API endpoint"
```

---

### Task 3: Update server middleware for admin support

**Files:**
- Modify: `web/server/middleware/01.auth.ts:4-10`
- Modify: `web/server/middleware/02.enterprise.ts:9`

- [ ] **Step 1: Add admin-login to public routes in `01.auth.ts`**

In `web/server/middleware/01.auth.ts`, add `/api/auth/admin-login` to the `publicPaths` array:

```ts
const publicPaths = [
  '/api/auth/sms.send',
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/admin-login',
  '/api/health',
  '/api/internal/',
]
```

- [ ] **Step 2: Skip enterprise check for superadmin in `02.enterprise.ts`**

In `web/server/middleware/02.enterprise.ts`, change line 9 from:

```ts
  if (!path.startsWith('/api/') || !event.context.user) return
```

to:

```ts
  if (!path.startsWith('/api/') || !event.context.user) return

  // Superadmin has no enterprise — skip check
  if (event.context.user.role === 'superadmin') return
```

- [ ] **Step 3: Commit**

```bash
git add web/server/middleware/01.auth.ts web/server/middleware/02.enterprise.ts
git commit -m "feat(auth): update middleware to support superadmin"
```

---

### Task 4: Update `/api/auth/me` for superadmin

**Files:**
- Modify: `web/server/api/auth/me.get.ts`

- [ ] **Step 1: Handle superadmin in me.get.ts**

Replace the full content of `web/server/api/auth/me.get.ts` with:

```ts
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { users, enterprises } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const user = event.context.user
  if (!user) {
    return error(ErrorCodes.TOKEN_INVALID, '未登录')
  }

  // Superadmin: return static info, no DB lookup
  if (user.role === 'superadmin') {
    return success({
      user: {
        id: 'superadmin',
        phone: '',
        name: '超级管理员',
        role: 'superadmin',
      },
      enterprise: null,
    })
  }

  const db = useDB()

  const userRecord = await db.select()
    .from(users)
    .where(eq(users.id, user.userId))
    .limit(1)

  if (userRecord.length === 0) {
    return error(ErrorCodes.TOKEN_INVALID, '用户不存在')
  }

  const enterpriseRecord = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, user.enterpriseId))
    .limit(1)

  return success({
    user: {
      id: userRecord[0].id,
      phone: userRecord[0].phone,
      name: userRecord[0].name,
      role: userRecord[0].role,
    },
    enterprise: enterpriseRecord[0] || null,
  })
})
```

- [ ] **Step 2: Commit**

```bash
git add web/server/api/auth/me.get.ts
git commit -m "feat(auth): handle superadmin in /api/auth/me"
```

---

### Task 5: Update auth store and client middleware

**Files:**
- Modify: `web/app/stores/auth.ts:38-48`
- Modify: `web/app/middleware/auth.global.ts:4`

- [ ] **Step 1: Make enterprise nullable in setAuth**

In `web/app/stores/auth.ts`, change the `setAuth` action signature (lines 38-48) from:

```ts
    setAuth(data: {
      token: string
      refreshToken: string
      user: User
      enterprise: Enterprise
    }) {
      this.token = data.token
      this.refreshToken = data.refreshToken
      this.user = data.user
      this.enterprise = data.enterprise
    },
```

to:

```ts
    setAuth(data: {
      token: string
      refreshToken: string
      user: User
      enterprise: Enterprise | null
    }) {
      this.token = data.token
      this.refreshToken = data.refreshToken
      this.user = data.user
      this.enterprise = data.enterprise
    },
```

The only change is `enterprise: Enterprise` → `enterprise: Enterprise | null`.

- [ ] **Step 2: Add `/admin/login` to public pages in client middleware**

In `web/app/middleware/auth.global.ts`, change line 4 from:

```ts
  const publicPages = ['/login', '/register']
```

to:

```ts
  const publicPages = ['/login', '/register', '/admin/login']
```

- [ ] **Step 3: Commit**

```bash
git add web/app/stores/auth.ts web/app/middleware/auth.global.ts
git commit -m "feat(auth): update store and middleware for admin login"
```

---

### Task 6: Create admin login page

**Files:**
- Create: `web/app/pages/admin/login.vue`

- [ ] **Step 1: Create the admin login page**

Create `web/app/pages/admin/login.vue`:

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add web/app/pages/admin/login.vue
git commit -m "feat(auth): add admin login page"
```

---

### Task 7: Add test phone support to SMS and login APIs

**Files:**
- Modify: `web/server/api/auth/sms.send.post.ts:14-51`
- Modify: `web/server/api/auth/login.post.ts:15-94`
- Modify: `web/server/api/auth/register.post.ts:17-104`

- [ ] **Step 1: Update sms.send.post.ts to skip SMS for test phone**

In `web/server/api/auth/sms.send.post.ts`, add the test phone check right after phone validation succeeds (after `const { phone } = parsed.data` on line 21), before the rate limiting check:

```ts
  const { phone } = parsed.data

  // Test phone: skip SMS sending entirely
  const config = useRuntimeConfig()
  if (config.testPhone && phone === config.testPhone) {
    return success({ sent: true })
  }

  const db = useDB()
```

This replaces the existing line `const db = useDB()` which was on line 22.

- [ ] **Step 2: Update login.post.ts to skip code verification for test phone**

In `web/server/api/auth/login.post.ts`, replace the SMS verification block (lines 22-49, from `const db = useDB()` through `// Mark code as used` and the update statement) with:

```ts
  const db = useDB()
  const config = useRuntimeConfig()
  const isTestPhone = config.testPhone && phone === config.testPhone

  // Verify SMS code (skip for test phone)
  if (isTestPhone) {
    if (code !== config.testSmsCode) {
      return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
    }
  } else {
    const smsRecord = await db.select()
      .from(smsCodes)
      .where(
        and(
          eq(smsCodes.phone, phone),
          eq(smsCodes.code, code),
          eq(smsCodes.used, 0)
        )
      )
      .orderBy(smsCodes.createdAt)
      .limit(1)

    if (smsRecord.length === 0) {
      return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
    }

    if (isExpired(smsRecord[0].expiresAt)) {
      return error(ErrorCodes.SMS_CODE_EXPIRED, '验证码已过期')
    }

    // Mark code as used
    await db.update(smsCodes)
      .set({ used: 1 })
      .where(eq(smsCodes.id, smsRecord[0].id))
  }
```

Everything after this (user lookup, token generation, etc.) stays unchanged.

- [ ] **Step 3: Update register.post.ts to skip code verification for test phone**

In `web/server/api/auth/register.post.ts`, apply the same pattern. Replace the SMS verification block (lines 25-51, from `const db = useDB()` through the mark-code-as-used update) with:

```ts
  const db = useDB()
  const config = useRuntimeConfig()
  const isTestPhone = config.testPhone && phone === config.testPhone

  // Verify SMS code (skip for test phone)
  if (isTestPhone) {
    if (code !== config.testSmsCode) {
      return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
    }
  } else {
    const smsRecord = await db.select()
      .from(smsCodes)
      .where(
        and(
          eq(smsCodes.phone, phone),
          eq(smsCodes.code, code),
          eq(smsCodes.used, 0)
        )
      )
      .orderBy(smsCodes.createdAt)
      .limit(1)

    if (smsRecord.length === 0) {
      return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
    }

    if (isExpired(smsRecord[0].expiresAt)) {
      return error(ErrorCodes.SMS_CODE_EXPIRED, '验证码已过期')
    }

    // Mark code as used
    await db.update(smsCodes)
      .set({ used: 1 })
      .where(eq(smsCodes.id, smsRecord[0].id))
  }
```

Everything after this (existing user check, enterprise creation, etc.) stays unchanged.

- [ ] **Step 4: Commit**

```bash
git add web/server/api/auth/sms.send.post.ts web/server/api/auth/login.post.ts web/server/api/auth/register.post.ts
git commit -m "feat(auth): add test phone support to SMS and login APIs"
```

---

### Task 8: Final verification

- [ ] **Step 1: Review all changes**

```bash
git diff HEAD~7 --stat
```

Verify the file list matches what was planned.

- [ ] **Step 2: Check for TypeScript errors**

```bash
cd web && npx nuxi typecheck
```

If typecheck is not configured, skip this step.

- [ ] **Step 3: Build test**

```bash
cd web && npm run build
```

Verify the build completes without errors.

- [ ] **Step 4: Docker build and test (if deploying)**

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Test in browser:
1. Visit `http://localhost/admin/login` — enter admin/oasis-admin-2026, verify redirect to dashboard
2. Visit `http://localhost/login` — enter 13800000000, click send code (should succeed without real SMS), enter 888888, verify login works (need to register first)
3. Visit `http://localhost/register` — register with phone 13800000000 and code 888888, verify registration works
