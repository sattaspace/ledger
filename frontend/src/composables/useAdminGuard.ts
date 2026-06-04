/**
 * useAdminGuard — Client-side composable for admin route protection.
 *
 * API-1 FIX: Now uses useAuth() shared state instead of making a separate
 * GET /users/me call. Previously, every admin page made its own /users/me
 * request via this composable, duplicating the call that useAuth() already
 * makes. On admin pages, this resulted in 3 calls to /users/me:
 *   1. useAdminGuard → apiClient.get("/users/me")
 *   2. AdminNavbar → apiClient.get("/users/me")
 *   3. SessionGuard → (implicit via useAuth initAuth)
 *
 * Now, useAdminGuard reuses the user data from useAuth(), which deduplicates
 * the /users/me call across all components. This saves 1-2 API calls per
 * admin page load.
 *
 * Checks if the current user is staff (is_staff or owner/admin role).
 * If not, redirects to /dashboard.
 *
 * VUE 3 CONVENTION: Navigation uses authHelpers.navigateTo() (Astro's
 * navigate() from 'astro:transitions') instead of window.location.href,
 * deferred with setTimeout(0) to avoid the "querySelector null" error
 * during View Transitions.
 *
 * Usage in admin page components:
 *   <script setup>
 *   import { useAdminGuard } from "@/composables/useAdminGuard";
 *   const { isAuthorized, isLoading } = useAdminGuard();
 *   </script>
 *
 *   <template>
 *     <div v-if="isLoading">Loading...</div>
 *     <div v-else-if="isAuthorized">Admin content here</div>
 *   </template>
 */
import { ref, onMounted } from "vue";
import { useAuth } from "@/composables/useAuth";
import { authHelpers } from "@/lib/api";

export function useAdminGuard() {
  const isAuthorized = ref(false);
  const isLoading = ref(true);

  onMounted(async () => {
    try {
      // API-1 FIX: Use useAuth() shared state instead of separate /users/me call.
      // The initAuth() call fetches user data if not already cached, and
      // fetchUser() is deduplicated via window-level promise sharing.
      const { initAuth, user } = useAuth();
      await initAuth();

      // Check if the user has admin access
      const hasAccess =
        user.value?.is_staff === true ||
        user.value?.role === "owner" ||
        user.value?.role === "admin";

      if (hasAccess) {
        isAuthorized.value = true;
      } else {
        // Not authorized — redirect to user dashboard
        // VUE 3 CONVENTION: Use navigateTo() deferred with setTimeout
        setTimeout(() => {
          authHelpers.navigateTo("/dashboard");
        }, 0);
      }
    } catch {
      // Not authenticated — redirect to login
      // VUE 3 CONVENTION: Use navigateTo() deferred with setTimeout
      setTimeout(() => {
        authHelpers.navigateTo("/auth/login");
      }, 0);
    } finally {
      isLoading.value = false;
    }
  });

  // Also expose the user from useAuth() so admin components can access
  // admin-specific fields (is_staff, role, etc.) without another API call
  const { user: adminUser } = useAuth();

  return { isAuthorized, isLoading, adminUser };
}
