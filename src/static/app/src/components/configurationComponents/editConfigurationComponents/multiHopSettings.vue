<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {onMounted, ref, watch} from "vue";

const props = defineProps({
	configuration: Object
})
const emit = defineEmits(["refresh"])
const store = DashboardConfigurationStore()

const defaultSettings = () => ({
	Enabled: false,
	OutboundInterface: "",
	OutboundGateway: "",
	RoutedNetworks: "0.0.0.0/0",
	ExcludedNetworks: "",
	TableID: 51820,
	RulePriority: 10000,
	FirewallMark: 51820,
	EnableMasquerade: true,
	AutoSetInterfaceTableOff: true,
	LocalDNSInstalled: false,
	LocalDNSAddress: ""
})

const settings = ref(defaultSettings())
const preview = ref({
	ManagedBlock: {
		PostUp: "",
		PostDown: ""
	},
	Result: {
		PostUp: "",
		PostDown: "",
		Table: ""
	}
})
const loading = ref(false)
const saving = ref(false)
const applyingSaved = ref(false)
const edited = ref(false)
const errorMessage = ref("")
const errorField = ref("")

const syncFromConfiguration = () => {
	settings.value = {
		...defaultSettings(),
		...(props.configuration?.Info?.MultiHop || {})
	}
	edited.value = false
}

const fetchPreview = async () => {
	if (!props.configuration?.Name) return
	loading.value = true
	await fetchGet("/api/getWireguardConfigurationMultiHop", {
		configurationName: props.configuration.Name
	}, (res) => {
		if (res.status){
			preview.value = res.data.Preview
		}else{
			store.newMessage("Server", res.message, "danger")
		}
	})
	loading.value = false
}

const save = async (apply = false) => {
	if (!props.configuration?.Name) return
	saving.value = true
	errorField.value = ""
	errorMessage.value = ""
	await fetchPost("/api/updateWireguardConfigurationMultiHop", {
		Name: props.configuration.Name,
		Value: settings.value,
		Apply: apply
	}, (res) => {
		saving.value = false
		if (res.status){
			props.configuration.Info.MultiHop = res.data.Settings
			preview.value = res.data.Preview
			edited.value = false
			store.newMessage("Server", apply ? "Multi-hop settings saved and applied" : "Multi-hop settings saved", "success")
			if (apply){
				emit("refresh")
			}
		}else{
			errorField.value = res.data || ""
			errorMessage.value = res.message || "Unknown error"
			store.newMessage("Server", errorMessage.value, "danger")
		}
	})
}

const applySavedConfiguration = async () => {
	if (!props.configuration?.Name) return
	applyingSaved.value = true
	errorField.value = ""
	errorMessage.value = ""
	await fetchPost("/api/applyWireguardConfigurationMultiHop", {
		Name: props.configuration.Name
	}, (res) => {
		applyingSaved.value = false
		if (res.status){
			preview.value = res.data.Preview
			store.newMessage("Server", "Multi-hop settings applied", "success")
			emit("refresh")
		}else{
			errorField.value = res.data || ""
			errorMessage.value = res.message || "Unknown error"
			store.newMessage("Server", errorMessage.value, "danger")
		}
	})
}

watch(settings, () => {
	edited.value = JSON.stringify(settings.value) !== JSON.stringify(props.configuration?.Info?.MultiHop || defaultSettings())
}, {
	deep: true
})

watch(() => props.configuration?.Info?.MultiHop, () => {
	syncFromConfiguration()
	fetchPreview()
}, {
	deep: true
})

onMounted(async () => {
	syncFromConfiguration()
	await fetchPreview()
})
</script>

