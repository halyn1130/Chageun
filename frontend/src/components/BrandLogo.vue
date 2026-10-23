<template>
  <div class="wordmark" aria-label="차근">
    <span class="brand-logo" aria-hidden="true" />
    <strong>차근</strong>
  </div>
</template>

<style scoped>
.wordmark { display: flex; align-items: center; gap: 10px; padding: 0; }
.brand-logo { display: block; flex-shrink: 0; width: 64px; height: 36px; background: currentColor; mask: url('/images/chageun-logo.png') center / contain no-repeat; }
:global([data-theme='light']) .brand-logo { background: #07366d; }
.wordmark strong { font-size: 21px; font-weight: 650; letter-spacing: -1px; }
.auth-brand { justify-content: center; margin: 0 0 5px; }
</style>
