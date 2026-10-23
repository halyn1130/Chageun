<template>
  <div
    class="road-context"
    role="img"
    aria-label="교차로와 횡단보도를 보여 주는 도로 개념도"
  >
    <svg viewBox="0 0 440 300" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="roadGlow" x1="65" y1="230" x2="390" y2="25">
          <stop stop-color="#86a9cc" stop-opacity=".04" />
          <stop offset=".55" stop-color="#91b4ff" stop-opacity=".35" />
          <stop offset="1" stop-color="#91b4ff" stop-opacity=".04" />
        </linearGradient>
      </defs>
      <g transform="translate(220 150) rotate(-24) translate(-220 -150)">
        <path
          d="M164 12H276V94H425V206H276V288H164V206H15V94H164Z"
          fill="#242b38"
          stroke="url(#roadGlow)"
          stroke-width="2"
        />
        <path
          d="M220 12V75M220 225V288M15 150H145M295 150H425"
          stroke="#9bacc4"
          stroke-opacity=".35"
          stroke-dasharray="10 9"
        />
        <path
          d="M178 81H262M178 220H262"
          stroke="#d4e1f5"
          stroke-opacity=".55"
          stroke-width="12"
          stroke-dasharray="6 5"
        />
        <path
          d="M150 109V191M289 109V191"
          stroke="#d4e1f5"
          stroke-opacity=".55"
          stroke-width="12"
          stroke-dasharray="6 5"
        />
        <path
          d="M171 62H269M171 239H269M129 101V199M310 101V199"
          stroke="#a9bddb"
          stroke-opacity=".3"
          stroke-width="2"
        />
        <rect x="239" y="251" width="18" height="30" rx="6" fill="#a6baff" />
        <rect x="242" y="256" width="12" height="7" rx="2" fill="#364867" />
        <circle cx="300" cy="80" r="5" fill="#b7cba6" fill-opacity=".9" />
        <circle cx="151" cy="219" r="5" fill="#b7cba6" fill-opacity=".5" />
      </g>
    </svg>
  </div>
</template>
