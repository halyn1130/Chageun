<script setup>
defineProps({ type: String, size: { type: Number, default: 32 } })
</script>
<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 40 32"
    fill="none"
    stroke="currentColor"
    stroke-width="2.2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <g v-if="type === 'engine'">
      <path
        d="M7 10h5l4-4h11v5h5l3 4v10h-7l-4 3H13l-4-5H5V12h2zM18 6V3h8M2 14v8M35 14h3v10h-3"
      />
    </g>
    <g v-else-if="type === 'oil'">
      <path
        d="M8 11h14l5 7 7-8 3 2-7 12H15l-7-8H4v-5h4zM17 11V7h7M31 27c0-2 2-4 2-4s2 2 2 4a2 2 0 0 1-4 0"
      />
    </g>
    <g v-else-if="type === 'battery'">
      <path d="M5 8h30v20H5zM10 8V4h6v4M24 8V4h6v4M10 17h6M25 14v6M22 17h6" />
    </g>
    <g v-else-if="type === 'brake' || type === 'abs'">
      <circle cx="20" cy="16" r="10" />
      <path d="M6 5a18 18 0 0 0 0 22M34 5a18 18 0 0 1 0 22" />
      <template v-if="type === 'brake'">
        <path d="M20 10v7" />
        <circle cx="20" cy="22" r="1" fill="currentColor" stroke="none" />
      </template>
      <text
        v-else
        x="20"
        y="19"
        fill="currentColor"
        stroke="none"
        text-anchor="middle"
        font-family="Arial,sans-serif"
        font-size="9"
        font-weight="700"
      >
        ABS
      </text>
    </g>
    <g v-else-if="type === 'tire'">
      <path
        d="M12 4C6 8 5 15 6 21l3 7h22l3-7c1-6 0-13-6-17M10 24v4M16 24v4M24 24v4M30 24v4M20 9v9"
      />
      <circle cx="20" cy="23" r="1" fill="currentColor" stroke="none" />
    </g>
    <g v-else-if="type === 'fuel'">
      <path
        d="M8 28V5h15v23M6 28h19M11 8h9v8h-9zM23 17h3v7a3 3 0 0 0 6 0V12l-5-6M29 8v6h3"
      />
    </g>
    <g v-else-if="type === 'airbag'">
      <circle cx="13" cy="6" r="3" />
      <path d="m12 12 6 7-3 8H7M7 15l4 6-3 6" />
      <circle cx="27" cy="13" r="7" />
    </g>
  </svg>
</template>
