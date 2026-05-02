<script setup lang="ts">
import Button from "primevue/button";
import Card from "primevue/card";
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import { computed, onMounted, reactive, ref } from "vue";

import {
  deleteRequest,
  fetchBootstrapStatus,
  fetchMe,
  patchJson,
  postJson,
  requestJson,
  uploadAvatar,
  type RegistrationCodeSummary,
  type DirectorySiteListPayload,
  type DirectorySiteSummary,
  type SessionPayload,
  type UserListPayload,
  type UserSummary,
} from "./lib/api";
import { useStatusStore } from "./stores/status";

const statusStore = useStatusStore();
const currentUser = ref<UserSummary | null>(null);
const users = ref<UserSummary[]>([]);
const registrationCodes = ref<RegistrationCodeSummary[]>([]);
const directorySites = ref<DirectorySiteSummary[]>([]);
const bootstrapRequired = ref(false);
const authTab = ref("login");
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const loading = ref(false);
const appBasePath = import.meta.env.VITE_APP_BASE_PATH ?? "/auth";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/auth/api/v1";

const loginForm = reactive({ username: "", password: "" });
const registerForm = reactive({ username: "", password: "", registrationCode: "" });
const profileForm = reactive({ displayName: "", timezone: "America/Chicago" });
const userForm = reactive({
  username: "",
  password: "",
  displayName: "",
  timezone: "America/Chicago",
  isAdmin: false,
  isDisabled: false,
});
const codeForm = reactive({
  description: "",
  expiresAt: "",
});

const statusTone = computed(() => (statusStore.status?.status === "ok" ? "success" : "warn"));
const displayName = computed(() => currentUser.value?.display_name || currentUser.value?.username || "");

function showError(error: unknown, fallback: string): void {
  errorMessage.value = error instanceof Error ? error.message : fallback;
}

function showSuccess(message: string): void {
  successMessage.value = message;
  errorMessage.value = null;
}

async function restoreSession(): Promise<void> {
  try {
    const response = await fetchMe();
    setCurrentUser(response.user);
    await loadDirectory();
  } catch {
    currentUser.value = null;
    const bootstrapStatus = await fetchBootstrapStatus();
    bootstrapRequired.value = bootstrapStatus.bootstrap_required;
    authTab.value = bootstrapStatus.bootstrap_required ? "bootstrap" : "login";
  }
}

function setCurrentUser(user: UserSummary): void {
  currentUser.value = user;
  profileForm.displayName = user.display_name ?? "";
  profileForm.timezone = user.timezone;
}

async function submitAuth(mode: "bootstrap" | "login" | "register"): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  try {
    let response: SessionPayload;
    if (mode === "register") {
      response = await postJson<SessionPayload>("/auth/register", {
        username: registerForm.username,
        password: registerForm.password,
        registration_code: registerForm.registrationCode,
      });
    } else {
      const form = mode === "bootstrap" ? loginForm : loginForm;
      response = await postJson<SessionPayload>(`/auth/${mode}`, {
        username: form.username,
        password: form.password,
      });
    }
    setCurrentUser(response.user);
    await loadAdminData();
    showSuccess("Signed in.");
  } catch (error) {
    showError(error, "Unable to authenticate.");
  } finally {
    loading.value = false;
  }
}

async function logout(): Promise<void> {
  await postJson<Record<string, never>>("/auth/logout", {});
  currentUser.value = null;
  await restoreSession();
}

async function loadAdminData(): Promise<void> {
  if (!currentUser.value?.is_admin) {
    users.value = [];
    registrationCodes.value = [];
    return;
  }
  const [userResponse, codeResponse] = await Promise.all([
    requestJson<UserListPayload>("/users"),
    requestJson<{ registration_codes: RegistrationCodeSummary[] }>("/registration-codes"),
  ]);
  users.value = userResponse.users;
  registrationCodes.value = codeResponse.registration_codes;
}

async function loadDirectory(): Promise<void> {
  if (!currentUser.value) {
    directorySites.value = [];
    return;
  }
  const response = await requestJson<DirectorySiteListPayload>("/directory/sites");
  directorySites.value = response.sites;
}

async function saveProfile(): Promise<void> {
  try {
    const user = await patchJson<UserSummary>("/users/me", {
      display_name: profileForm.displayName || null,
      timezone: profileForm.timezone,
    });
    setCurrentUser(user);
    showSuccess("Profile saved.");
  } catch (error) {
    showError(error, "Unable to save profile.");
  }
}

