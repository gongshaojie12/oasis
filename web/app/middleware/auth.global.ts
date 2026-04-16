export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore()

  const publicPages = ['/login', '/register', '/admin/login']
  const isPublic = publicPages.includes(to.path)

  if (!isPublic && !authStore.isLoggedIn) {
    return navigateTo('/login')
  }

  if (isPublic && authStore.isLoggedIn) {
    return navigateTo('/dashboard')
  }
})
