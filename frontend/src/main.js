import { createApp } from 'vue'
import App from './App.vue'
import DisplayPreview from './DisplayPreview.vue'
import './style.css'
import './cockpit.css'
import './mobile.css'

const isSurface = new URLSearchParams(window.location.search).get('surface') === '1'
createApp(isSurface ? App : DisplayPreview).mount('#app')