async function changePassword(): Promise<void> {
  const currentPassword = window.prompt("Current password");
  const newPassword = window.prompt("New password");
  if (!currentPassword || !newPassword) {
    return;
  }
  try {
    await postJson<UserSummary>("/users/me/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    currentUser.value = null;
    showSuccess("Password changed. Sign in again.");
  } catch (error) {
    showError(error, "Unable to change password.");
  }
}

async function uploadProfileAvatar(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  try {
    const user = await uploadAvatar(file);
    setCurrentUser(user);
    showSuccess("Avatar updated.");
  } catch (error) {
    showError(error, "Unable to upload avatar.");
  } finally {
    input.value = "";
  }
}

async function createUser(): Promise<void> {
  try {
    await postJson<UserSummary>("/users", {
      username: userForm.username,
      password: userForm.password,
      display_name: userForm.displayName || null,
      timezone: userForm.timezone,
      is_admin: userForm.isAdmin,
      is_disabled: userForm.isDisabled,
    });
    Object.assign(userForm, {
      username: "",
      password: "",
      displayName: "",
      timezone: "America/Chicago",
      isAdmin: false,
      isDisabled: false,
    });
    await loadAdminData();
    showSuccess("User created.");
  } catch (error) {
    showError(error, "Unable to create user.");
  }
}

async function toggleUserDisabled(user: UserSummary): Promise<void> {
  try {
    await patchJson<UserSummary>(`/users/${user.id}`, {
      display_name: user.display_name,
      timezone: user.timezone,
      is_admin: user.is_admin,
      is_disabled: !user.is_disabled,
    });
    await loadAdminData();
  } catch (error) {
    showError(error, "Unable to update user.");
  }
}

async function deleteUser(user: UserSummary): Promise<void> {
  try {
    await deleteRequest(`/users/${user.id}`);
    await loadAdminData();
  } catch (error) {
    showError(error, "Unable to delete user.");
  }
}

async function createCode(): Promise<void> {
  try {
    await postJson<RegistrationCodeSummary>("/registration-codes", {
      description: codeForm.description || null,
      expires_at: new Date(codeForm.expiresAt).toISOString(),
    });
    codeForm.description = "";
    codeForm.expiresAt = "";
    await loadAdminData();
    showSuccess("Registration code created.");
  } catch (error) {
    showError(error, "Unable to create registration code.");
  }
}

async function revokeCode(code: RegistrationCodeSummary): Promise<void> {
  try {
    await postJson<RegistrationCodeSummary>(`/registration-codes/${code.id}/revoke`, {});
    await loadAdminData();
  } catch (error) {
    showError(error, "Unable to revoke registration code.");
  }
}

onMounted(async () => {
  await Promise.all([statusStore.loadStatus(), restoreSession()]);
  await loadAdminData();
});
</script>

<template>
  <main class="app-shell">
    <section class="app-header">
      <div>
        <p class="eyebrow">Central identity</p>
        <h1>Auth Directory</h1>
      </div>
      <div class="header-actions">
        <span v-if="currentUser">{{ displayName }}</span>
        <Button v-if="currentUser" label="Sign out" icon="pi pi-sign-out" severity="secondary" @click="logout" />
      </div>
    </section>

    <Message v-if="errorMessage" severity="error" :closable="false">{{ errorMessage }}</Message>
    <Message v-if="successMessage" severity="success" :closable="false">{{ successMessage }}</Message>

    <section v-if="!currentUser" class="auth-grid">
      <Card>
        <template #title>{{ bootstrapRequired ? "Bootstrap admin" : "Sign in" }}</template>
        <template #content>
          <Tabs v-model:value="authTab">
            <TabList>
              <Tab :value="bootstrapRequired ? 'bootstrap' : 'login'">
                {{ bootstrapRequired ? "Bootstrap" : "Login" }}
              </Tab>
              <Tab v-if="!bootstrapRequired" value="register">Register</Tab>
            </TabList>
            <TabPanels>
              <TabPanel :value="bootstrapRequired ? 'bootstrap' : 'login'">
                <form class="form-grid" @submit.prevent="submitAuth(bootstrapRequired ? 'bootstrap' : 'login')">
                  <InputText v-model="loginForm.username" placeholder="Username" autocomplete="username" />
                  <Password v-model="loginForm.password" placeholder="Password" toggle-mask :feedback="false" />
                  <Button type="submit" label="Continue" icon="pi pi-arrow-right" :loading="loading" />
                </form>
              </TabPanel>
              <TabPanel value="register">
                <form class="form-grid" @submit.prevent="submitAuth('register')">
                  <InputText v-model="registerForm.username" placeholder="Username" autocomplete="username" />
                  <Password v-model="registerForm.password" placeholder="Password" toggle-mask />
                  <InputText v-model="registerForm.registrationCode" placeholder="Registration code" />
                  <Button type="submit" label="Create account" icon="pi pi-user-plus" :loading="loading" />
                </form>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </template>
      </Card>
    </section>

    <Tabs v-else value="directory" class="workspace-tabs">
      <TabList>
        <Tab value="directory">Directory</Tab>
        <Tab v-if="currentUser.is_admin" value="users">Users</Tab>
        <Tab v-if="currentUser.is_admin" value="codes">Registration Codes</Tab>
        <Tab value="profile">My Profile</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="directory">
          <Card>
            <template #title>Directory</template>
            <template #content>
              <div class="site-grid">
                <a v-for="site in directorySites" :key="site.id" class="site-link" :href="site.base_url">
                  <i v-if="site.icon" :class="site.icon" aria-hidden="true"></i>
                  <span>
                    <strong>{{ site.name }}</strong>
                    <small>{{ site.description }}</small>
                  </span>
                </a>
              </div>
            </template>
          </Card>
        </TabPanel>

        <TabPanel value="users">
          <section class="panel-stack">
            <Card>
              <template #title>Create user</template>
              <template #content>
                <form class="management-grid" @submit.prevent="createUser">
                  <InputText v-model="userForm.username" placeholder="Username" />
                  <Password v-model="userForm.password" placeholder="Password" toggle-mask />
                  <InputText v-model="userForm.displayName" placeholder="Display name" />
                  <InputText v-model="userForm.timezone" placeholder="Timezone" />
                  <label class="check-row"><Checkbox v-model="userForm.isAdmin" binary /> Admin</label>
                  <label class="check-row"><Checkbox v-model="userForm.isDisabled" binary /> Disabled</label>
                  <Button type="submit" label="Create" icon="pi pi-plus" />
                </form>
              </template>
            </Card>

            <Card>
              <template #title>Users</template>
              <template #content>
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Name</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="user in users" :key="user.id">
                        <td>{{ user.username }}</td>
                        <td>{{ user.display_name || "-" }}</td>
                        <td>{{ user.is_admin ? "Admin" : "User" }}</td>
                        <td>{{ user.is_disabled ? "Disabled" : "Active" }}</td>
                        <td class="row-actions">
                          <Button
                            size="small"
                            severity="secondary"
                            :label="user.is_disabled ? 'Enable' : 'Disable'"
                            @click="toggleUserDisabled(user)"
                          />
                          <Button size="small" severity="danger" label="Delete" @click="deleteUser(user)" />
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </Card>
          </section>
        </TabPanel>

        <TabPanel value="codes">
          <section class="panel-stack">
            <Card>
              <template #title>Create registration code</template>
              <template #content>
                <form class="management-grid" @submit.prevent="createCode">
                  <InputText v-model="codeForm.description" placeholder="Description" />
                  <InputText v-model="codeForm.expiresAt" type="datetime-local" />
                  <Button type="submit" label="Create code" icon="pi pi-ticket" />
                </form>
              </template>
            </Card>
            <Card>
              <template #title>Registration codes</template>
              <template #content>
                <div class="code-list">
                  <article v-for="code in registrationCodes" :key="code.id" class="code-row">
                    <div>
                      <strong>{{ code.description || "Registration code" }}</strong>
                      <p v-if="code.code">New code: {{ code.code }}</p>
                      <p>Expires {{ new Date(code.expires_at).toLocaleString() }}</p>
                      <p>{{ code.revoked_at ? "Revoked" : "Active" }}</p>
                    </div>
                    <Button
                      label="Revoke"
                      icon="pi pi-ban"
                      severity="secondary"
                      :disabled="code.revoked_at !== null"
                      @click="revokeCode(code)"
                    />
                  </article>
                </div>
              </template>
            </Card>
          </section>
        </TabPanel>

        <TabPanel value="profile">
          <Card>
            <template #title>My Profile</template>
            <template #content>
              <form class="form-grid" @submit.prevent="saveProfile">
                <img v-if="currentUser.avatar_url" :src="currentUser.avatar_url" class="avatar-preview" alt="" />
                <InputText v-model="profileForm.displayName" placeholder="Display name" />
                <InputText v-model="profileForm.timezone" placeholder="Timezone" />
                <input type="file" accept="image/*" @change="uploadProfileAvatar" />
                <div class="button-row">
                  <Button type="submit" label="Save profile" icon="pi pi-save" />
                  <Button type="button" label="Change password" icon="pi pi-key" severity="secondary" @click="changePassword" />
                </div>
              </form>
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
