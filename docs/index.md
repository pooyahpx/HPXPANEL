---
layout: home
---

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  const base = import.meta.env.BASE_URL || '/HPXPANEL/'
  window.location.replace(`${base}en/`)
})
</script>

Redirecting to English docs…
