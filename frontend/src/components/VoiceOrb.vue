<script setup>
defineProps({ phase: { type: String, default: 'idle' } })
</script>

<template>
  <span class="voice-orb" :data-phase="phase" aria-hidden="true">
    <span class="voice-orb-halo" />
    <span class="voice-orb-core"><i /><i /></span>
  </span>
</template>

<style scoped>
.voice-orb {
  --orb-speed: 5s;
  position: relative;
  display: inline-block;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  isolation: isolate;
}
.voice-orb-halo {
  position: absolute;
  inset: 1%;
  border-radius: 50%;
  background: conic-gradient(from 50deg, #8bbaff00, #93caff65, #cab4ff18, #8bbaff00, #82e0dd60, #8bbaff00);
  filter: blur(4px);
  animation: orb-turn calc(var(--orb-speed) * 1.3) linear infinite;
}
.voice-orb-core {
  position: absolute;
  inset: 12%;
  overflow: hidden;
  border-radius: 48% 52% 46% 54%;
  background: linear-gradient(135deg, #d9eeff, #91b9fa 35%, #6177d9 78%, #acbdf5);
  box-shadow: inset 1px 2px 7px #eff9ffa0, 0 2px 20px #76a5ff40;
  animation: orb-flow var(--orb-speed) ease-in-out infinite alternate;
}
.voice-orb-core i {
  position: absolute;
  width: 110%;
  height: 70%;
  top: -20%;
  left: -35%;
  border-radius: 40% 60% 55% 45%;
  background: #e8faffc0;
  filter: blur(4px);
  animation: orb-current var(--orb-speed) ease-in-out infinite alternate;
}
.voice-orb-core i + i {
  top: 40%;
  left: 35%;
  background: #77e3e380;
  animation-delay: -2s;
  animation-direction: alternate-reverse;
}
.voice-orb[data-phase='listening'] { --orb-speed: 3.8s; }
.voice-orb[data-phase='thinking'] { --orb-speed: 2.8s; }
.voice-orb[data-phase='thinking'] .voice-orb-core { animation: orb-flow var(--orb-speed) ease-in-out infinite alternate, orb-turn 8s linear infinite; }
.voice-orb[data-phase='speaking'] { --orb-speed: 1.6s; }
.voice-orb[data-phase='speaking'] .voice-orb-halo { filter: blur(6px); }
.voice-orb[data-phase='idle'] *, .voice-orb[data-phase='error'] * { animation-play-state: paused; }
@keyframes orb-turn { to { transform: rotate(360deg); } }
@keyframes orb-flow {
  from { border-radius: 44% 56% 53% 47%; scale: .9; }
  50% { border-radius: 56% 44% 43% 57%; }
  to { border-radius: 49% 51% 58% 42%; scale: 1.07; }
}
@keyframes orb-current {
  from { transform: translate(-8%, -10%) rotate(-25deg); }
  to { transform: translate(30%, 40%) rotate(65deg); }
}
@media (prefers-reduced-motion: reduce) {
  .voice-orb *, .voice-orb[data-phase='thinking'] .voice-orb-core { animation: none; }
}
</style>
