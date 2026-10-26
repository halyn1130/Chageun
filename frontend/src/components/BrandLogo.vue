<template>
  <div class="wordmark" role="img" aria-label="차근">
    <span class="brand-logo" aria-hidden="true" />
  </div>
</template>

<style scoped>
.wordmark { display: flex; align-items: center; gap: 10px; padding: 0; }
.brand-logo { display: block; flex-shrink: 0; width: 64px; height: 36px; background: currentColor; mask: url('/images/chageun-logo.png') center / contain no-repeat; }
:global([data-theme='light']) .brand-logo { background: #07366d; }
.auth-brand { justify-content: center; margin: 0 0 5px; }
</style>
