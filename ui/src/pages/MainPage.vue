<script setup lang="ts">
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import strings from '@milaboratories/strings';
import type { PlRef } from '@platforma-sdk/model';
import { getRawPlatformaInstance } from '@platforma-sdk/model';
import {
  PlAgDataTableV2,
  PlAlert,
  PlBlockPage,
  PlBtnGhost,
  PlDropdownMulti,
  PlDropdownRef,
  PlMaskIcon24,
  PlSlideModal,
  usePlDataTableSettingsV2,
} from '@platforma-sdk/ui-vue';
import { asyncComputed } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
import { useApp } from '../app';

const app = useApp();

function setInput(inputRef?: PlRef) {
  if (!inputRef) return;
  app.model.args.inputAnchor = inputRef;
}

const tableSettings = usePlDataTableSettingsV2({
  model: () => app.model.outputs.pt,
});

const settingsIsShown = ref(app.model.args.inputAnchor === undefined);

// Auto-close settings panel when block starts running
watch(
  () => app.model.outputs.isRunning,
  (isRunning, wasRunning) => {
    // Close settings when block starts running (false -> true transition)
    if (isRunning && !wasRunning) {
      settingsIsShown.value = false;
    }
  },
);

const liabilityTypesModel = computed({
  get: () => (app.model.args.liabilityTypes ?? []),
  set: (value) => {
    app.model.args.liabilityTypes = value ?? [];
  },
});

const isEmpty = asyncComputed(async () => {
  if (app.model.outputs.liabilitiesRiskTable === undefined) return undefined;
  return (await getRawPlatformaInstance().pFrameDriver.getShape(app.model.outputs.liabilitiesRiskTable)).rows === 0;
});

</script>

<template>
  <PlBlockPage
    v-model:subtitle="app.model.args.customBlockLabel"
    :subtitle-placeholder="app.model.args.defaultBlockLabel"
    title="Antibody Sequence Liabilities"
  >
    <template #append>
      <PlBtnGhost @click.stop="settingsIsShown = true">
        {{ strings.titles.settings }}
        <template #append>
          <PlMaskIcon24 name="settings" />
        </template>
      </PlBtnGhost>
    </template>
    <PlAgDataTableV2
      v-model="app.model.ui.tableState"
      :settings="tableSettings"
      show-export-button
      :not-ready-text="strings.callToActions.configureSettingsAndRun"
      :no-rows-text="strings.states.noDataAvailable"
    />
  </PlBlockPage>

  <PlSlideModal v-model="settingsIsShown">
    <template #title>{{ strings.titles.settings }}</template>
    <PlDropdownRef
      v-model="app.model.args.inputAnchor"
      :options="app.model.outputs.inputOptions ?? []"
      :label="strings.titles.dataset"
      required
      @update:model-value="setInput"
    />
    <PlAlert v-if="isEmpty === true" type="warn" :style="{ width: '320px' }">
      <template #title>Empty dataset selection</template>
      The input dataset you have selected is empty.
      Please choose a different dataset.
    </PlAlert>
    <PlDropdownMulti v-model="liabilityTypesModel" label="Liability types" :options="liabilityTypes" >
      <template #tooltip>
        Select the liability types to include in the analysis.
      </template>
    </PlDropdownMulti>
  </PlSlideModal>
</template>
