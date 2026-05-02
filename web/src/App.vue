<script setup lang="ts">
import Button from "primevue/button";
import Card from "primevue/card";
import Message from "primevue/message";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import { computed, onMounted } from "vue";

import { useStatusStore } from "./stores/status";

const statusStore = useStatusStore();
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/auth/api/v1";
const appBasePath = import.meta.env.VITE_APP_BASE_PATH ?? "/auth";
const statusTone = computed(() => (statusStore.status?.status === "ok" ? "success" : "warn"));

onMounted(() => {
  void statusStore.loadStatus();
});
</script>

<template>
  <main class="app-shell">
    <section class="app-header">
      <div>
        <p class="eyebrow">Central identity</p>
        <h1>Auth Directory</h1>
      </div>
      <Button icon="pi pi-refresh" rounded text aria-label="Refresh status" @click="statusStore.loadStatus()" />
    </section>

    <Tabs value="directory" class="workspace-tabs">
      <TabList>
        <Tab value="directory">Directory</Tab>
        <Tab value="users">Users</Tab>
        <Tab value="codes">Registration Codes</Tab>
        <Tab value="profile">My Profile</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="directory">
          <Card>
            <template #title>Directory foundation</template>
            <template #content>
              <p>The directory and OAuth launch surface will be implemented after the auth foundation.</p>
            </template>
          </Card>
        </TabPanel>
        <TabPanel value="users">
          <Card>
            <template #title>User management foundation</template>
            <template #content>
              <p>Admin user CRUD will be added with the central account model.</p>
            </template>
          </Card>
        </TabPanel>
        <TabPanel value="codes">
          <Card>
            <template #title>Registration-code foundation</template>
            <template #content>
              <p>Registration-code CRUD will be added with the central account model.</p>
            </template>
          </Card>
        </TabPanel>
        <TabPanel value="profile">
          <Card>
            <template #title>Profile foundation</template>
            <template #content>
              <p>Password changes, profile metadata, and profile icons will be managed here.</p>
            </template>
          </Card>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <section class="status-panel">
      <Message :severity="statusTone" :closable="false">
        <span v-if="statusStore.status">
          API {{ statusStore.status.status }}; database {{ statusStore.status.database }}.
        </span>
        <span v-else-if="statusStore.error">{{ statusStore.error }}</span>
        <span v-else>Loading status.</span>
      </Message>
      <dl>
        <div>
          <dt>Configured app base</dt>
          <dd>{{ appBasePath }}</dd>
        </div>
        <div>
          <dt>Configured API base</dt>
          <dd>{{ apiBaseUrl }}</dd>
        </div>
      </dl>
    </section>
  </main>
</template>
