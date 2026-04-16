# 平台超级管理员登录 & 测试手机号

## 概述

新增两个功能：
1. **平台超级管理员登录** — 独立于企业用户体系，通过账号密码登录，无需手机验证码
2. **测试手机号** — 预置一个测试手机号和验证码，跳过真实短信发送，方便本地测试

两个功能均通过环境变量配置，不改动数据库 schema。

---

## 一、平台超级管理员登录

### 1.1 架构

管理员体系完全独立于现有的企业用户体系：

```
现有流程：  /login → 手机号+验证码 → 查 users 表 → JWT(userId, enterpriseId, role) → /dashboard
管理员流程：/admin/login → 账号+密码 → 校验环境变量 → JWT(adminId, role:"superadmin") → /dashboard
```

### 1.2 环境变量

在 `.env.production` 中新增：

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
```

在 `nuxt.config.ts` 的 `runtimeConfig` 中新增：

```ts
adminUsername: process.env.ADMIN_USERNAME || '',
adminPassword: process.env.ADMIN_PASSWORD || '',
```

### 1.3 后端 API

#### `POST /api/auth/admin-login`

新增接口，接收 JSON body：

```json
{
  "username": "admin",
  "password": "your-secure-password"
}
```

逻辑：
1. 校验 username 和 password 是否与环境变量匹配
2. 匹配失败返回 401 错误（使用通用错误信息"账号或密码错误"，不泄露具体是哪个错）
3. 匹配成功签发 JWT，payload：
   ```json
   {
     "userId": "superadmin",
     "enterpriseId": null,
     "role": "superadmin"
   }
   ```
4. 返回格式与现有登录一致：
   ```json
   {
     "token": "...",
     "refreshToken": "...",
     "user": {
       "id": "superadmin",
       "phone": "",
       "name": "超级管理员",
       "role": "superadmin"
     },
     "enterprise": null
   }
   ```

### 1.4 Server 中间件修改

#### `01.auth.ts`

将 `/api/auth/admin-login` 加入公开路由白名单（不需要 token 即可访问）。

#### `02.enterprise.ts`

当 `event.context.user.role === 'superadmin'` 时，跳过企业状态检查（superadmin 不属于任何企业）。

### 1.5 前端页面

#### 新增 `/admin/login` 页面

- 使用 `guest` layout（与现有登录页一致）
- 表单字段：用户名（text）+ 密码（password）
- UI 风格与现有登录页保持一致（Naive UI 组件）
- 提交后调用 `/api/auth/admin-login`
- 登录成功后调用 `authStore.setAuth()` 存储 token，跳转到 `/dashboard`

### 1.6 客户端中间件修改

#### `auth.global.ts`

将 `/admin/login` 加入公开页面白名单，未登录用户可以访问。

### 1.7 Auth Store 兼容

`authStore.setAuth()` 需要兼容 enterprise 为 null 的情况。Dashboard 及其他页面中使用 enterprise 数据的地方需做防空处理（可选链 `?.`）。

### 1.8 `/api/auth/me` 兼容

当 token 中 userId 为 `"superadmin"` 时，直接返回超管信息，不查数据库：

```json
{
  "user": {
    "id": "superadmin",
    "phone": "",
    "name": "超级管理员",
    "role": "superadmin"
  },
  "enterprise": null
}
```

---

## 二、测试手机号

### 2.1 环境变量

在 `.env.production` 中新增：

```env
TEST_PHONE=13800000000
TEST_SMS_CODE=888888
```

在 `nuxt.config.ts` 的 `runtimeConfig` 中新增：

```ts
testPhone: process.env.TEST_PHONE || '',
testSmsCode: process.env.TEST_SMS_CODE || '',
```

### 2.2 后端改动

#### `POST /api/auth/sms.send`

在发送短信前检查：当请求的手机号等于 `TEST_PHONE`（且 TEST_PHONE 非空）时，跳过真实短信发送和 smsCodes 表写入，直接返回 `{ sent: true }`。

#### `POST /api/auth/login`

在验证码校验前检查：当手机号等于 `TEST_PHONE` 且验证码等于 `TEST_SMS_CODE`（且两者均非空）时，直接通过验证，不查 smsCodes 表。后续流程（查用户、签发 token）不变。

注意：测试手机号对应的用户需要先通过注册流程创建（使用测试号注册）。

#### `POST /api/auth/register`

同样的测试号逻辑：当手机号等于 `TEST_PHONE` 且验证码等于 `TEST_SMS_CODE` 时，跳过 smsCodes 表验证。

### 2.3 切换到生产模式

当 `.env.production` 中 `TEST_PHONE` 为空（或不设置）时，所有请求走正常的短信验证流程，无需改代码。

---

## 三、不改动的部分

- 现有手机号+验证码登录/注册流程完全不变
- 数据库 schema 不变，不新增表
- 现有的企业 admin/user 角色权限逻辑不变
- `.env.production.example` 模板需更新，补充新增的环境变量

---

## 四、涉及文件清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `web/app/pages/admin/login.vue` | 管理员登录页面 |
| `web/server/api/auth/admin-login.post.ts` | 管理员登录 API |

### 修改文件
| 文件 | 改动 |
|------|------|
| `nuxt.config.ts` | runtimeConfig 新增 4 个变量 |
| `.env.production` | 新增 ADMIN_USERNAME、ADMIN_PASSWORD、TEST_PHONE、TEST_SMS_CODE |
| `.env.production.example` | 同步更新模板 |
| `web/server/middleware/01.auth.ts` | 公开路由白名单加 admin-login |
| `web/server/middleware/02.enterprise.ts` | superadmin 跳过企业检查 |
| `web/app/middleware/auth.global.ts` | 公开页面白名单加 /admin/login |
| `web/app/stores/auth.ts` | setAuth 兼容 enterprise 为 null |
| `web/server/api/auth/sms.send.post.ts` | 测试手机号跳过短信发送 |
| `web/server/api/auth/login.post.ts` | 测试手机号跳过验证码校验 |
| `web/server/api/auth/register.post.ts` | 测试手机号跳过验证码校验 |
| `web/server/api/auth/me.get.ts` | 兼容 superadmin 返回 |