<template>
<div id="multiHopSettings">
	<h5 class="mb-0">
		<LocaleText t="Multi-hop Routing"></LocaleText>
	</h5>
	<h6 class="mb-3 text-muted">
		<small>
			<LocaleText t="Traffic from this interface can be forwarded to another VPN interface"></LocaleText>
		</small>
	</h6>
	<div class="d-flex flex-column gap-3">
		<div class="form-check form-switch">
			<input class="form-check-input" type="checkbox" role="switch" id="multiHop_enabled" v-model="settings.Enabled">
			<label class="form-check-label" for="multiHop_enabled">
				<LocaleText t="Enable Multi-hop"></LocaleText>
			</label>
		</div>
		<div>
			<label for="multiHop_outboundInterface" class="form-label">
				<small class="text-muted">
					<LocaleText t="Outbound Interface"></LocaleText>
				</small>
			</label>
			<input type="text"
			       id="multiHop_outboundInterface"
			       class="form-control form-control-sm rounded-3"
			       :class="{'is-invalid': errorField === 'OutboundInterface'}"
			       v-model="settings.OutboundInterface">
		</div>
		<div>
			<label for="multiHop_outboundGateway" class="form-label">
				<small class="text-muted">
					<LocaleText t="Outbound Gateway (Optional)"></LocaleText>
				</small>
			</label>
			<input type="text"
			       id="multiHop_outboundGateway"
			       class="form-control form-control-sm rounded-3"
			       :class="{'is-invalid': errorField === 'OutboundGateway'}"
			       v-model="settings.OutboundGateway">
		</div>
		<div>
			<label for="multiHop_routedNetworks" class="form-label">
				<small class="text-muted">
					<LocaleText t="Routed Networks"></LocaleText>
				</small>
			</label>
			<input type="text"
			       id="multiHop_routedNetworks"
			       class="form-control form-control-sm rounded-3"
			       :class="{'is-invalid': errorField === 'RoutedNetworks'}"
			       v-model="settings.RoutedNetworks">
		</div>
		<div>
			<label for="multiHop_excludedNetworks" class="form-label">
				<small class="text-muted">
					<LocaleText t="Excluded Networks (Optional)"></LocaleText>
				</small>
			</label>
			<input type="text"
			       id="multiHop_excludedNetworks"
			       class="form-control form-control-sm rounded-3"
			       :class="{'is-invalid': errorField === 'ExcludedNetworks'}"
			       v-model="settings.ExcludedNetworks">
		</div>
		<div class="d-flex gap-3 flex-column">
			<div class="form-check form-switch">
				<input class="form-check-input" type="checkbox" role="switch" id="multiHop_localDNSInstalled" v-model="settings.LocalDNSInstalled">
				<label class="form-check-label" for="multiHop_localDNSInstalled">
					Установлен локальный DNS
				</label>
			</div>
			<div>
				<label for="multiHop_localDNSAddress" class="form-label">
					<small class="text-muted">
						Адрес локального DNS
					</small>
				</label>
				<input type="text"
				       id="multiHop_localDNSAddress"
				       class="form-control form-control-sm rounded-3"
				       :disabled="!settings.LocalDNSInstalled"
				       :class="{'is-invalid': errorField === 'LocalDNSAddress'}"
				       v-model="settings.LocalDNSAddress">
			</div>
		</div>
		<div class="row gx-2 gy-2">
			<div class="col-12 col-md-4">
				<label for="multiHop_tableId" class="form-label">
					<small class="text-muted">
						<LocaleText t="Table ID"></LocaleText>
					</small>
				</label>
				<input type="number"
				       id="multiHop_tableId"
				       class="form-control form-control-sm rounded-3"
				       :class="{'is-invalid': errorField === 'TableID'}"
				       v-model="settings.TableID">
			</div>
			<div class="col-12 col-md-4">
				<label for="multiHop_rulePriority" class="form-label">
					<small class="text-muted">
						<LocaleText t="Rule Priority"></LocaleText>
					</small>
				</label>
				<input type="number"
				       id="multiHop_rulePriority"
				       class="form-control form-control-sm rounded-3"
				       :class="{'is-invalid': errorField === 'RulePriority'}"
				       v-model="settings.RulePriority">
			</div>
			<div class="col-12 col-md-4">
				<label for="multiHop_firewallMark" class="form-label">
					<small class="text-muted">
						<LocaleText t="Firewall Mark"></LocaleText>
					</small>
				</label>
				<input type="number"
				       id="multiHop_firewallMark"
				       class="form-control form-control-sm rounded-3"
				       :class="{'is-invalid': errorField === 'FirewallMark'}"
				       v-model="settings.FirewallMark">
			</div>
		</div>
		<div class="d-flex gap-3 flex-column flex-md-row">
			<div class="form-check form-switch">
				<input class="form-check-input" type="checkbox" role="switch" id="multiHop_enableMasquerade" v-model="settings.EnableMasquerade">
				<label class="form-check-label" for="multiHop_enableMasquerade">
					<LocaleText t="Enable Masquerade"></LocaleText>
				</label>
			</div>
			<div class="form-check form-switch">
				<input class="form-check-input" type="checkbox" role="switch" id="multiHop_autoTableOff" v-model="settings.AutoSetInterfaceTableOff">
				<label class="form-check-label" for="multiHop_autoTableOff">
					<LocaleText t="Auto set Table=off"></LocaleText>
				</label>
			</div>
		</div>
		<div class="invalid-feedback d-block" v-if="errorMessage">
			{{ errorMessage }}
		</div>
		<div class="d-flex mt-1 gap-2">
			<button class="btn btn-sm bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto"
			        :disabled="!edited || saving"
			        @click="syncFromConfiguration()">
				<i class="bi bi-arrow-clockwise me-2"></i>
				<LocaleText t="Reset"></LocaleText>
			</button>
			<button class="btn btn-sm bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 shadow"
			        :disabled="!edited || saving || applyingSaved"
			        @click="save(false)">
				<i class="bi bi-save-fill me-2"></i>
				<LocaleText t="Save"></LocaleText>
			</button>
			<button class="btn btn-sm bg-success-subtle border-success-subtle text-success-emphasis rounded-3 shadow"
			        :disabled="saving || applyingSaved"
			        @click="save(true)">
				<i class="bi bi-sign-turn-right-fill me-2"></i>
				<LocaleText t="Save & Apply"></LocaleText>
			</button>
			<button class="btn btn-sm bg-warning-subtle border-warning-subtle text-warning-emphasis rounded-3 shadow"
			        :disabled="saving || applyingSaved || loading"
			        @click="applySavedConfiguration()">
				<span class="spinner-border spinner-border-sm me-2" v-if="applyingSaved"></span>
				<i class="bi bi-lightning-charge-fill me-2" v-else></i>
				<LocaleText t="Apply Saved"></LocaleText>
			</button>
		</div>
		<div class="card rounded-3 bg-transparent mt-2">
			<div class="card-body py-2">
				<div class="mb-2">
					<small class="text-muted"><LocaleText t="Resulting Table"></LocaleText></small>
					<div><code>{{ preview?.Result?.Table || "-" }}</code></div>
				</div>
				<div class="mb-2">
					<small class="text-muted"><LocaleText t="Managed PostUp Block"></LocaleText></small>
					<textarea class="form-control form-control-sm rounded-3" rows="3" disabled :value="preview?.ManagedBlock?.PostUp || ''"></textarea>
				</div>
				<div>
					<small class="text-muted"><LocaleText t="Managed PostDown Block"></LocaleText></small>
					<textarea class="form-control form-control-sm rounded-3" rows="3" disabled :value="preview?.ManagedBlock?.PostDown || ''"></textarea>
				</div>
			</div>
		</div>
	</div>
</div>
</template>

<style scoped>
textarea{
	font-family: monospace;
}
</style>
