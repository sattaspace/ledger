<script setup lang="ts">
// MarkdownViewer — Renders markdown content with Tailwind prose styling
// Used by protected docs pages to display .md files

import { ref, onMounted, computed, watch } from "vue";
import { marked } from "marked";
import { requireAuth } from "@/lib/auth";

const props = withDefaults(
  defineProps<{
    content?: string;
    src?: string;
  }>(),
  {
    content: "",
    src: undefined,
  }
);

const raw = ref("");
const loading = ref(true);
const error = ref<string | null>(null);

// Configure marked for safe rendering
marked.setOptions({
  gfm: true,
  breaks: false,
});

const html = computed(() => {
  if (!raw.value) return "";
  return marked.parse(raw.value) as string;
});

// Track active section for TOC scroll-spy
const activeHeading = ref("");

onMounted(async () => {
  requireAuth();

  try {
    if (props.src) {
      const res = await fetch(props.src);
      if (!res.ok) throw new Error(`Failed to load document: ${res.status}`);
      raw.value = await res.text();
    } else if (props.content) {
      raw.value = props.content;
    }
  } catch (err: any) {
    error.value = err.message || "Failed to load document.";
  } finally {
    loading.value = false;
  }

  // Set up scroll spy for TOC
  setupScrollSpy();
});

function setupScrollSpy() {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeHeading.value = entry.target.id;
        }
      }
    },
    { rootMargin: "-80px 0px -70% 0px" }
  );

  // Small delay to let DOM render
  setTimeout(() => {
    document.querySelectorAll("article h2").forEach((el) => {
      observer.observe(el);
    });
  }, 100);
}

function scrollToHeading(id: string) {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
</script>

<template>
  <div>
    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="flex flex-col items-center gap-3">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent"></div>
        <p class="text-sm text-muted-foreground">Loading document...</p>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="flex flex-col items-center justify-center py-20 text-center">
      <svg class="h-12 w-12 text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      <h3 class="text-lg font-semibold text-foreground">Failed to load document</h3>
      <p class="mt-1 text-sm text-muted-foreground">{{ error }}</p>
    </div>

    <!-- Content layout -->
    <div v-else class="flex gap-8">
      <!-- Table of Contents sidebar (desktop) -->
      <aside class="hidden xl:block w-56 shrink-0">
        <nav class="sticky top-24 max-h-[calc(100vh-8rem)] overflow-y-auto">
          <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">On this page</p>
          <ul class="space-y-1 text-sm border-l border-border">
            <li
              v-for="heading in ($el as any)?.querySelectorAll('article h2')"
              :key="heading.id"
            >
              <button
                type="button"
                class="block w-full text-left pl-3 py-1 -ml-px text-muted-foreground hover:text-foreground transition-colors truncate"
                :class="{
                  'border-l-2 border-brand-500 text-foreground font-medium -ml-px': activeHeading === heading.id,
                  'border-l-2 border-transparent': activeHeading !== heading.id,
                }"
                @click="scrollToHeading(heading.id)"
              >
                {{ heading.textContent }}
              </button>
            </li>
          </ul>
        </nav>
      </aside>

      <!-- Markdown content -->
      <article
        class="prose prose-slate dark:prose-invert max-w-none prose-headings:scroll-mt-24 prose-a:text-brand-600 dark:prose-a:text-brand-400 prose-code:before:content-[''] prose-code:after:content-[''] prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-pre:rounded-xl prose-img:rounded-lg"
        v-html="html"
      ></article>
    </div>
  </div>
</template>
