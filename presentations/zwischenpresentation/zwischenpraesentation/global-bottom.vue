<template>
  <div
    v-if="$slidev.nav.currentPage > 1"
    class="absolute bottom-4 right-4 text-xs opacity-50 z-10"
  >
    <SlideCurrentNo /> / <SlidesTotal />
  </div>
</template>
