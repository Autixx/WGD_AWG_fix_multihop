<script setup async>
import {computed, ref} from "vue";
import {useRoute} from "vue-router";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import AllowedIPsInput from "@/components/configurationComponents/newPeersComponents/allowedIPsInput.vue";
import EndpointAllowedIps from "@/components/configurationComponents/newPeersComponents/endpointAllowedIps.vue";
import NameInput from "@/components/configurationComponents/newPeersComponents/nameInput.vue";
import DnsInput from "@/components/configurationComponents/newPeersComponents/dnsInput.vue";
import PresharedKeyInput from "@/components/configurationComponents/newPeersComponents/presharedKeyInput.vue";
import MtuInput from "@/components/configurationComponents/newPeersComponents/mtuInput.vue";
import PersistentKeepAliveInput
	from "@/components/configurationComponents/newPeersComponents/persistentKeepAliveInput.vue";

const emits = defineEmits(["close", "addedPeer"])
const dashboardStore = DashboardConfigurationStore()
const route = useRoute()

const availableIp = ref([])
const saving = ref(false)
const endpointError = ref(false)

const stsPeerData = ref({
	name: "",
	public_key: "",
	private_key: "",
	allowed_ips: [],
	allowed_ips_validation: false,
	endpoint: "",
	DNS: dashboardStore.Configuration.Peers.peer_global_dns,
	endpoint_allowed_ip: dashboardStore.Configuration.Peers.peer_endpoint_allowed_ip,
	keepalive: parseInt(dashboardStore.Configuration.Peers.peer_keep_alive),
	mtu: parseInt(dashboardStore.Configuration.Peers.peer_mtu),
	preshared_key: "",
})

await fetchGet("/api/getAvailableIPs/" + route.params.id, {}, (res) => {
	if (res.status){
		availableIp.value = res.data
	}
})

const checkEndpoint = () => {
	const endpoint = (stsPeerData.value.endpoint || "").trim()
	if (endpoint.length === 0){
		endpointError.value = true
		return false
	}
	const reg = /^(\[[0-9a-fA-F:]+\]|[^:\s]+):\d{1,5}$/
	const ok = reg.test(endpoint)
	if (!ok){
		endpointError.value = true
		return false
	}
	const port = parseInt(endpoint.substring(endpoint.lastIndexOf(":") + 1), 10)
	endpointError.value = Number.isNaN(port) || port < 1 || port > 65535
	return !endpointError.value
}

const requiredFieldsFilled = computed(() => {
	return (
		(stsPeerData.value.public_key || "").trim().length > 0 &&
		stsPeerData.value.allowed_ips.length > 0 &&
		(stsPeerData.value.endpoint || "").trim().length > 0 &&
		(stsPeerData.value.endpoint_allowed_ip || "").trim().length > 0 &&
		!endpointError.value
	)
})

const createStSPeer = () => {
	if (!checkEndpoint()){
		dashboardStore.newMessage("WGDashboard", "Endpoint format is incorrect. Use host:port or [ipv6]:port", "danger")
		return
	}
	saving.value = true
	fetchPost("/api/addSiteToSitePeer/" + route.params.id, stsPeerData.value, (res) => {
		saving.value = false
		if (res.status){
			dashboardStore.newMessage("Server", "Site-to-site peer created successfully", "success")
			emits("addedPeer")
		}else{
			dashboardStore.newMessage("Server", res.message, "danger")
		}
	})
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 1000px">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
						<h4 class="mb-0">
							<LocaleText t="Add Site-to-site Peer"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
					</div>
					<div class="card-body px-4 pb-4 d-flex flex-column gap-3">
						<NameInput :saving="saving" :data="stsPeerData"></NameInput>

						<div>
							<label for="sts_public_key" class="form-label">
								<small class="text-muted">
									<LocaleText t="Public Key"></LocaleText> <code><LocaleText t="(Required)"></LocaleText></code>
								</small>
							</label>
							<input type="text"
							       id="sts_public_key"
							       class="form-control form-control-sm rounded-3"
							       :disabled="saving"
							       v-model="stsPeerData.public_key">
						</div>

						<div>
							<label for="sts_private_key" class="form-label">
								<small class="text-muted">
									<LocaleText t="Private Key"></LocaleText>
									<code><LocaleText t="(Optional)"></LocaleText></code>
								</small>
							</label>
							<input type="text"
							       id="sts_private_key"
							       class="form-control form-control-sm rounded-3"
							       :disabled="saving"
							       v-model="stsPeerData.private_key">
						</div>

						<AllowedIPsInput :availableIp="availableIp" :saving="saving" :data="stsPeerData"></AllowedIPsInput>

						<div>
							<label for="sts_endpoint" class="form-label">
								<small class="text-muted">
									<LocaleText t="Endpoint"></LocaleText>
									<code><LocaleText t="(Required)"></LocaleText></code>
								</small>
							</label>
							<input type="text"
							       id="sts_endpoint"
							       class="form-control form-control-sm rounded-3"
							       :class="{'is-invalid': endpointError}"
							       :disabled="saving"
							       @blur="checkEndpoint()"
							       v-model="stsPeerData.endpoint"
							       placeholder="host:port">
							<small class="text-muted">
								<LocaleText t="Use format host:port or [ipv6]:port"></LocaleText>
							</small>
						</div>

						<div class="accordion mb-1" id="stsPeerAccordion">
							<div class="accordion-item">
								<h2 class="accordion-header">
									<button class="accordion-button collapsed rounded-3"
									        type="button"
									        data-bs-toggle="collapse"
									        data-bs-target="#stsPeerAccordionAdvancedOptions">
										<LocaleText t="Advanced Options"></LocaleText>
									</button>
								</h2>
								<div id="stsPeerAccordionAdvancedOptions"
								     class="accordion-collapse collapse collapsed"
								     data-bs-parent="#stsPeerAccordion">
									<div class="accordion-body rounded-bottom-3 d-flex flex-column gap-2">
										<DnsInput :saving="saving" :data="stsPeerData"></DnsInput>
										<EndpointAllowedIps :saving="saving" :data="stsPeerData"></EndpointAllowedIps>
										<div class="row gy-3">
											<div class="col-sm">
												<PresharedKeyInput :saving="saving" :data="stsPeerData"></PresharedKeyInput>
											</div>
											<div class="col-sm">
												<MtuInput :saving="saving" :data="stsPeerData"></MtuInput>
											</div>
											<div class="col-sm">
												<PersistentKeepAliveInput :saving="saving" :data="stsPeerData"></PersistentKeepAliveInput>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>

						<div class="d-flex mt-2">
							<button class="ms-auto btn btn-dark btn-brand rounded-3 px-3 py-2 shadow"
							        :disabled="!requiredFieldsFilled || saving"
							        @click="createStSPeer()">
								<i class="bi bi-diagram-3-fill me-2" v-if="!saving"></i>
								<LocaleText t="Adding..." v-if="saving"></LocaleText>
								<LocaleText t="Add" v-else></LocaleText>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
