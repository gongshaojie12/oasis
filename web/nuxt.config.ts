export default defineNuxtConfig({
  devtools: { enabled: true },

  css: ['~/assets/css/main.css'],

  modules: [
    '@pinia/nuxt',
    '@vueuse/nuxt',
    '@nuxt/icon',
    'pinia-plugin-persistedstate/nuxt',
    '@nuxtjs/i18n',
  ],

  i18n: {
    locales: [
      { code: 'zh-CN', name: '中文', file: 'zh-CN.json' },
      { code: 'en-US', name: 'English', file: 'en-US.json' },
    ],
    defaultLocale: 'zh-CN',
    langDir: 'locales',
    strategy: 'no_prefix',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_locale',
      fallbackLocale: 'zh-CN',
    },
  },

  build: {
    transpile: ['naive-ui', '@css-render/vue3-ssr', '@juggle/resize-observer'],
  },

  vite: {
    optimizeDeps: {
      include: ['naive-ui', 'vueuc', 'date-fns-tz/formatInTimeZone'],
    },
    ssr: {
      noExternal: ['naive-ui', 'vueuc', 'date-fns-tz'],
    },
  },

  runtimeConfig: {
    databaseType: process.env.DATABASE_TYPE || 'sqlite',
    databaseUrl: process.env.DATABASE_URL || 'file:./data/oasis.db',
    jwtSecret: process.env.JWT_SECRET || 'dev-secret-change-in-production',
    jwtExpiresIn: '2h',
    refreshTokenExpiresIn: '7d',
    smsAccessKey: process.env.SMS_ACCESS_KEY || '',
    smsAccessSecret: process.env.SMS_ACCESS_SECRET || '',
    internalApiKey: process.env.INTERNAL_API_KEY || 'dev-internal-key',
    engineUrl: process.env.ENGINE_URL || 'http://localhost:8000',
    encryptionKey: process.env.ENCRYPTION_KEY || 'dev-encryption-key-32chars!!',
    adminUsername: process.env.ADMIN_USERNAME || '',
    adminPassword: process.env.ADMIN_PASSWORD || '',
    testPhone: process.env.TEST_PHONE || '',
    testSmsCode: process.env.TEST_SMS_CODE || '',
  },

  compatibilityDate: '2025-01-01',
})
